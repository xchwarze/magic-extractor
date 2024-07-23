import argparse
import logging
import sys
import os
import pathlib
from logger import setup_logging
from config import Config
from file_type import determine_file_type_with_magic, determine_file_type_with_trid, determine_file_type_with_trid_dll, determine_file_type_with_die
from formats import get_handler_from_mime

# Define the path to the 'bin' directory
BIN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'bin')

def file_path_type_check(path):
    """Custom argparse type to check if a file exists."""
    if not pathlib.Path(path).is_file():
        raise argparse.ArgumentTypeError(f"The file {path} does not exist.")

    return pathlib.Path(path)

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
    parser.add_argument("file_path", help="Path to the file to be extracted", type=file_path_type_check)
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
    parser.add_argument("--fast-check", help="Perform a fast type check by reading only the first 2048 bytes", action='store_true', default=None)
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

def main():
    """Main function to handle file extraction based on command line arguments and configurable settings."""
    parser = configure_parser()
    args = parser.parse_args()
    setup_logging(args.debug)

    config = Config()
    configure_settings(args, config)

    file_type = determine_file_type_with_magic(file_path=args.file_path, fast_check=args.fast_check)
    
    ### debug
    #########################
    logging.debug(
        determine_file_type_with_trid(file_path=args.file_path, bin_path=BIN_PATH)
    )
    #logging.debug(
    #    determine_file_type_with_trid_dll(file_path=args.file_path, bin_path=BIN_PATH)
    #)
    logging.debug(
        determine_file_type_with_die(file_path=args.file_path, bin_path=BIN_PATH)
    )
    #########################

    handler_class = get_handler_from_mime(mime_type=file_type)
    if handler_class:
        handler = handler_class(cli_args=args, bin_path=BIN_PATH)
        success = handler.extract()
        if success:
            logging.info("Extraction completed successfully.")
            sys.exit(0)  # Success exit code
        else:
            logging.error("Extraction failed.")
            sys.exit(1)  # Error exit code
    else:
        logging.error(f"No suitable handler found for the file: {args.file_path}")
        sys.exit(1)  # Error exit code if no handler is found

if __name__ == "__main__":
    main()
