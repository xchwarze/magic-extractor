import logging
from .format_7z import Format7zHandler
from .format_rar import FormatRarHandler

# Dictionary mapping types to handler classes
MIME_HANDLERS = {
    # list from 7z readme
    'application/x-7z-compressed': Format7zHandler,
    'application/x-xz': Format7zHandler,
    'application/x-bzip2': Format7zHandler,
    'application/x-gzip': Format7zHandler,
    'application/x-tar': Format7zHandler,
    'application/zip': Format7zHandler,
    'application/x-ms-wim': Format7zHandler,
    'application/x-apfs-image': Format7zHandler,
    'application/x-archive': Format7zHandler,
    'application/x-arj': Format7zHandler,
    'application/vnd.ms-cab-compressed': Format7zHandler,
    'application/vnd.ms-htmlhelp': Format7zHandler,
    'application/x-cpio': Format7zHandler,
    'application/x-cramfs': Format7zHandler,
    'application/x-apple-diskimage': Format7zHandler,
    'application/x-extfs-image': Format7zHandler,
    'application/x-fatfs-image': Format7zHandler,
    'application/x-hfs': Format7zHandler,
    'application/x-iso9660-image': Format7zHandler,
    'application/x-lzh-compressed': Format7zHandler,
    'application/x-lzma': Format7zHandler,
    'application/x-msi': Format7zHandler,
    'application/x-nsis-package': Format7zHandler,
    'application/x-qemu-disk': Format7zHandler,
    'application/x-rpm': Format7zHandler,
    'application/x-squashfs': Format7zHandler,
    'application/x-udf': Format7zHandler,
    'application/x-virtualbox-vdi': Format7zHandler,
    'application/x-vhd': Format7zHandler,
    'application/x-vhdx': Format7zHandler,
    'application/x-vmdk': Format7zHandler,
    'application/x-xar': Format7zHandler,
    'application/x-compress': Format7zHandler,
    'application/zstd': Format7zHandler,

    # others
    'application/vnd.rar': FormatRarHandler,
}

DETECTION_HANDLERS = {
    '7-zip': Format7zHandler,
    'winrar': FormatRarHandler,
}

def get_handler_from_mime(mime_type):
    """Returns the appropriate handler class for a given MIME type."""
    logging.debug(f"Looking for a handler for this mime type: '{mime_type}'")
    handler_class = MIME_HANDLERS.get(mime_type)
    return handler_class if handler_class else None

def get_handler_from_detection(detection):
    """Returns the appropriate handler class based on a detection result."""
    logging.debug(f"Looking for a handler for this detection: '{detection}'")
    handler_class = DETECTION_HANDLERS.get(detection.lower())
    return handler_class if handler_class else None
