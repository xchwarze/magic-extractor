"""Entry point for the Magic Extractor GUI."""
import os
import sys

# Allow `python gui/main.py` (frozen or dev) to import the `gui` package.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
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


def main():
    root = _make_root()
    source, dest, mode = _parse_args(sys.argv[1:])
    ExtractorApp(root, initial_source=source, initial_dest=dest, initial_mode=mode)
    root.minsize(460, 360)
    root.mainloop()


if __name__ == "__main__":
    main()
