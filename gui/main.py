"""Entry point for the Magic Extractor GUI."""
import os
import sys

# Allow `python gui/main.py` (frozen or dev) to import the `gui` package.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tkinter as tk
from gui.app import ExtractorApp


def main():
    root = tk.Tk()
    ExtractorApp(root)
    root.minsize(460, 360)
    root.mainloop()


if __name__ == "__main__":
    main()
