import argparse
import logging
import sys
import os
import pathlib
from logger import setup_logging
from config import Config
from file_type import determine_file_type_with_magic, determine_file_type_with_signatures, determine_file_type_with_binwalk, determine_file_type_with_die, determine_file_type_with_magika, binwalk_file_map
from formats import init_handlers, get_handler_from_mime, get_handler_from_detection, HANDLER_REGISTRY
from detection_filter import init_blacklist, filter_mimes, filter_detections, is_generic_detection
from helpers import delete_source

# Resolve the base path (frozen-exe aware) so 'bin' and 'data' stay external and updatable.
# When frozen by PyInstaller they live beside the executable; in dev they live under 'src'.
if getattr(sys, "frozen", False):
    BASE_PATH = os.path.dirname(sys.executable)
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))

BIN_PATH = os.path.join(BASE_PATH, 'bin')
DATA_PATH = os.path.join(BASE_PATH, 'data')
CONFIG_PATH = os.path.join(BASE_PATH, 'config.ini')

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
    extract_parser.add_argument("--check-unicode", help="Check for unicode characters in file names", type=bool, default=None)
    extract_parser.add_argument("--fix-file-extensions", help="Automatically fix file extensions", type=bool, default=None)
    extract_parser.add_argument("--create-log-files", help="Create log files of the operations", type=bool, default=None)
    extract_parser.add_argument("-r", "--recursive", help="Recursively extract archives found inside the output", action="store_true")
    extract_parser.add_argument("--max-depth", help="Maximum recursion depth for --recursive", type=int, default=5)
    extract_parser.add_argument("-b", "--bruteforce", help="Try every handler DIE and Magika detect (no early-exit)", action="store_true")
    extract_parser.add_argument("--delete-source", help="Delete the source file after a successful extraction (Recycle Bin unless delete_to_recycle_bin is off)", action="store_true")

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
    keys = ["open_output_folder", "check_free_space",
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
    Yield (source, mime_list, detection_list) per detector, lazily so callers can
    stop early. Each detector contributes uniquely: puremagic (free MIME for clean
    archives), built-in signatures (magic bytes for BCM/DGCA/KGB/UHARC), DIE
    (installers / PE / SFX), binwalk (short type keys), Magika (AI catch-all).
    Cheapest first; Magika (ML) last so early-exit usually avoids it.
    """
    mime_types = determine_file_type_with_magic(file_path=file_path, fast_check=fast_check)
    yield ("puremagic", list(mime_types) if mime_types else [], [])

    for source, detector in (
        ("signatures", determine_file_type_with_signatures),
        ("DIE", determine_file_type_with_die),
        ("binwalk", determine_file_type_with_binwalk),
    ):
        detections = detector(file_path=file_path, bin_path=BIN_PATH)
        yield (source, [], detections or [])

    magika_result = determine_file_type_with_magika(file_path=file_path, bin_path=BIN_PATH)
    yield (
        "Magika",
        magika_result["mime_types"] if magika_result else [],
        magika_result["labels"] if magika_result else [],
    )

def _collect_candidates(output, candidates):
    """Resolve one detector output into handler candidates; return True if any were added."""
    source, mimes, detections = output
    added = False
    for mime_type in filter_mimes(mimes):
        handler_class = get_handler_from_mime(mime_type=mime_type)
        if handler_class and handler_class not in candidates:
            logging.info(f"Candidate handler from {source} MIME: {mime_type}")
            candidates.append(handler_class)
            added = True

    for detection in filter_detections(detections):
        handler_class = get_handler_from_detection(detection=detection)
        if handler_class and handler_class not in candidates:
            logging.info(f"Candidate handler from {source} detection: {detection}")
            candidates.append(handler_class)
            added = True

    return added

def _candidates_from_outputs(outputs):
    """Resolve all detector outputs to an ordered, deduped list of handler classes."""
    candidates = []
    for output in outputs:
        _collect_candidates(output, candidates)
    return candidates

# Self-extracting / wrapped-exe archives and installers look like a generic PE
# to content detectors. Their tools each validate their own format and fail
# cleanly on a mismatch, so they are tried as last-resort candidates for any PE
# that nothing more specific matched. 7z is deliberately excluded: it opens any
# PE as an "archive" (dumping its sections), which would short-circuit the
# format-specific handlers.
PE_INSTALLER_FALLBACK = (
    'FormatInnoSetupHandler', 'FormatRarHandler', 'FormatAceHandler',
    'FormatArcHandler', 'FormatKgbHandler', 'FormatUharcHandler',
    'FormatBitrockHandler', 'FormatCicdecHandler', 'FormatPyInstallerHandler',
)

def _is_pe(file_path):
    """True if the file starts with the 'MZ' DOS/PE signature."""
    try:
        with open(file_path, 'rb') as probe:
            return probe.read(2) == b'MZ'
    except OSError:
        return False

def confirm_run_installer(file_path):
    """
    Confirm before extracting by RUNNING the original installer with parameters.

    Reserved for handlers that execute the installer itself (none do yet — the
    current handlers all parse the file with external tools). Prompts on a tty;
    non-interactive callers are warned via the log and allowed to proceed.
    """
    logging.warning(f"About to run installer to extract: {file_path}")
    if not sys.stdin.isatty():
        return True
    try:
        answer = input("Run it anyway? [y/N] ")
    except EOFError:
        return True
    return answer.strip().lower() in ('y', 'yes')

def _append_pe_installer_fallbacks(file_path, candidates):
    """Wrapped-exe installers can't be identified by content; try them on any PE."""
    if not _is_pe(file_path):
        return
    for name in PE_INSTALLER_FALLBACK:
        handler_class = HANDLER_REGISTRY.get(name)
        if handler_class and handler_class not in candidates:
            logging.info(f"PE installer fallback candidate: {name}")
            candidates.append(handler_class)

def find_candidate_handlers(file_path, fast_check, bruteforce=False):
    """
    Return candidate handler classes. By default stops at the first detector that
    yields a mapped handler (early-exit). In bruteforce mode every detector runs
    and all candidates are returned, so extraction tries everything DIE and Magika
    detect. PE-installer fallbacks are always appended for executables.
    """
    candidates = []
    for output in _detector_outputs(file_path, fast_check):
        added = _collect_candidates(output, candidates)
        if added and not bruteforce:
            break  # early-exit: first detector with a mapped handler wins

    _append_pe_installer_fallbacks(file_path, candidates)
    return candidates

def process_extraction(args, depth=0):
    """
    Process file extraction by iterating over candidate handlers.
    Waits for a handler to return True from extract(). When --recursive is set,
    archives found inside the output are extracted too, up to --max-depth.
    """
    candidates = find_candidate_handlers(file_path=args.file_path, fast_check=args.fast_check,
                                         bruteforce=getattr(args, 'bruteforce', False))
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
    outputs = list(_detector_outputs(args.file_path, args.fast_check))
    print(f"File: {args.file_path}")
    for source, mimes, detections in outputs:
        for mime_type in filter_mimes(mimes):
            print(f"  [{source}] MIME     {mime_type}")
        for detection in filter_detections(detections):
            print(f"  [{source}] detect   {detection}")

    candidates = _candidates_from_outputs(outputs)
    _append_pe_installer_fallbacks(args.file_path, candidates)  # match extract's behavior
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
        print(f"{'IDX':>3}  {'OFFSET':>10}  {'SIZE':>12}  {'NAME':<20}  DESCRIPTION")
        print(f"{'-' * 3}  {'-' * 10}  {'-' * 12}  {'-' * 20}  {'-' * 11}")
        for index, entry in enumerate(entries):
            offset = entry.get('offset', 0) or 0
            size = entry.get('size', 0) or 0
            name = (entry.get('name') or '')
            description = (entry.get('description') or '')
            print(f"{index:>3}  {offset:#010x}  {size:>12,}  {name:<20.20}  {description}")
        print(f"\n{len(entries)} fragment(s).")
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
    delete_after = getattr(args, 'delete_source', False)
    use_recycle_bin = getattr(args, 'delete_to_recycle_bin', True)

    if args.file_path.is_dir():
        for item in args.file_path.iterdir():
            if item.is_file():
                logging.info(f"Processing file: {item}")

                # Create a temporary args instance for the current file
                temp_args = argparse.Namespace(**vars(args))
                temp_args.file_path = item
                if process_extraction(temp_args):
                    if delete_after:
                        delete_source(item, use_recycle_bin)
                else:
                    logging.error(f"Extraction failed for file: {item}")

        return True

    result = process_extraction(args)
    if result and delete_after:
        delete_source(args.file_path, use_recycle_bin)
    return result

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
    config = Config(CONFIG_PATH)
    configure_settings(args, config)
    args.delete_to_recycle_bin = config.get('settings', 'delete_to_recycle_bin', fallback=True, type=bool)
    sys.exit(0 if run_extract(args) else 1)

if __name__ == "__main__":
    main()
