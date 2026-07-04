import argparse
import logging
import sys
import os
import pathlib
from logger import setup_logging
from config import Config
from file_type import determine_file_type_with_magic, determine_file_type_with_binwalk, determine_file_type_with_die, determine_file_type_with_trid, determine_file_type_with_magika, binwalk_file_map
from formats import init_handlers, get_handler_from_mime, get_handler_from_detection
from detection_filter import init_blacklist, filter_mimes, filter_detections, is_generic_detection

# Resolve the base path (frozen-exe aware) so 'bin' and 'data' stay external and updatable.
# When frozen by PyInstaller they live beside the executable; in dev they live under 'src'.
if getattr(sys, "frozen", False):
    BASE_PATH = os.path.dirname(sys.executable)
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))

BIN_PATH = os.path.join(BASE_PATH, 'bin')
DATA_PATH = os.path.join(BASE_PATH, 'data')

def file_path_type_check(path):
    """Custom argparse type to check if a file or directory exists."""
    input_path = pathlib.Path(path)
    if not (input_path.is_file() or input_path.is_dir()):
        raise argparse.ArgumentTypeError(f"The path {path} does not exist or is not a file/directory.")

    return input_path

def dir_path_type_check(path):
    """Custom argparse type to check if a directory exists and is writable."""
    dir_path = pathlib.Path(path)
    if not dir_path.is_dir():
        raise argparse.ArgumentTypeError(f"The directory {path} does not exist.")

    if not os.access(dir_path, os.W_OK):
        raise argparse.ArgumentTypeError(f"The directory {path} is not writable.")

    return dir_path

SUBCOMMANDS = ("extract", "identify", "list", "carve")

def configure_parser():
    """Configure and return the subcommand argument parser."""
    # Options shared by every subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--debug", help="Enable debug logging", action="store_true")
    common.add_argument("--no-fast-check", help="Disable fast type check", action='store_false', dest='fast_check')

    parser = argparse.ArgumentParser(description="Universal Extractor for various file formats")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # extract: detect and extract (the historical default behaviour).
    extract_parser = subparsers.add_parser("extract", parents=[common], help="Detect and extract an archive")
    extract_parser.add_argument("file_path", help="Path to the file or directory to be extracted", type=file_path_type_check)
    extract_parser.add_argument("output_dir", help="Directory to extract the file to", type=dir_path_type_check, nargs='?', default=None)
    extract_parser.add_argument("--password", help="Password for encrypted files, required by some extractors", type=str, default=None)
    extract_parser.add_argument("--update-defaults", help="Update default configuration values", action="store_true")

    # Configurable settings as command-line options
    extract_parser.add_argument("--open-output-folder", help="Open output folder after extraction", type=bool, default=None)
    extract_parser.add_argument("--check-free-space", help="Check disk space before extraction", type=bool, default=None)
    extract_parser.add_argument("--extract-video-tracks", help="Extract video tracks if available", type=bool, default=None)
    extract_parser.add_argument("--warn-before-executing", help="Warn before executing any executable file", type=bool, default=None)
    extract_parser.add_argument("--check-unicode", help="Check for unicode characters in file names", type=bool, default=None)
    extract_parser.add_argument("--fix-file-extensions", help="Automatically fix file extensions", type=bool, default=None)
    extract_parser.add_argument("--create-log-files", help="Create log files of the operations", type=bool, default=None)
    extract_parser.add_argument("-r", "--recursive", help="Recursively extract archives found inside the output", action="store_true")
    extract_parser.add_argument("--max-depth", help="Maximum recursion depth for --recursive", type=int, default=5)

    # identify: run the detectors and report, without extracting.
    identify_parser = subparsers.add_parser("identify", parents=[common], help="Detect file type and candidate handlers without extracting")
    identify_parser.add_argument("file_path", help="Path to the file to identify", type=file_path_type_check)

    # list: list archive contents without extracting.
    list_parser = subparsers.add_parser("list", parents=[common], help="List archive contents without extracting")
    list_parser.add_argument("file_path", help="Path to the archive to list", type=file_path_type_check)
    list_parser.add_argument("--password", help="Password for encrypted files, required by some extractors", type=str, default=None)

    # carve: carve embedded archives at binwalk offsets and extract them.
    carve_parser = subparsers.add_parser("carve", parents=[common], help="Carve embedded archives at binwalk offsets and extract them")
    carve_parser.add_argument("file_path", help="Path to the file to carve", type=file_path_type_check)
    carve_parser.add_argument("output_dir", help="Directory to write carved segments to", type=dir_path_type_check, nargs='?', default=None)
    carve_parser.add_argument("--password", help="Password for encrypted files, required by some extractors", type=str, default=None)
    carve_parser.add_argument("--list", help="List binwalk fragments (index, offset, size, name) and exit", action="store_true", dest="list_fragments")
    carve_parser.add_argument("--fragment", help="Carve only the fragment at this index (see --list)", type=int, default=None)
    carve_parser.add_argument("--raw", help="Carve every fragment raw (binwalk extract-all), not only handler-known ones", action="store_true")

    return parser

def configure_settings(args, config):
    """Update settings from command line arguments if necessary, and apply them."""
    keys = ["open_output_folder", "check_free_space", "extract_video_tracks", "warn_before_executing",
            "check_unicode", "fix_file_extensions", "create_log_files", "fast_check"]
    
    # Update configuration defaults if requested
    if args.update_defaults:
        for key in keys:
            value = getattr(args, key)
            if value is not None:
                config.set('settings', key, str(value))
        config.save()

    # Apply current command-line options or use defaults from configuration
    for key in keys:
        if getattr(args, key) is None:
            setattr(args, key, config.get('settings', key, type=bool))

def _detector_outputs(file_path, fast_check):
    """
    Run the detectors in priority order and normalize each result to
    (source_name, mime_list, detection_list). Magika (AI, high precision) runs
    first; puremagic runs last as a pure-python fallback.
    """
    outputs = []

    magika_result = determine_file_type_with_magika(file_path=file_path, bin_path=BIN_PATH)
    outputs.append((
        "Magika",
        magika_result["mime_types"] if magika_result else [],
        magika_result["labels"] if magika_result else [],
    ))

    for source, detector in (
        ("DIE", determine_file_type_with_die),
        ("TrID", determine_file_type_with_trid),
        ("binwalk", determine_file_type_with_binwalk),
    ):
        detections = detector(file_path=file_path, bin_path=BIN_PATH)
        outputs.append((source, [], detections or []))

    # puremagic last: pure-python fallback; generic MIME is filtered downstream.
    mime_types = determine_file_type_with_magic(file_path=file_path, fast_check=fast_check)
    outputs.append(("puremagic", list(mime_types) if mime_types else [], []))

    return outputs

def _candidates_from_outputs(outputs):
    """Resolve detector outputs to an ordered, deduped list of handler classes."""
    candidates = []
    for source, mimes, detections in outputs:
        for mime_type in filter_mimes(mimes):
            handler_class = get_handler_from_mime(mime_type=mime_type)
            if handler_class and handler_class not in candidates:
                logging.info(f"Candidate handler from {source} MIME: {mime_type}")
                candidates.append(handler_class)

        for detection in filter_detections(detections):
            handler_class = get_handler_from_detection(detection=detection)
            if handler_class and handler_class not in candidates:
                logging.info(f"Candidate handler from {source} detection: {detection}")
                candidates.append(handler_class)

    return candidates

def find_candidate_handlers(file_path, fast_check):
    """Return a list of candidate handler classes based on file type detection."""
    return _candidates_from_outputs(_detector_outputs(file_path, fast_check))

def process_extraction(args, depth=0):
    """
    Process file extraction by iterating over candidate handlers.
    Waits for a handler to return True from extract(). When --recursive is set,
    archives found inside the output are extracted too, up to --max-depth.
    """
    candidates = find_candidate_handlers(file_path=args.file_path, fast_check=args.fast_check)
    for candidate in candidates:
        handler = candidate(cli_args=args, bin_path=BIN_PATH)
        handler.pre_extract_actions()
        if handler.extract():
            handler.post_extract_actions()
            logging.info("Extraction completed successfully.")
            if getattr(args, 'recursive', False):
                extract_nested(handler.extract_directory, args, depth)
            return True
        else:
            logging.error(f"Extraction failed using handler: {candidate.__name__}")

    logging.error(f"No handler succeeded for file: {args.file_path}")
    return False

def extract_nested(directory, args, depth):
    """Extract any archives found inside a freshly-extracted directory (bounded by --max-depth)."""
    if depth + 1 > getattr(args, 'max_depth', 1):
        return

    # Snapshot the files first so newly-created output subdirs are not re-walked.
    targets = []
    for root, dirs, files in os.walk(directory):
        for name in files:
            if name == 'magic-extractor.log':
                continue
            targets.append(pathlib.Path(root) / name)

    for nested_path in targets:
        if not nested_path.is_file():
            continue
        if not find_candidate_handlers(file_path=nested_path, fast_check=args.fast_check):
            continue

        logging.info(f"Recursively extracting: {nested_path}")
        nested_args = argparse.Namespace(**vars(args))
        nested_args.file_path = nested_path
        nested_args.output_dir = None          # extract into a sibling <name>_extracted dir
        nested_args.open_output_folder = False  # only the top-level extraction opens a folder
        process_extraction(nested_args, depth + 1)

def process_identify(args):
    """Run the detectors and print detected types + candidate handlers, no extraction."""
    outputs = _detector_outputs(args.file_path, args.fast_check)
    print(f"File: {args.file_path}")
    for source, mimes, detections in outputs:
        for mime_type in filter_mimes(mimes):
            print(f"  [{source}] MIME     {mime_type}")
        for detection in filter_detections(detections):
            print(f"  [{source}] detect   {detection}")

    candidates = _candidates_from_outputs(outputs)
    if candidates:
        print("Candidate handlers (in order):")
        for candidate in candidates:
            print(f"  - {candidate.__name__}")
        return True

    print("No candidate handler found.")
    return False

def process_list(args):
    """List archive contents using the first candidate handler that supports it."""
    candidates = find_candidate_handlers(file_path=args.file_path, fast_check=args.fast_check)
    for candidate in candidates:
        handler = candidate(cli_args=args, bin_path=BIN_PATH)
        listing = handler.list_contents()
        if listing is not None:
            print(listing)
            return True
        logging.info(f"{candidate.__name__} does not support listing; trying next candidate.")

    logging.error(f"No candidate handler could list: {args.file_path}")
    return False

def process_carve(args):
    """
    Carve embedded blobs at binwalk offsets and extract them.

    Default: carve+extract every handler-known, non-generic blob.
    --raw: carve every fragment raw (binwalk extract-all), extracting where possible.
    --fragment N: carve only the fragment at index N (from --list).
    --list: just print the fragment table and exit.
    """
    entries = binwalk_file_map(args.file_path, BIN_PATH)
    if not entries:
        logging.error(f"Binwalk found nothing to carve in {args.file_path}")
        return False

    if getattr(args, 'list_fragments', False):
        for index, entry in enumerate(entries):
            print(f"[{index}] offset={entry.get('offset')} size={entry.get('size')} "
                  f"name={entry.get('name')}  {entry.get('description', '')}")
        return True

    if args.fragment is not None:
        if not 0 <= args.fragment < len(entries):
            logging.error(f"Fragment index {args.fragment} out of range (0..{len(entries) - 1})")
            return False
        selected = [(args.fragment, entries[args.fragment])]
    else:
        selected = list(enumerate(entries))

    # A specific fragment or --raw carves regardless of handler coverage.
    carve_all = args.raw or args.fragment is not None

    output_dir = str(args.output_dir) if args.output_dir else f"{args.file_path}_carved"
    os.makedirs(output_dir, exist_ok=True)
    with open(args.file_path, 'rb') as source_fh:
        data = source_fh.read()

    carved_any = False
    for index, entry in selected:
        name = (entry.get('name') or '').lower()
        offset = entry.get('offset', 0)
        size = entry.get('size') or 0
        if size <= 0:
            continue

        has_handler = bool(get_handler_from_detection(name)) and not is_generic_detection(name)
        if not carve_all and not has_handler:
            continue

        carved_path = os.path.join(output_dir, f"carved_{index}_{offset}_{name}.bin")
        with open(carved_path, 'wb') as carved_fh:
            carved_fh.write(data[offset:offset + size])
        logging.info(f"Carved [{index}] {name} at offset {offset} ({size} bytes) -> {carved_path}")
        carved_any = True

        # Attempt extraction only when a handler covers this blob type.
        if has_handler:
            nested_args = argparse.Namespace(
                file_path=pathlib.Path(carved_path), output_dir=None,
                fast_check=args.fast_check, password=getattr(args, 'password', None),
                recursive=False, open_output_folder=False,
            )
            process_extraction(nested_args)

    if not carved_any:
        logging.error(f"No matching data to carve in {args.file_path}")
    return carved_any

def run_extract(args):
    """Extract a single file, or every file in a directory (non-recursive)."""
    if args.file_path.is_dir():
        for item in args.file_path.iterdir():
            if item.is_file():
                logging.info(f"Processing file: {item}")

                # Create a temporary args instance for the current file
                temp_args = argparse.Namespace(**vars(args))
                temp_args.file_path = item
                if not process_extraction(temp_args):
                    logging.error(f"Extraction failed for file: {item}")

        return True

    return process_extraction(args)

def main():
    """Entry point: dispatch subcommands (extract, identify, ...)."""
    argv = sys.argv[1:]
    # Backward compatibility: a bare path (no subcommand) defaults to 'extract'.
    if argv and not argv[0].startswith('-') and argv[0] not in SUBCOMMANDS:
        argv = ["extract"] + argv

    parser = configure_parser()
    args = parser.parse_args(argv)
    setup_logging(args.debug)

    # Load the detection -> handler routing maps and the generic-token blacklist
    init_handlers(DATA_PATH)
    init_blacklist(DATA_PATH)

    if args.command == "identify":
        sys.exit(0 if process_identify(args) else 1)

    if args.command == "list":
        sys.exit(0 if process_list(args) else 1)

    if args.command == "carve":
        sys.exit(0 if process_carve(args) else 1)

    # extract
    config = Config()
    configure_settings(args, config)
    sys.exit(0 if run_extract(args) else 1)

if __name__ == "__main__":
    main()
