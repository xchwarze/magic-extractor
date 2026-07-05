import os
import logging

def has_free_space(path, minimum_free_bytes):
    """
    Check if there is enough disk space in the path.
    """
    statvfs = os.statvfs(path)
    free_space = statvfs.f_frsize * statvfs.f_bavail
    return free_space > minimum_free_bytes

def log_setup(debug_level):
    """
    Setup logging configuration based on the debug level.
    """
    level = logging.DEBUG if debug_level else logging.INFO
    logging.basicConfig(level=level, format='%(asctime)s - %(levelname)s - %(message)s')

def open_url(url):
    """
    Open a URL in the default web browser.
    """
    import webbrowser
    webbrowser.open(url)

def delete_source(path, use_recycle_bin=True):
    """
    Delete a source file after a successful extraction.

    Recycle Bin by default (recoverable). If the Recycle Bin is requested but
    send2trash is unavailable, the file is KEPT (never silently permanently
    deleted). Returns True if the file was removed, False if kept/failed.
    """
    path = str(path)
    if use_recycle_bin:
        try:
            from send2trash import send2trash
        except ImportError:
            logging.warning(f"send2trash unavailable; keeping source (not permanently deleting): {path}")
            return False
        try:
            send2trash(path)
            logging.info(f"Source moved to Recycle Bin: {path}")
            return True
        except OSError as exc:
            logging.error(f"Could not recycle source {path}: {exc}")
            return False

    try:
        os.remove(path)
        logging.info(f"Source permanently deleted: {path}")
        return True
    except OSError as exc:
        logging.error(f"Could not delete source {path}: {exc}")
        return False
