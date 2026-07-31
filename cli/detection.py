"""File detection and ordered handler candidate selection."""

import logging

from cli_paths import BIN_PATH
from detection_filter import filter_detections, filter_mimes
from file_type import (
    determine_file_type_with_binwalk,
    determine_file_type_with_die,
    determine_file_type_with_magika,
    determine_file_type_with_magic,
    determine_file_type_with_signatures,
)
from formats import HANDLER_REGISTRY, get_handler_from_detection, get_handler_from_mime


PE_INSTALLER_FALLBACK = (
    "FormatRarHandler",
    "FormatAceHandler",
    "FormatArcHandler",
    "FormatKgbHandler",
    "FormatUharcHandler",
    "FormatInnoSetupHandler",
    "FormatBitrockHandler",
    "FormatCicdecHandler",
)


def detector_outputs(file_path, fast_check):
    """Yield each detector's MIME types and labels, cheapest detector first."""
    mime_types = determine_file_type_with_magic(
        file_path=file_path, fast_check=fast_check
    )
    yield ("puremagic", list(mime_types) if mime_types else [], [])

    for source, detector in (
        ("signatures", determine_file_type_with_signatures),
        ("DIE", determine_file_type_with_die),
        ("binwalk", determine_file_type_with_binwalk),
    ):
        detections = detector(file_path=file_path, bin_path=BIN_PATH)
        yield (source, [], detections or [])

    magika_result = determine_file_type_with_magika(
        file_path=file_path, bin_path=BIN_PATH
    )
    yield (
        "Magika",
        magika_result["mime_types"] if magika_result else [],
        magika_result["labels"] if magika_result else [],
    )


def collect_candidates(output, candidates):
    """Resolve one detector output into candidates; return whether any were added."""
    source, mimes, detections = output
    added = False
    for mime_type in filter_mimes(mimes):
        handler_class = get_handler_from_mime(mime_type=mime_type)
        if handler_class and handler_class not in candidates:
            logging.info(f"Candidate handler from {source} MIME: {mime_type}")
            candidates.append(handler_class)
            added = True

    for detected_type in filter_detections(detections):
        handler_class = get_handler_from_detection(detection=detected_type)
        if handler_class and handler_class not in candidates:
            logging.info(
                f"Candidate handler from {source} detection: {detected_type}"
            )
            candidates.append(handler_class)
            added = True
    return added


def candidates_from_outputs(outputs):
    """Resolve all detector outputs to an ordered, deduplicated candidate list."""
    candidates = []
    for output in outputs:
        collect_candidates(output, candidates)
    return candidates


def is_pe(file_path):
    """Return whether a file starts with the DOS/PE ``MZ`` signature."""
    try:
        with open(file_path, "rb") as probe:
            return probe.read(2) == b"MZ"
    except OSError:
        return False


def append_pe_installer_fallbacks(file_path, candidates):
    """Append strict archive and installer fallbacks for PE files."""
    if not is_pe(file_path):
        return
    for name in PE_INSTALLER_FALLBACK:
        handler_class = HANDLER_REGISTRY.get(name)
        if handler_class and handler_class not in candidates:
            logging.info(f"PE installer fallback candidate: {name}")
            candidates.append(handler_class)


def find_candidate_handlers(file_path, fast_check, bruteforce=False):
    """Return ordered candidates, stopping at the first mapped detector by default."""
    candidates = []
    for output in detector_outputs(file_path, fast_check):
        added = collect_candidates(output, candidates)
        if added and not bruteforce:
            break

    append_pe_installer_fallbacks(file_path, candidates)
    return candidates
