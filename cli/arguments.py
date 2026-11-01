"""Argument parsing and configuration-backed CLI settings."""

import argparse
import os
import pathlib


SUBCOMMANDS = ("extract", "identify", "list", "carve")


# Options that take a value (`--password pw`): the value is never a subcommand
# or the file path. Kept in sync with configure_parser() by a unit test.
VALUE_OPTIONS = frozenset((
    "--password", "--max-depth", "--open-output-folder", "--check-free-space",
    "--check-unicode", "--fix-file-extensions", "--create-log-files", "--fragment",
))


def normalize_argv(argv):
    """
    Default to the extract subcommand and let options come before it, so
    `main.py file.zip`, `main.py --debug file.zip` and `main.py --password pw
    list file.zip` all parse. The subcommand is only looked for before the
    first positional argument (a file path never becomes a subcommand).
    """
    skip_value = False
    for index, arg in enumerate(argv):
        if skip_value:
            skip_value = False
            continue
        if arg in SUBCOMMANDS:
            return [arg] + argv[:index] + argv[index + 1:]
        if arg in VALUE_OPTIONS:
            skip_value = True
            continue
        if not arg.startswith("-"):
            break
    if argv and not set(argv) <= {"-h", "--help"}:
        return ["extract"] + argv
    return argv


def file_path_type_check(path):
    """Check that an input file or directory exists."""
    input_path = pathlib.Path(path)
    if not (input_path.is_file() or input_path.is_dir()):
        raise argparse.ArgumentTypeError(
            f"The path {path} does not exist or is not a file/directory."
        )
    return input_path


def dir_path_type_check(path):
    """
    Check an output directory without creating it: it is created when it is
    actually used, so a run that extracts nothing leaves no empty folder.
    """
    dir_path = pathlib.Path(path)
    if dir_path.exists() and not dir_path.is_dir():
        raise argparse.ArgumentTypeError(f"{path} exists and is not a directory.")
    if dir_path.is_dir() and not os.access(dir_path, os.W_OK):
        raise argparse.ArgumentTypeError(f"The directory {path} is not writable.")
    return dir_path


def str2bool(value):
    """Parse a real boolean option instead of relying on ``bool(str)``."""
    lowered = value.strip().lower()
    if lowered in ("true", "1", "yes", "y", "on"):
        return True
    if lowered in ("false", "0", "no", "n", "off"):
        return False
    raise argparse.ArgumentTypeError(
        f"expected a boolean (true/false), got {value!r}"
    )


def configure_parser():
    """Configure and return the subcommand argument parser."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--debug", help="Enable debug logging", action="store_true")
    common.add_argument(
        "--fast-check",
        help="Check only the first 64 KiB with PureMagic",
        action="store_true",
        default=None,
    )

    parser = argparse.ArgumentParser(
        description="Universal Extractor for various file formats"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser(
        "extract", parents=[common], help="Detect and extract an archive"
    )
    extract_parser.add_argument(
        "file_path",
        help="Path to the file or directory to be extracted",
        type=file_path_type_check,
    )
    extract_parser.add_argument(
        "output_dir",
        help="Directory to extract the file to",
        type=dir_path_type_check,
        nargs="?",
        default=None,
    )
    extract_parser.add_argument(
        "--password",
        help="Password for encrypted files, required by some extractors",
        type=str,
        default=None,
    )
    extract_parser.add_argument(
        "--update-defaults",
        help="Update default configuration values",
        action="store_true",
    )
    extract_parser.add_argument(
        "--open-output-folder",
        help="Open output folder after extraction (true/false)",
        type=str2bool,
        default=None,
    )
    extract_parser.add_argument(
        "--check-free-space",
        help="Check disk space before extraction (true/false)",
        type=str2bool,
        default=None,
    )
    extract_parser.add_argument(
        "--check-unicode",
        help="Check for unicode characters in file names (true/false)",
        type=str2bool,
        default=None,
    )
    extract_parser.add_argument(
        "--fix-file-extensions",
        help="Automatically fix file extensions (true/false)",
        type=str2bool,
        default=None,
    )
    extract_parser.add_argument(
        "--create-log-files",
        help="Create log files of the operations (true/false)",
        type=str2bool,
        default=None,
    )
    extract_parser.add_argument(
        "-r",
        "--recursive",
        help="Recursively extract archives found inside the output",
        action="store_true",
    )
    extract_parser.add_argument(
        "--max-depth",
        help="Maximum recursion depth for --recursive",
        type=int,
        default=5,
    )
    extract_parser.add_argument(
        "-b",
        "--bruteforce",
        help="Try every handler DIE and Magika detect (no early-exit)",
        action="store_true",
    )
    extract_parser.add_argument(
        "--delete-source",
        help=(
            "Delete the source file after a successful extraction "
            "(Recycle Bin unless delete_to_recycle_bin is off)"
        ),
        action="store_true",
    )

    identify_parser = subparsers.add_parser(
        "identify",
        parents=[common],
        help="Detect file type and candidate handlers without extracting",
    )
    identify_parser.add_argument(
        "file_path", help="Path to the file to identify", type=file_path_type_check
    )

    list_parser = subparsers.add_parser(
        "list", parents=[common], help="List archive contents without extracting"
    )
    list_parser.add_argument(
        "file_path", help="Path to the archive to list", type=file_path_type_check
    )
    list_parser.add_argument(
        "--password",
        help="Password for encrypted files, required by some extractors",
        type=str,
        default=None,
    )

    carve_parser = subparsers.add_parser(
        "carve",
        parents=[common],
        help="Carve embedded archives at binwalk offsets and extract them",
    )
    carve_parser.add_argument(
        "file_path", help="Path to the file to carve", type=file_path_type_check
    )
    carve_parser.add_argument(
        "output_dir",
        help="Directory to write carved segments to",
        type=dir_path_type_check,
        nargs="?",
        default=None,
    )
    carve_parser.add_argument(
        "--password",
        help="Password for encrypted files, required by some extractors",
        type=str,
        default=None,
    )
    carve_parser.add_argument(
        "--list",
        help="List binwalk fragments (index, offset, size, name) and exit",
        action="store_true",
        dest="list_fragments",
    )
    carve_parser.add_argument(
        "--fragment",
        help="Carve only the fragment at this index (see --list)",
        type=int,
        default=None,
    )
    carve_parser.add_argument(
        "--raw",
        help="Carve every fragment raw (binwalk extract-all), not only handler-known ones",
        action="store_true",
    )
    return parser


def configure_settings(args, config):
    """Update persisted defaults when requested, then apply effective settings."""
    keys = [
        "open_output_folder",
        "check_free_space",
        "check_unicode",
        "fix_file_extensions",
        "create_log_files",
        "fast_check",
    ]

    # Subcommands only carry some of these options (identify/list/carve just
    # --fast-check); fill in the ones they have.
    keys = [key for key in keys if hasattr(args, key)]

    if getattr(args, "update_defaults", False):
        for key in keys:
            value = getattr(args, key)
            if value is not None:
                config.set("settings", key, str(value))
        config.save()

    for key in keys:
        if getattr(args, key) is None:
            setattr(args, key, config.get("settings", key, type=bool))
