"""The status line under the log and the wording of what a run is doing / did.

One muted line: a message that is too long ends in an ellipsis and its full text is a
tooltip. Colour is never the only signal: the words say "failed" too.
"""
import ntpath
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from gui import theme
from gui.surfaces import surface
from gui.tooltip import Tooltip

ELLIPSIS = "\u2026"

# mode -> (verb while running, what success is called, what failure is called, level of a failure)
_MODES = {
    "extract": ("Extracting", "extracted", "failed", "error"),
    "scan": ("Scanning", "identified", "not identified", "warning"),
    "carve": ("Carving", "carved", "failed", "error"),
}
_GENERIC = ("Running", "succeeded", "failed", "error")


def source_name(source):
    """The file name of a source path. ntpath, not os.path: the sources are Windows
    paths, and ntpath splits on both separators on any OS (posixpath, which os.path is
    on the Linux CI runner, ignores backslashes)."""
    return ntpath.basename(source.rstrip("\\/")) or source


def job_status(index, total, mode, source):
    """What is running: "Extracting foo.zip", or "Extracting 2 of 5: foo.zip" in a batch."""
    verb = _MODES.get(mode, _GENERIC)[0]
    if total > 1:
        return f"{verb} {index} of {total}: {source_name(source)}"
    return f"{verb} {source_name(source)}"


def run_summary(results, total, cancelled=False):
    """``(text, level)`` for a finished run.

    ``results`` is one ``(mode, source, exit_code)`` per job that ended, ``total`` how many were
    planned. Level is "info", "warning" (some failed) or "error" (all failed); the exit code 0 is
    success, and -1 on a cancelled run is the job that was interrupted, not a failure.
    """
    results = list(results)
    interrupted = 1 if cancelled and results and results[-1][2] == -1 else 0
    done = results[:len(results) - interrupted]
    good = sum(1 for _mode, _source, code in done if code == 0)
    bad = len(done) - good
    modes = {mode for mode, _source, _code in done}
    _verb, good_word, bad_word, bad_level = _MODES.get(next(iter(modes)), _GENERIC) if len(modes) == 1 else _GENERIC
    if cancelled:
        if total == 1:
            return "Cancelled", "info"
        parts = [f"{good} {good_word}"] if good else []
        if bad:
            parts.append(f"{bad} {bad_word}")
        if total - good - bad:
            parts.append(f"{total - good - bad} not run")
        return "Cancelled: " + ", ".join(parts), "info"
    if len(done) == 1 and total == 1:
        _mode, source, code = done[0]
        if code == 0:
            return f"{good_word.capitalize()}: {source_name(source)}", "info"
        detail = f" (exit code {code})" if code > 0 else ""
        return f"{bad_word.capitalize()}: {source_name(source)}{detail}", bad_level
    parts = [f"{good} {good_word}"] if good else []
    if bad:
        parts.append(f"{bad} {bad_word}")
    if not parts:
        return "Nothing to do", "info"
    return ", ".join(parts), ("info" if not bad else "warning" if good else bad_level)


def fit(text, width, measure):
    """``text`` cut with an ellipsis so that it measures at most ``width`` pixels."""
    if measure(text) <= width:
        return text
    low, high = 0, len(text)
    while low < high:  # longest prefix that still fits together with the ellipsis
        middle = (low + high + 1) // 2
        if measure(text[:middle].rstrip() + ELLIPSIS) <= width:
            low = middle
        else:
            high = middle - 1
    return text[:low].rstrip() + ELLIPSIS


class StatusLine:
    """A one-line, ellipsized status label coloured by level ("info", "warning", "error")."""

    def __init__(self, parent):
        # width=1: a label requests the width of its text, which would let a long message
        # widen the window; the packed/gridded fill gives the real width.
        self.label = ttk.Label(parent, text="", width=1, anchor="w")
        self.full = ""
        self.level = "info"
        self._tip = Tooltip(self.label, "")
        self.label.bind("<Configure>", lambda _event: self._render(), add="+")
        self.label.bind("<<ThemeChanged>>", lambda _event: self._colorize(), add="+")

    def set(self, text, level="info"):
        self.full = " ".join(str(text).split())  # one line: the row reserves exactly one
        self.level = level
        self._colorize()
        self._render()

    def _colorize(self):
        try:
            mode = theme.current(self.label)
            color = {"warning": theme.alert_colors(mode)["fg"], "error": surface(mode)["error"]}.get(self.level, "")
            self.label.configure(foreground=color)  # "" falls back to the style's colour
        except tk.TclError:  # destroyed during shutdown
            pass

    def _render(self):
        try:
            width = self.label.winfo_width()
            shown = self.full
            if width > 1:  # 1 px is the not-yet-mapped default
                font = tkfont.nametofont(theme.body_font(self.label), root=self.label)
                shown = fit(self.full, width, font.measure)
            self.label.configure(text=shown)
            self._tip.text = self.full if shown != self.full else ""
        except tk.TclError:  # destroyed during shutdown
            pass
