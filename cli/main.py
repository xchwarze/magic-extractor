"""Magic Extractor command-line entry point."""

import sys

from arguments import (
    SUBCOMMANDS,
    configure_parser,
    configure_settings,
    dir_path_type_check,
    file_path_type_check,
    str2bool,
)
from carving import process_carve
from cli_paths import BIN_PATH, CONFIG_PATH, DATA_PATH
from commands import process_identify, process_list
from config import Config
from detection import (
    PE_INSTALLER_FALLBACK,
    append_pe_installer_fallbacks as _append_pe_installer_fallbacks,
    candidates_from_outputs as _candidates_from_outputs,
    collect_candidates as _collect_candidates,
    detector_outputs as _detector_outputs,
    find_candidate_handlers,
    is_pe as _is_pe,
)
from detection_filter import init_blacklist
from extraction import (
    confirm_run_installer,
    extract_nested,
    process_extraction,
    run_extract,
)
from formats import init_handlers
from logger import setup_logging


def main():
    """Parse arguments, initialize runtime data, and dispatch a subcommand."""
    argv = sys.argv[1:]
    if argv and not argv[0].startswith("-") and argv[0] not in SUBCOMMANDS:
        argv = ["extract"] + argv

    parser = configure_parser()
    args = parser.parse_args(argv)
    setup_logging(args.debug)

    init_handlers(DATA_PATH)
    init_blacklist(DATA_PATH)

    if args.command == "identify":
        return 0 if process_identify(args) else 1
    if args.command == "list":
        return 0 if process_list(args) else 1
    if args.command == "carve":
        return 0 if process_carve(args) else 1

    config = Config(CONFIG_PATH)
    configure_settings(args, config)
    args.delete_to_recycle_bin = config.get(
        "settings", "delete_to_recycle_bin", fallback=True, type=bool
    )
    return 0 if run_extract(args) else 1


if __name__ == "__main__":
    sys.exit(main())
