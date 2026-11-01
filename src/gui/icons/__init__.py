"""Fluent System Icons on the GUI's buttons, from pre-baked PNGs.

tools/generate_icons.py bakes every icon, per theme and state, into
``assets/<light|dark>/<name>-<size>[-disabled].png``. At runtime this module only
loads those files with tk.PhotoImage: no icon library, font or Pillow. Without the
assets every helper leaves the button text-only, so the GUI still works.
"""
import logging
import os
import sys
import tkinter as tk

from gui.geometry import dpi_scale
from gui.icons.catalog import (
    ACCENT, ACCENT_DISABLED, ACCENT_ICONS, COMPACT, DISABLED, NORMAL, REGULAR, THEMES, asset_name, nearest_size,
)

_FROZEN_SUBPATH = ("gui", "icons", "assets")
GAP = 6  # transparent pixels between the icon and the button text


def assets_dir():
    """The folder with the light/dark icon folders, or None when it is absent."""
    candidates = []
    if getattr(sys, "frozen", False) and getattr(sys, "_MEIPASS", None):
        candidates.append(os.path.join(sys._MEIPASS, *_FROZEN_SUBPATH))
    candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets"))
    return next((path for path in candidates if os.path.isdir(path)), None)


def icon_size(widget, base_size):
    """``base_size`` moved to the nearest baked size for this display's scaling."""
    return nearest_size(base_size * dpi_scale(widget))


def available():
    folder = assets_dir()
    return folder is not None and any(os.path.isdir(os.path.join(folder, mode)) for mode in THEMES)


class ButtonIcons:
    """Puts icons on ttk buttons and re-tints them when the theme changes."""

    def __init__(self, root):
        self.root = root
        self._cache = {}
        self._buttons = []  # (button, semantic, size, with_text)

    def photo(self, mode, semantic, size, variant=NORMAL, gap=0):
        """The baked icon as a Tk image (with ``gap`` transparent pixels on its right), or None."""
        key = (mode, semantic, size, variant, gap)
        if key in self._cache:
            return self._cache[key]
        folder = assets_dir()
        image = None
        if folder is not None:
            path = os.path.join(folder, mode if mode in THEMES else "light", asset_name(semantic, size, variant))
            try:
                icon = tk.PhotoImage(master=self.root, file=path)
                if gap:
                    padded = tk.PhotoImage(master=self.root, width=icon.width() + gap, height=icon.height())
                    padded.tk.call(padded, "copy", icon, "-to", 0, 0)
                    icon = padded
                image = icon
            except tk.TclError as exc:
                logging.debug(f"No icon {path}: {exc}")
        self._cache[key] = image
        return image

    def attach(self, button, semantic, mode, with_text=True):
        """Show ``semantic`` on ``button`` (left of its text, or alone) in theme
        ``mode``, at the size for the display scaling; returns the button."""
        size = icon_size(self.root, REGULAR if with_text else COMPACT)
        self._buttons.append((button, semantic, size, with_text))
        self._apply(button, semantic, mode, size, with_text)
        return button

    def _apply(self, button, semantic, mode, size, with_text):
        gap = round(GAP * dpi_scale(self.root)) if with_text else 0
        # An Accent.TButton draws its text in another colour than a plain one, so its
        # icon has its own tints (only the icons in ACCENT_ICONS are baked that way).
        accent = semantic in ACCENT_ICONS and str(button.cget("style")).startswith("Accent.")
        normal = self.photo(mode, semantic, size, ACCENT if accent else NORMAL, gap)
        if normal is None:
            return  # no assets: keep the text-only button
        disabled = self.photo(mode, semantic, size, ACCENT_DISABLED if accent else DISABLED, gap) or normal
        button.configure(image=(normal, "disabled", disabled),
                         compound="left" if with_text else "image")
        button._icon_refs = (normal, disabled)  # keep the images alive
        return button

    def retheme(self, mode):
        """Re-tint every attached button for a new theme."""
        alive = []
        for button, semantic, size, with_text in self._buttons:
            try:
                if button.winfo_exists():
                    self._apply(button, semantic, mode, size, with_text)
                    alive.append((button, semantic, size, with_text))
            except tk.TclError:
                pass
        self._buttons = alive
