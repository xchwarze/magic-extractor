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


def main():
    root = _make_root()
    ExtractorApp(root)
    root.minsize(460, 360)
    root.mainloop()


if __name__ == "__main__":
    main()
