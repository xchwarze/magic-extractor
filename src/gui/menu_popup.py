"""Self-drawn popup menus: the pieces shared by the menu bar dropdowns and context menus.

Native tk.Menu popups are rendered by the OS on Windows and ignore the theme colours, so
these are plain Tk widgets. A popup is an ``overrideredirect`` + ``-topmost`` Toplevel that
closes on ``<FocusOut>`` and ``<Escape>``. It deliberately uses neither ``transient()`` nor
``grab_set()``: on Windows an overrideredirect *transient* window is stacked behind its owner,
and a grab held by that invisible window redirects every click in the application to it,
which freezes the whole GUI.

Keyboard: Up/Down, Home/End move over the enabled rows (wrapping), Enter or Space runs the
highlighted one, Escape closes; the menu bar adds Left/Right to step to the neighbouring menu.
"""
import tkinter as tk
from typing import Callable, NamedTuple

from gui import theme
from gui.surfaces import surface
from gui.workarea import clamp_into, scaled, work_area

ROW_PAD_X = 12
ROW_PAD_Y = 4
ICON_GAP = 8  # pixels between a row's icon and its text (padded into the image)


class Item(NamedTuple):
    """One popup row. ``text`` may carry a shortcut after a tab ("Copy\tCtrl+C", shown dimmed
    on the right); ``icon`` is a semantic icon name (gui/icons/catalog.py) or ""."""

    text: str
    command: Callable[[], object]
    icon: str = ""
    enabled: bool = True


def icon_image(provider, semantic, mode, disabled):
    """The row's image from ``provider(semantic, mode, disabled)``, or None (no icon / no assets)."""
    if not semantic or provider is None:
        return None
    try:
        return provider(semantic, mode, disabled)
    except tk.TclError:
        return None


class _Row:
    def __init__(self, widgets, command, enabled):
        self.widgets = widgets
        self.command = command
        self.enabled = enabled


class RowList:
    """The rows of one popup plus the hover / keyboard highlight."""

    def __init__(self, inner, mode, icon=None, invoke=None):
        """``icon(semantic, mode, disabled)`` -> a Tk image or None. ``invoke(command)`` runs a
        row's command (a popup closes itself first); the default calls it directly."""
        self.inner = inner
        self.mode = "dark" if mode == "dark" else "light"
        self.colors = {**theme.palette(self.mode), **surface(self.mode)}
        self._icon = icon
        self._invoke = invoke or (lambda command: command())
        self.rows = []
        self.index = None

    def populate(self, items):
        """Add every ``Item`` (``None`` makes a separator). Rows without an icon in a menu that
        has some get a blank of the same size, so all the text lines up."""
        blank = None
        for item in items:
            image = icon_image(self._icon, item.icon, self.mode, False) if item is not None else None
            if image is not None:
                blank = (image.width(), image.height())
                break
        for item in items:
            if item is None:
                self.separator()
            else:
                self.add(item, blank)

    def add(self, item, blank=None):
        """Append a row; ``blank`` is the (width, height) of an empty icon slot, if rows need one."""
        colors = self.colors
        label, _, shortcut = item.text.partition("\t")
        fg = colors["fg"] if item.enabled else colors["disabled"]
        row = tk.Frame(self.inner, bg=colors["bg"])
        row.pack(fill="x")
        title = tk.Label(row, text=label, anchor="w", padx=ROW_PAD_X, pady=ROW_PAD_Y,
                         bg=colors["bg"], fg=fg, font=theme.body_font(self.inner))
        image = icon_image(self._icon, item.icon, self.mode, not item.enabled)
        if image is None and blank is not None:
            image = tk.PhotoImage(master=row, width=blank[0], height=blank[1])
        if image is not None:
            title.config(image=image, compound="left")
            title._icon_ref = image  # keep it alive
        title.pack(side="left", fill="x", expand=True)
        widgets = [row, title]
        if shortcut:
            hint = tk.Label(row, text=shortcut, anchor="e", padx=ROW_PAD_X, pady=ROW_PAD_Y,
                            bg=colors["bg"], fg=colors["muted"] if item.enabled else colors["disabled"],
                            font=theme.body_font(self.inner))
            hint.pack(side="right")
            widgets.append(hint)
        position = len(self.rows)
        self.rows.append(_Row(widgets, item.command, item.enabled))
        for widget in widgets:
            widget.bind("<Enter>", lambda _e, i=position: self._hover(i))
            widget.bind("<Leave>", lambda _e, i=position: self._leave(i))
            widget.bind("<Button-1>", lambda _e, i=position: self.activate(i))
        return row

    def separator(self):
        """A 1 px divider (skipped by keyboard navigation)."""
        tk.Frame(self.inner, height=1, bg=self.colors["border"]).pack(fill="x", padx=4, pady=4)

    def highlight(self, index):
        """Mark row ``index`` (or none) as the hover / keyboard target."""
        self.index = index
        for position, row in enumerate(self.rows):
            colour = self.colors["hover"] if position == index else self.colors["bg"]
            for widget in row.widgets:
                widget.config(bg=colour)

    def _hover(self, index):
        if self.rows[index].enabled:
            self.highlight(index)

    def _leave(self, index):
        if self.index == index:  # only if this row still owns the highlight
            self.highlight(None)

    def move(self, delta, start=None):
        """Move the highlight by ``delta`` over the enabled rows, wrapping. ``start`` >= 0 jumps
        to the first enabled row, < 0 to the last."""
        enabled = [i for i, row in enumerate(self.rows) if row.enabled]
        if not enabled:
            return
        if start is not None:
            self.highlight(enabled[0] if start >= 0 else enabled[-1])
        elif self.index not in enabled:
            self.highlight(enabled[0] if delta > 0 else enabled[-1])
        else:
            self.highlight(enabled[(enabled.index(self.index) + delta) % len(enabled)])

    def activate(self, index=None):
        """Run the command of row ``index`` (default: the highlighted row); disabled rows do nothing."""
        target = self.index if index is None else index
        if target is None:
            return
        row = self.rows[target]
        if row.enabled and row.command is not None:
            self._invoke(row.command)


def make_popup(parent, mode):
    """A hidden, borderless, topmost popup and the inner frame that holds its rows."""
    colors = surface(mode)
    popup = tk.Toplevel(parent)
    popup.withdraw()  # hidden until placed, so it never flashes at the default position
    popup.wm_overrideredirect(True)
    # Stay above the main window even when it is always-on-top; an overrideredirect popup is
    # otherwise drawn behind a -topmost root.
    popup.attributes("-topmost", True)
    popup.config(bg=colors["border"])  # the 1 px border
    inner = tk.Frame(popup, bg=theme.palette(mode)["bg"])
    inner.pack(padx=1, pady=1)
    return popup, inner


def place(popup, x, y, near):
    """Put the popup at screen ``x``/``y`` clamped into the work area of ``near``'s monitor, then show it."""
    popup.update_idletasks()  # measure after the rows were packed
    x, y = clamp_into(x, y, popup.winfo_reqwidth(), popup.winfo_reqheight(), work_area(popup, near))
    popup.wm_geometry(f"+{x}+{y}")
    popup.deiconify()
    popup.lift()


def bind_navigation(popup, rows, close, side=None):
    """Arrows, Home/End, Enter, Space and Escape on a popup; Left/Right only when ``side`` is given."""
    popup.bind("<Down>", lambda _e: rows.move(1))
    popup.bind("<Up>", lambda _e: rows.move(-1))
    popup.bind("<Home>", lambda _e: rows.move(1, start=0))
    popup.bind("<End>", lambda _e: rows.move(-1, start=-1))
    for key in ("<Return>", "<KP_Enter>", "<space>"):
        popup.bind(key, lambda _e: rows.activate())
    popup.bind("<Escape>", lambda _e: close())
    if side is not None:
        popup.bind("<Left>", lambda _e: side(-1))
        popup.bind("<Right>", lambda _e: side(1))


def keyboard_anchor(widget):
    """Screen position for a menu opened from the keyboard: under the caret, else near the top-left."""
    try:
        box = widget.bbox("insert")
    except (tk.TclError, TypeError):
        box = None
    if not box:
        return widget.winfo_rootx() + scaled(widget, 8), widget.winfo_rooty() + scaled(widget, 8)
    return widget.winfo_rootx() + box[0], widget.winfo_rooty() + box[1] + box[3]


def show_context_menu(parent, mode, x, y, items, icon=None):
    """Show a themed popup of ``Item`` rows at screen ``x``/``y`` and return it.

    It closes when a row runs, on Escape, and when it loses focus (a click elsewhere).
    Without a grab, focus is what makes the key bindings and that last rule work.
    """
    popup, inner = make_popup(parent, mode)

    def close(_event=None):
        try:
            if popup.winfo_exists():
                popup.destroy()
        except tk.TclError:  # already destroyed by a concurrent FocusOut
            pass

    def run(command):
        close()
        command()

    rows = RowList(inner, mode, icon=icon, invoke=run)
    rows.populate(items)
    popup.rows = rows  # reachable for keyboard tests and the caller
    place(popup, x, y, parent)
    popup.bind("<FocusOut>", close)
    bind_navigation(popup, rows, close)
    popup.update_idletasks()
    popup.focus_force()
    return popup

