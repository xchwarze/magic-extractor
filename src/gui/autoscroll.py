"""A vertical scrollbar that is only there while the content needs it."""
from tkinter import ttk


class AutoScrollbar(ttk.Scrollbar):
    """Hidden while the whole content is visible (no dead scrollbar, no horizontal one).

    Grid it in its own column first: hiding uses ``grid_remove``, which keeps the
    grid position and options, so the widget beside it (column weight 1) simply
    takes the room back.
    """

    def set(self, first, last):
        """``yscrollcommand`` target: show or hide the bar, then forward the fractions."""
        if float(first) <= 0.0 and float(last) >= 1.0:
            self.grid_remove()
        else:
            self.grid()
        super().set(first, last)
