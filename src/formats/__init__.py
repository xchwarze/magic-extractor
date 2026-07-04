import os
import json
import logging
from .format_7z import Format7zHandler
from .format_rar import FormatRarHandler
from .format_ace import FormatAceHandler
from .format_kgb import FormatKgbHandler
from .format_uharc import FormatUharcHandler
from .format_zpaq import FormatZpaqHandler
from .format_alzip import FormatAlzipHandler
from .format_egg import FormatEggHandler
from .format_bcm import FormatBcmHandler
from .format_arc import FormatArcHandler
from .format_pea import FormatPeaHandler
from .format_exe_innosetup import FormatInnoSetupHandler
from .format_exe_msi import FormatMsiHandler

# Registry mapping the handler class names used in data/handlers.json to the classes.
# The extraction logic lives in code (format_*.py); only the routing map is data.
_HANDLER_CLASSES = (
    Format7zHandler, FormatRarHandler, FormatAceHandler, FormatKgbHandler,
    FormatUharcHandler, FormatZpaqHandler, FormatAlzipHandler, FormatEggHandler,
    FormatBcmHandler, FormatArcHandler, FormatPeaHandler, FormatInnoSetupHandler,
    FormatMsiHandler,
)
HANDLER_REGISTRY = {cls.__name__: cls for cls in _HANDLER_CLASSES}

# Populated at runtime from data/handlers.json via init_handlers().
MIME_HANDLERS = {}
DETECTION_HANDLERS = {}

def _resolve_map(raw):
    """Resolve a {key: handler_class_name} map to {lowercased_key: handler_class}."""
    resolved = {}
    for key, class_name in raw.items():
        handler_class = HANDLER_REGISTRY.get(class_name)
        if handler_class is None:
            logging.error(f"Unknown handler class '{class_name}' for key '{key}' in handlers.json")
            continue
        resolved[key.lower()] = handler_class
    return resolved

def init_handlers(data_path):
    """Load the MIME/detection -> handler routing maps from data/handlers.json."""
    global MIME_HANDLERS, DETECTION_HANDLERS
    handlers_file = os.path.join(data_path, 'handlers.json')
    try:
        with open(handlers_file, encoding='utf-8') as handlers_fh:
            data = json.load(handlers_fh)
    except (OSError, json.JSONDecodeError) as exc:
        logging.error(f"Failed to load handlers map from {handlers_file}: {exc}")
        MIME_HANDLERS, DETECTION_HANDLERS = {}, {}
        return

    MIME_HANDLERS = _resolve_map(data.get('mime_handlers', {}))
    DETECTION_HANDLERS = _resolve_map(data.get('detection_handlers', {}))
    logging.debug(f"Loaded {len(MIME_HANDLERS)} MIME and {len(DETECTION_HANDLERS)} detection handlers")

def get_handler_from_mime(mime_type):
    """Returns the appropriate handler class for a given MIME type."""
    logging.debug(f"Looking for a handler for this mime type: '{mime_type}'")
    return MIME_HANDLERS.get(mime_type.lower())

def get_handler_from_detection(detection):
    """Returns the appropriate handler class based on a detection result."""
    logging.debug(f"Looking for a handler for this detection: '{detection}'")
    return DETECTION_HANDLERS.get(detection.lower())
