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
