"""The app's own window and taskbar icon instead of Tk's default feather."""
import logging
import os
import sys
import tkinter as tk

ICON_NAME = "appicon.ico"
# Windows groups taskbar buttons by this id; without one, a run from source
# (python.exe gui/main.py) shows python.exe's icon in the taskbar.
APP_USER_MODEL_ID = "xchwarze.MagicExtractor.GUI"


def icon_path():
    """
    Path of appicon.ico, or None. Frozen: bundled into the exe (PyInstaller
    --add-data, unpacked under sys._MEIPASS/assets) or shipped beside it.
    Source: <repo>/assets/.
    """
    if getattr(sys, "frozen", False):
        candidates = [
            os.path.join(getattr(sys, "_MEIPASS", ""), "assets", ICON_NAME),
            os.path.join(os.path.dirname(sys.executable), ICON_NAME),
        ]
    else:
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        candidates = [os.path.join(repo_root, "assets", ICON_NAME)]
    return next((path for path in candidates if os.path.isfile(path)), None)


def set_app_user_model_id():
    """Give the process its own taskbar identity (Windows). Call before the first window."""
    if os.name != "nt":
        return
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except (AttributeError, OSError) as exc:
        logging.debug(f"Could not set the AppUserModelID: {exc}")


def apply(root):
    """Use appicon.ico for the main window and, via default=, every dialog."""
    path = icon_path()
    if path is None:
        logging.debug(f"{ICON_NAME} not found; keeping Tk's default icon")
        return
    try:
        root.iconbitmap(default=path)
    except tk.TclError as exc:  # e.g. a Tk build that cannot read .ico (non-Windows)
        logging.debug(f"Could not set the window icon from {path}: {exc}")
