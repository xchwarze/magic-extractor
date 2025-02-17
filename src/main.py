import argparse
import logging
import sys
import os
import pathlib
from logger import setup_logging
from config import Config
from file_type import determine_file_type_with_magic, determine_file_type_with_binwalk, determine_file_type_with_die, determine_file_type_with_trid
from formats import get_handler_from_mime, get_handler_from_detection

# Define the path to the 'bin' directory
BIN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bin')

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

def configure_parser():
    """Configure and return the argument parser."""
    parser = argparse.ArgumentParser(description="Universal Extractor for various file formats")
    parser.add_argument("file_path", help="Path to the file or directory to be extracted", type=file_path_type_check)
    parser.add_argument("output_dir", help="Directory to extract the file to", type=dir_path_type_check, nargs='?', default=None)
    parser.add_argument("--password", help="Password for encrypted files, required by some extractors", type=str, default=None)
    parser.add_argument("--debug", help="Enable debug logging", action="store_true")
    parser.add_argument("--update-defaults", help="Update default configuration values", action="store_true")

    # Configurable settings as command-line options
    parser.add_argument("--open-output-folder", help="Open output folder after extraction", type=bool, default=None)
    parser.add_argument("--check-free-space", help="Check disk space before extraction", type=bool, default=None)
    parser.add_argument("--extract-video-tracks", help="Extract video tracks if available", type=bool, default=None)
    parser.add_argument("--warn-before-executing", help="Warn before executing any executable file", type=bool, default=None)
    parser.add_argument("--check-unicode", help="Check for unicode characters in file names", type=bool, default=None)
    parser.add_argument("--fix-file-extensions", help="Automatically fix file extensions", type=bool, default=None)
    parser.add_argument("--create-log-files", help="Create log files of the operations", type=bool, default=None)
    parser.add_argument("--no-fast-check", help="Disable fast type check", action='store_false', dest='fast_check')

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

def find_candidate_handlers(file_path, fast_check):
    """Return a list of candidate handler classes based on file type detection."""
    candidates = []

    # MIME type detection
    mime_types = determine_file_type_with_magic(file_path=file_path, fast_check=fast_check)
    if mime_types:
        for mime_type in mime_types:
            handler_class = get_handler_from_mime(mime_type=mime_type)
            if handler_class and handler_class not in candidates:
                logging.info(f"Candidate handler for MIME type: {mime_type}")
                candidates.append(handler_class)

    # Binwalk detection
    detection_results = determine_file_type_with_binwalk(file_path=file_path, bin_path=BIN_PATH)
    if detection_results:
        for detection in detection_results:
            handler_class = get_handler_from_detection(detection=detection)
            if handler_class and handler_class not in candidates:
                logging.info(f"Candidate handler for detection: {detection}")
                candidates.append(handler_class)

    # DIE detection
    detection_results = determine_file_type_with_die(file_path=file_path, bin_path=BIN_PATH)
    if detection_results:
        for detection in detection_results:
            handler_class = get_handler_from_detection(detection=detection)
            if handler_class and handler_class not in candidates:
                logging.info(f"Candidate handler for detection: {detection}")
                candidates.append(handler_class)

    # TRiD detection
    detection_results = determine_file_type_with_trid(file_path=file_path, bin_path=BIN_PATH)
    if detection_results:
        for detection in detection_results:
            handler_class = get_handler_from_detection(detection=detection)
            if handler_class and handler_class not in candidates:
                logging.info(f"Candidate handler for detection: {detection}")
                candidates.append(handler_class)

    return candidates

def process_extraction(args):
    """
    Process file extraction by iterating over candidate handlers.
    Waits for a handler to return True from extract().
    """
    candidates = find_candidate_handlers(file_path=args.file_path, fast_check=args.fast_check)
    for candidate in candidates:
        handler = candidate(cli_args=args, bin_path=BIN_PATH)
        handler.pre_extract_actions()
        if handler.extract():
            handler.post_extract_actions()
            logging.info("Extraction completed successfully.")
            return True
        else:
            logging.error(f"Extraction failed using handler: {candidate.__name__}")

    logging.error(f"No handler succeeded for file: {args.file_path}")
    return False

def main():
    """Main function to handle file extraction for a file or a directory of files."""
    parser = configure_parser()
    args = parser.parse_args()
    setup_logging(args.debug)

    config = Config()
    configure_settings(args, config)

    # Process a directory by iterating over its files (non-recursive)
    if args.file_path.is_dir():
        for item in args.file_path.iterdir():
            if item.is_file():
                logging.info(f"Processing file: {item}")

                # Create a temporary args instance for the current file
                temp_args = argparse.Namespace(**vars(args))
                temp_args.file_path = item
                if not process_extraction(temp_args):
                    logging.error(f"Extraction failed for file: {item}")

        sys.exit(0)
    else:
        success = process_extraction(args)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
