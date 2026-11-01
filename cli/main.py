"""Magic Extractor command-line entry point."""

import sys

from arguments import (
    SUBCOMMANDS,
    configure_parser,
    configure_settings,
    dir_path_type_check,
    file_path_type_check,
    normalize_argv,
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
    extract_nested,
    process_extraction,
    run_extract,
)
from formats import init_handlers
from logger import setup_logging


def use_utf8_output():
    """
    Write stdout/stderr as UTF-8 (bad characters replaced). Piped output
    otherwise uses the ANSI code page, so `identify` on a file named e.g.
    "архив.zip" crashed with UnicodeEncodeError under the GUI, which reads
    the CLI's output as UTF-8.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def main():
    """Parse arguments, initialize runtime data, and dispatch a subcommand."""
    use_utf8_output()
    parser = configure_parser()
    args = parser.parse_args(normalize_argv(sys.argv[1:]))
    setup_logging(args.debug)

    init_handlers(DATA_PATH)
    init_blacklist(DATA_PATH)

    # Every subcommand honors config.ini (e.g. fast_check), not only extract.
    config = Config(CONFIG_PATH)
    configure_settings(args, config)

    if args.command == "identify":
        return 0 if process_identify(args) else 1
    if args.command == "list":
        return 0 if process_list(args) else 1
    if args.command == "carve":
        return 0 if process_carve(args) else 1

    args.delete_to_recycle_bin = config.get(
        "settings", "delete_to_recycle_bin", fallback=True, type=bool
    )
    return 0 if run_extract(args) else 1


if __name__ == "__main__":
    sys.exit(main())
