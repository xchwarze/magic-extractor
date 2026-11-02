"""Archive extraction workflows, including batch and recursive extraction."""

import argparse
import datetime
import enum
import logging
import os
import pathlib

from cli_paths import BIN_PATH
from detection import find_candidate_handlers
from formats.base_extractor import STAGING_PREFIX, default_output_dir, remove_stale_staging
from helpers import delete_source, run_per_file


class Outcome(enum.Enum):
    """How the extraction of one file (or a whole run) ended."""
    OK = "ok"
    PARTIAL = "partial"   # extracted, but some entries failed (e.g. symlinks on Windows)
    FAILED = "failed"

    def __bool__(self):
        # Only a full success is truthy, so nothing treats a partial extraction as
        # one (--delete-source, a batch's success, carve's result).
        return self is Outcome.OK


# Exit codes of `extract` (2 is argparse's "invalid arguments").
EXIT_CODES = {Outcome.OK: 0, Outcome.FAILED: 1, Outcome.PARTIAL: 3}


def _has_user_content(folder):
    """Whether folder holds anything besides staging folders of runs in progress."""
    return any(not name.startswith(STAGING_PREFIX) for name in os.listdir(folder))


def resolve_output_dir(args, now=None):
    """
    Decide the output folder for one file, once, before any handler runs:
    ``args.output_dir`` or ``<stem>_extracted`` beside the file. If that folder
    already has files, a new ``<folder>_<YYYYmmdd-HHMMSS>`` is used instead (a
    re-extraction never mixes with, or overwrites, an earlier one), unless
    ``--merge-output`` asks to extract into the existing folder.

    Returns:
        (str, bool): the folder (created if needed) and whether this call
        created it.
    """
    if args.output_dir:
        output_dir = os.path.abspath(str(args.output_dir))
    else:
        output_dir = os.path.abspath(default_output_dir(str(args.file_path)))

    if os.path.isdir(output_dir):
        remove_stale_staging(output_dir)  # left by a run that was killed (GUI Cancel)
    if (os.path.isdir(output_dir) and _has_user_content(output_dir)
            and not getattr(args, "merge_output", False)):
        stamp = (now or datetime.datetime.now()).strftime("%Y%m%d-%H%M%S")
        candidate, suffix = f"{output_dir}_{stamp}", 2
        while os.path.exists(candidate):
            candidate, suffix = f"{output_dir}_{stamp}-{suffix}", suffix + 1
        logging.info(f"Output folder already has files: {output_dir}; extracting to {candidate}")
        output_dir = candidate

    created = not os.path.exists(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    return output_dir, created


def process_extraction(args, depth=0, candidates=None):
    """
    Try candidate handlers until one extracts the input successfully.

    ``candidates`` can be passed when the caller already ran detection (as
    extract_nested does), so the detectors don't run twice on the same file.
    """
    if candidates is None:
        candidates = find_candidate_handlers(
            file_path=args.file_path,
            fast_check=args.fast_check,
            bruteforce=getattr(args, "bruteforce", False),
        )
    if not candidates:
        logging.error(f"No handler succeeded for file: {args.file_path}")
        return Outcome.FAILED

    # One output folder for every attempt on this file; each attempt runs in
    # its own staging folder inside it (BaseExtractor.extract_atomically).
    try:
        output_dir, created = resolve_output_dir(args)
    except OSError as exc:
        logging.error(f"Cannot prepare the output folder for {args.file_path}: {exc}")
        return Outcome.FAILED
    file_args = argparse.Namespace(**vars(args))
    file_args.output_dir = output_dir

    partials = []  # handlers whose failed attempt still extracted files
    try:
        for candidate in candidates:
            logging.info(f"Trying handler: {candidate.__name__}")
            handler = candidate(cli_args=file_args, bin_path=BIN_PATH)
            handler.pre_extract_actions()
            if handler.extract_atomically():
                handler.post_extract_actions()
                logging.info(f"Extraction completed successfully using handler: {candidate.__name__}")
                if getattr(args, "recursive", False):
                    extract_nested(handler.extracted_files(), args, depth)
                return Outcome.OK
            if getattr(handler, "partial_staging", None):
                partials.append(handler)
                logging.warning(f"Extraction failed using handler: {candidate.__name__} "
                                f"(but it extracted part of the content; kept in case nothing does better)")
            else:
                logging.error(f"Extraction failed using handler: {candidate.__name__}")

        # Nothing fully succeeded: keep the biggest partial extraction rather than
        # nothing (it used to be kept before attempts were staged).
        best = max(partials, key=lambda partial: partial.partial_size(), default=None)
        if best is not None:
            partials.remove(best)
            if best.adopt_partial():
                best.post_extract_actions()
                logging.warning(
                    f"Extracted with errors using handler: {type(best).__name__}: some entries could not "
                    f"be written (e.g. symbolic links on Windows); the rest is in {output_dir}")
                if getattr(args, "recursive", False):
                    extract_nested(best.extracted_files(), args, depth)
                return Outcome.PARTIAL
    finally:
        for partial in partials:
            partial.discard_partial()

    logging.error(f"No handler succeeded for file: {args.file_path}")
    if created:
        try:
            os.rmdir(output_dir)  # only removes it if it is still empty
        except OSError:
            pass
    return Outcome.FAILED


def extract_nested(files, args, depth):
    """
    Extract the archives among ``files`` (what the parent extraction produced,
    not the rest of a shared output folder), bounded by ``max_depth``.
    """
    if depth + 1 > getattr(args, "max_depth", 1):
        return

    targets = [pathlib.Path(path) for path in files
               if os.path.basename(path) != "magic-extractor.log"]

    failed = []
    for nested_path in targets:
        if not nested_path.is_file():
            continue
        candidates = find_candidate_handlers(
            file_path=nested_path,
            fast_check=args.fast_check,
            bruteforce=getattr(args, "bruteforce", False),
        )
        if not candidates:
            continue

        logging.info(f"Recursively extracting: {nested_path}")
        nested_args = argparse.Namespace(**vars(args))
        nested_args.file_path = nested_path
        nested_args.output_dir = None
        nested_args.open_output_folder = False
        if not process_extraction(nested_args, depth + 1, candidates=candidates):
            failed.append(nested_path)

    if failed:
        # Contract: recursion is best effort. A nested file can be a detection
        # candidate without being an archive (every DLL of an installer is a PE
        # candidate), so nested failures are reported here but do not change
        # the exit code of the extraction that produced them.
        logging.warning(f"{len(failed)} nested file(s) could not be extracted "
                        f"(listed above); the exit code only reflects the top-level extraction.")


def run_extract(args):
    """Extract one file, or each file in a directory (non-recursively)."""
    delete_after = getattr(args, "delete_source", False)
    use_recycle_bin = getattr(args, "delete_to_recycle_bin", True)

    outcomes = []

    def extract_one(file_args):
        outcome = process_extraction(file_args)
        if outcome is Outcome.OK and delete_after and not delete_source(file_args.file_path, use_recycle_bin):
            logging.error(f"Extracted, but the source could not be deleted as asked: {file_args.file_path}")
            outcome = Outcome.FAILED
        elif outcome is Outcome.PARTIAL and delete_after:
            logging.warning(f"Not deleting the source: it was only partly extracted: {file_args.file_path}")
        outcomes.append(outcome)
        return outcome is not Outcome.FAILED

    # The run's outcome: any failure (or a folder with no files) fails it; else a
    # partial extraction makes it partial.
    if not run_per_file(args, extract_one, output_name=batch_output_name) or not outcomes:
        return Outcome.FAILED
    return Outcome.PARTIAL if Outcome.PARTIAL in outcomes else Outcome.OK


def batch_output_name(item, items):
    """
    Output folder name for one file of a directory batch: <stem>_extracted,
    the same as a single extraction, or <name>_extracted when another file of
    the batch has the same stem (a.zip + a.7z would otherwise share a folder).
    """
    same_stem = sum(1 for other in items if other.stem == item.stem)
    return f"{item.stem}_extracted" if same_stem == 1 else f"{item.name}_extracted"
