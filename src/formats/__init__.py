import logging
from .format_7z import Format7zHandler
from .format_rar import FormatRarHandler

# Dictionary mapping types to handler classes
MIME_HANDLERS = {
    'application/x-7z-compressed': Format7zHandler,
    'application/vnd.rar': FormatRarHandler,
}

EXTENSION_HANDLERS = {
    '.exe': {
        '7-zip': Format7zHandler,
        'winrar': FormatRarHandler,
        'rar': FormatRarHandler,
    },
}

def get_handler_from_mime(mime_type):
    """Returns the appropriate handler class for a given MIME type."""
    logging.info(f"Looking for a handler for this mime type: '{mime_type}'")
    handler_class = MIME_HANDLERS.get(mime_type)
    return handler_class if handler_class else None
