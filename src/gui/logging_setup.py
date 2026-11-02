"""Make GUI errors visible in the windowed (--noconsole) exe.

A frozen windowed build has no stderr, so without a file handler every ``logging.error``
call and every traceback Tk or a thread prints would vanish. In the frozen exe the root
logger gets a rotating ``gui.log`` (beside the exe, like gui.ini, or under %LOCALAPPDATA%
when that folder is read-only) and uncaught exceptions are logged to it. A source run keeps
logging to the console, where the developer already sees it.
"""
import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler

LOG_NAME = "gui.log"
_MAX_BYTES = 512_000
_BACKUPS = 2
_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"

_path = None  # the log file in use, or None


def log_path():
    """The log file in use (frozen exe), or None when logging goes to the console."""
    return _path


def _candidate_dirs(primary):
    yield primary
    local = os.environ.get("LOCALAPPDATA")
    if local:
        yield os.path.join(local, "magic-extractor")


def configure(log_dir, frozen=None):
    """Log to ``gui.log`` in ``log_dir`` when frozen; returns the file path or None.

    Safe to call twice (one handler only), and a folder that cannot be written is not fatal:
    the next candidate is tried and, failing all, the GUI just starts without a log file.
    """
    global _path
    if frozen is None:
        frozen = getattr(sys, "frozen", False)
    if not frozen:
        return None
    root = logging.getLogger()
    for handler in root.handlers:
        if isinstance(handler, RotatingFileHandler) and handler.baseFilename.endswith(LOG_NAME):
            return _path
    for folder in _candidate_dirs(log_dir):
        target = os.path.join(folder, LOG_NAME)
        try:
            os.makedirs(folder, exist_ok=True)
            handler = RotatingFileHandler(target, maxBytes=_MAX_BYTES, backupCount=_BACKUPS, encoding="utf-8")
        except OSError:
            continue
        handler.setFormatter(logging.Formatter(_FORMAT))
        handler.setLevel(logging.INFO)
        root.addHandler(handler)
        if root.level == logging.NOTSET or root.level > logging.INFO:
            root.setLevel(logging.INFO)
        _path = target
        install_hooks()
        return target
    return None


def _log_uncaught(exc_type, exc, tb):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc, tb)
        return
    logging.critical("Uncaught exception", exc_info=(exc_type, exc, tb))


def _log_thread_exception(args):
    if args.exc_type is SystemExit:
        return
    name = args.thread.name if args.thread else "?"
    logging.error("Uncaught exception in thread %s", name,
                  exc_info=(args.exc_type, args.exc_value, args.exc_traceback))


def install_hooks():
    """Route uncaught exceptions (main thread and worker threads) to the log."""
    sys.excepthook = _log_uncaught
    threading.excepthook = _log_thread_exception


def report_fatal(title, message):
    """Tell the user the GUI cannot go on: logged, and a native message box in the frozen exe
    (the window may not exist, and there is no console to read it from)."""
    logging.critical("%s: %s", title, message, exc_info=True)
    if getattr(sys, "frozen", False):
        _message_box(title, message + (f"\n\nDetails: {_path}" if _path else ""))


def _message_box(title, message):
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, message, title, 0x10)  # MB_ICONERROR
    except (OSError, AttributeError):
        pass
