import os
import json
import logging

# Generic / noise detector outputs, loaded from data/detection_blacklist.json.
# These must never produce a handler candidate even if a stray entry maps them.
_MIME_BLACKLIST = set()
_DETECTION_EXACT = set()
_DETECTION_SUBSTRINGS = []

def init_blacklist(data_path):
    """Load the generic-token blacklist from data/detection_blacklist.json."""
    global _MIME_BLACKLIST, _DETECTION_EXACT, _DETECTION_SUBSTRINGS
    blacklist_file = os.path.join(data_path, 'detection_blacklist.json')
    try:
        with open(blacklist_file, encoding='utf-8') as blacklist_fh:
            data = json.load(blacklist_fh)
    except (OSError, json.JSONDecodeError) as exc:
        logging.error(f"Failed to load detection blacklist from {blacklist_file}: {exc}")
        return

    _MIME_BLACKLIST = {value.lower() for value in data.get('mime', [])}
    _DETECTION_EXACT = {value.lower() for value in data.get('detection_exact', [])}
    _DETECTION_SUBSTRINGS = [value.lower() for value in data.get('detection_substrings', [])]

def is_generic_mime(mime_type):
    """True if the MIME type is a generic/noise token that should be ignored."""
    return mime_type.lower() in _MIME_BLACKLIST

def is_generic_detection(detection):
    """True if the detection string is a generic/noise token that should be ignored."""
    value = detection.lower()
    return value in _DETECTION_EXACT or any(sub in value for sub in _DETECTION_SUBSTRINGS)

def filter_mimes(mime_types):
    """Drop generic/noise MIME types."""
    return [value for value in mime_types if not is_generic_mime(value)]

def filter_detections(detections):
    """Drop generic/noise detection strings."""
    return [value for value in detections if not is_generic_detection(value)]
