"""Archive extraction workflows, including batch and recursive extraction."""

import argparse
import datetime
import logging
import os
import pathlib

from cli_paths import BIN_PATH
from detection import find_candidate_handlers
from formats.base_extractor import default_output_dir
from helpers import delete_source, run_per_file


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

    if os.path.isdir(output_dir) and os.listdir(output_dir) and not getattr(args, "merge_output", False):
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
        return False

    # One output folder for every attempt on this file; each attempt runs in
    # its own staging folder inside it (BaseExtractor.extract_atomically).
    try:
        output_dir, created = resolve_output_dir(args)
    except OSError as exc:
        logging.error(f"Cannot prepare the output folder for {args.file_path}: {exc}")
        return False
    file_args = argparse.Namespace(**vars(args))
    file_args.output_dir = output_dir

    for candidate in candidates:
        logging.info(f"Trying handler: {candidate.__name__}")
        handler = candidate(cli_args=file_args, bin_path=BIN_PATH)
        handler.pre_extract_actions()
        if handler.extract_atomically():
            handler.post_extract_actions()
            logging.info(f"Extraction completed successfully using handler: {candidate.__name__}")
            if getattr(args, "recursive", False):
                extract_nested(handler.extracted_files(), args, depth)
            return True
        logging.error(f"Extraction failed using handler: {candidate.__name__}")

    logging.error(f"No handler succeeded for file: {args.file_path}")
    if created:
        try:
            os.rmdir(output_dir)  # only removes it if it is still empty
        except OSError:
            pass
    return False


def extract_nested(files, args, depth):
    """
    Extract the archives among ``files`` (what the parent extraction produced,
    not the rest of a shared output folder), bounded by ``max_depth``.
    """
    if depth + 1 > getattr(args, "max_depth", 1):
        return

    targets = [pathlib.Path(path) for path in files
               if os.path.basename(path) != "magic-extractor.log"]

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
        process_extraction(nested_args, depth + 1, candidates=candidates)


def run_extract(args):
    """Extract one file, or each file in a directory (non-recursively)."""
    delete_after = getattr(args, "delete_source", False)
    use_recycle_bin = getattr(args, "delete_to_recycle_bin", True)

    def extract_one(file_args):
        if not process_extraction(file_args):
            return False
        if delete_after:
            delete_source(file_args.file_path, use_recycle_bin)
        return True

    return run_per_file(args, extract_one, output_name=batch_output_name)


def batch_output_name(item, items):
    """
    Output folder name for one file of a directory batch: <stem>_extracted,
    the same as a single extraction, or <name>_extracted when another file of
    the batch has the same stem (a.zip + a.7z would otherwise share a folder).
    """
    same_stem = sum(1 for other in items if other.stem == item.stem)
    return f"{item.stem}_extracted" if same_stem == 1 else f"{item.name}_extracted"
