"""Entry point for the Magic Extractor GUI."""
import logging
import os
import sys

# Allow `python gui/main.py` (frozen or dev) to import the `gui` package.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from gui import app_icon, logging_setup, runner
from gui.app import ExtractorApp


def _make_root():
    """A DnD-capable root when tkinterdnd2 is installed; a plain Tk otherwise."""
    try:
        from tkinterdnd2 import TkinterDnD
        return TkinterDnD.Tk()
    except Exception:
        return tk.Tk()


def _parse_args(argv):
    """Parse `magic-extractor-gui.exe <file> [<outdir>|/scan]` → prefill values."""
    mode = "scan" if "/scan" in argv else None
    positionals = [a for a in argv if not a.startswith(("/", "-"))]
    source = positionals[0] if positionals else None
    dest = positionals[1] if len(positionals) > 1 else None
    return source, dest, mode


def _enable_dpi_awareness():
    """Per-monitor DPI awareness (Windows) before Tk starts, so text is crisp at
    125-200% scaling instead of bitmap-stretched."""
    if os.name != "nt":
        return
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # per-monitor
    except (AttributeError, OSError):
        try:
            ctypes.windll.user32.SetProcessDPIAware()  # system-aware fallback
        except (AttributeError, OSError):
            pass


def main():
    # First thing, so a failure below is recorded even in the windowed exe (no console).
    logging_setup.configure(os.path.dirname(runner.resolve_gui_config_path()))
    try:
        _enable_dpi_awareness()
        app_icon.set_app_user_model_id()  # before the first window, so the taskbar uses our icon
        root = _make_root()
        app_icon.apply(root)
        source, dest, mode = _parse_args(sys.argv[1:])
        ExtractorApp(root, initial_source=source, initial_dest=dest, initial_mode=mode)
        scale = root.winfo_fpixels("1i") / 96.0  # 1.0 at 100%, 2.0 at 200%
        root.minsize(int(460 * scale), int(360 * scale))
    except Exception as exc:
        logging_setup.report_fatal("Magic Extractor", f"The window could not start: {exc}")
        return 1
    logging.info("Magic Extractor GUI %s started", runner.read_version())
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
