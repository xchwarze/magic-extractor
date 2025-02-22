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
    'application/x-ace': FormatAceHandler,
    'application/x-alz': FormatAlzipHandler,
}

DETECTION_HANDLERS = {
    # sfx
    '7-zip': Format7zHandler,
    'winrar': FormatRarHandler,
    'winace': FormatAceHandler,

    # compresor
    'kgb archiver compressed archive': FormatKgbHandler,
    'uharc compressed archive': FormatUharcHandler,
    'zpaq compressed archive (.zpaq)': FormatZpaqHandler,
    'egg compressed archive': FormatEggHandler,
    'bcm compressed archive': FormatBcmHandler,
    'freearc compressed archive': FormatArcHandler,
    'pea compressed archive (v1.x)': FormatPeaHandler,

    # installer
    'inno setup module': FormatInnoSetupHandler,
    'nullsoft scriptable install system': Format7zHandler,
    'microsoft windows installer': FormatMsiHandler,

    # generic
    'gzip (.gz)': Format7zHandler,
    'gzipped data': Format7zHandler,

    # from binwalk
    '7zip': Format7zHandler,
    'xz': Format7zHandler,
    'bzip2': Format7zHandler,
    'compressd': Format7zHandler,
    'gzip': Format7zHandler,
    'tar': Format7zHandler,
    'apfs': Format7zHandler,
    'cab': Format7zHandler,
    'chm': Format7zHandler,
    'cpio': Format7zHandler,
    'cramfs': Format7zHandler,
    'dmg': Format7zHandler,
    'ext': Format7zHandler,
    'fat': Format7zHandler,
    'efigpt': Format7zHandler,
    'iso9660': Format7zHandler,
    'lzma': Format7zHandler,
    'mbr': Format7zHandler,
    'ntfs': Format7zHandler,
    'squashfs': Format7zHandler,
    'zip': Format7zHandler,
    'zlib': Format7zHandler,
    'zstd': Format7zHandler,
    'rar': FormatRarHandler,
}

def get_handler_from_mime(mime_type):
    """Returns the appropriate handler class for a given MIME type."""
    logging.debug(f"Looking for a handler for this mime type: '{mime_type}'")
    handler_class = MIME_HANDLERS.get(mime_type.lower())
    return handler_class if handler_class else None

def get_handler_from_detection(detection):
    """Returns the appropriate handler class based on a detection result."""
    logging.debug(f"Looking for a handler for this detection: '{detection}'")
    handler_class = DETECTION_HANDLERS.get(detection.lower())
    return handler_class if handler_class else None
