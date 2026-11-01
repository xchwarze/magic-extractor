import os
import json
import logging
from .format_7z import Format7zHandler
from .format_7z_ext import Format7zExtHandler
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
from .format_innosetup import FormatInnoSetupHandler
from .format_msi import FormatMsiHandler
from .format_bitrock import FormatBitrockHandler
from .format_cicdec import FormatCicdecHandler
from .format_dgca import FormatDgcaHandler
from .format_wix import FormatWixHandler
from .format_installshield import FormatInstallShieldHandler
from .format_lzip import FormatLzipHandler

# Registry mapping the handler class names used in data/handlers.json to the classes.
# The extraction logic lives in code (format_*.py); only the routing map is data.
# The order is also the routing priority when several handlers claim the same
# MIME/detection key: they become candidates in this order, and the next one is
# only tried if the previous one fails.
_HANDLER_CLASSES = (
    Format7zHandler, Format7zExtHandler, FormatRarHandler, FormatAceHandler, FormatKgbHandler,
    FormatUharcHandler, FormatZpaqHandler, FormatAlzipHandler, FormatEggHandler,
    FormatBcmHandler, FormatArcHandler, FormatPeaHandler, FormatInnoSetupHandler,
    FormatMsiHandler, FormatBitrockHandler, FormatCicdecHandler, FormatDgcaHandler,
    FormatWixHandler, FormatInstallShieldHandler,
    FormatLzipHandler,
)
HANDLER_REGISTRY = {cls.__name__: cls for cls in _HANDLER_CLASSES}

# Populated at runtime from data/handlers.json via init_handlers().
MIME_HANDLERS = {}
DETECTION_HANDLERS = {}

def _resolve_map(raw):
    """
    Resolve a {key: class_name | [class_name, ...]} map to
    {lowercased_key: (handler_class, ...)}, keeping the priority order.
    """
    resolved = {}
    for key, class_names in raw.items():
        if isinstance(class_names, str):
            class_names = [class_names]
        handler_classes = []
        for class_name in class_names:
            handler_class = HANDLER_REGISTRY.get(class_name)
            if handler_class is None:
                logging.error(f"Unknown handler class '{class_name}' for key '{key}' in handlers.json")
                continue
            handler_classes.append(handler_class)
        if handler_classes:
            resolved[key.lower()] = tuple(handler_classes)
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

def get_handlers_from_mime(mime_type):
    """Returns the handler classes for a given MIME type, in priority order (empty if none)."""
    logging.debug(f"Looking for handlers for this mime type: '{mime_type}'")
    return MIME_HANDLERS.get(mime_type.lower(), ())

def get_handlers_from_detection(detection):
    """Returns the handler classes for a detection result, in priority order (empty if none)."""
    logging.debug(f"Looking for handlers for this detection: '{detection}'")
    return DETECTION_HANDLERS.get(detection.lower(), ())
