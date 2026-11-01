"""Archive extraction workflows, including batch and recursive extraction."""

import argparse
import logging
import os
import pathlib
import sys

from cli_paths import BIN_PATH
from detection import find_candidate_handlers
from helpers import delete_source


def confirm_run_installer(file_path):
    """Confirm before a handler runs the original installer itself."""
    logging.warning(f"About to run installer to extract: {file_path}")
    if not sys.stdin.isatty():
        return True
    try:
        answer = input("Run it anyway? [y/N] ")
    except EOFError:
        return True
    return answer.strip().lower() in ("y", "yes")


def process_extraction(args, depth=0):
    """Try candidate handlers until one extracts the input successfully."""
    candidates = find_candidate_handlers(
        file_path=args.file_path,
        fast_check=args.fast_check,
        bruteforce=getattr(args, "bruteforce", False),
    )
    for candidate in candidates:
        logging.info(f"Trying handler: {candidate.__name__}")
        handler = candidate(cli_args=args, bin_path=BIN_PATH)
        handler.pre_extract_actions()
        if handler.extract():
            handler.post_extract_actions()
            logging.info(f"Extraction completed successfully using handler: {candidate.__name__}")
            if getattr(args, "recursive", False):
                extract_nested(handler.extract_directory, args, depth)
            return True
        logging.error(f"Extraction failed using handler: {candidate.__name__}")

    logging.error(f"No handler succeeded for file: {args.file_path}")
    return False


def extract_nested(directory, args, depth):
    """Extract archives inside an output directory, bounded by ``max_depth``."""
    if depth + 1 > getattr(args, "max_depth", 1):
        return

    targets = []
    for root, _dirs, files in os.walk(directory):
        for name in files:
            if name != "magic-extractor.log":
                targets.append(pathlib.Path(root) / name)

    for nested_path in targets:
        if not nested_path.is_file():
            continue
        if not find_candidate_handlers(
            file_path=nested_path, fast_check=args.fast_check
        ):
            continue

        logging.info(f"Recursively extracting: {nested_path}")
        nested_args = argparse.Namespace(**vars(args))
        nested_args.file_path = nested_path
        nested_args.output_dir = None
        nested_args.open_output_folder = False
        process_extraction(nested_args, depth + 1)


def run_extract(args):
    """Extract one file or each file in a directory (non-recursively)."""
    delete_after = getattr(args, "delete_source", False)
    use_recycle_bin = getattr(args, "delete_to_recycle_bin", True)

    if args.file_path.is_dir():
        any_failed = False
        for item in args.file_path.iterdir():
            if not item.is_file():
                continue

            logging.info(f"Processing file: {item}")
            temp_args = argparse.Namespace(**vars(args))
            temp_args.file_path = item
            if process_extraction(temp_args):
                if delete_after:
                    delete_source(item, use_recycle_bin)
            else:
                any_failed = True
                logging.error(f"Extraction failed for file: {item}")
        return not any_failed

    result = process_extraction(args)
    if result and delete_after:
        delete_source(args.file_path, use_recycle_bin)
    return result
