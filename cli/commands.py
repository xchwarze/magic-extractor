"""Read-only CLI commands: identify and list."""

import logging

from cli_paths import BIN_PATH
from detection import (
    append_pe_installer_fallbacks,
    candidates_from_outputs,
    detector_outputs,
    find_candidate_handlers,
)
from detection_filter import filter_detections, filter_mimes


def process_identify(args):
    """Print detector results and candidate handlers without extracting."""
    outputs = list(detector_outputs(args.file_path, args.fast_check))
    print(f"File: {args.file_path}")
    for source, mimes, detections in outputs:
        for mime_type in filter_mimes(mimes):
            print(f"  [{source}] MIME     {mime_type}")
        for detected_type in filter_detections(detections):
            print(f"  [{source}] detect   {detected_type}")

    candidates = candidates_from_outputs(outputs)
    append_pe_installer_fallbacks(args.file_path, candidates)
    if candidates:
        print("Candidate handlers (in order):")
        for candidate in candidates:
            print(f"  - {candidate.__name__}")
        return True

    print("No candidate handler found.")
    return False


def process_list(args):
    """List contents with the first candidate handler that supports listing."""
    candidates = find_candidate_handlers(
        file_path=args.file_path, fast_check=args.fast_check
    )
    for candidate in candidates:
        handler = candidate(cli_args=args, bin_path=BIN_PATH)
        listing = handler.list_contents()
        if listing is not None:
            print(listing)
            return True
        logging.info(
            f"{candidate.__name__} does not support listing; trying next candidate."
        )

    logging.error(f"No candidate handler could list: {args.file_path}")
    return False
