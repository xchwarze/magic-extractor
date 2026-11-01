"""Themed modal dialogs: creation, placement, Enter/Escape, grab and focus, confirm and message boxes.

The native ``messagebox`` boxes stay light in dark mode and cannot carry our icons, so the
GUI draws its own from ttk widgets. Everything here is a plain function over a parent window
and the current theme mode; the app wraps them (``ExtractorApp._confirm`` / ``_message``).
"""
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from gui import theme
from gui.geometry import clamp_into, fit_size, frame_extras, scaled, work_area

# The spacing scale (4 / 8 / 12 / 16); dialogs take every gap from here.
XS, SM, MD, LG = 4, 8, 12, 16


class DialogWindow(tk.Toplevel):
    """A Toplevel that remembers the grab and focus it interrupted."""

    # Widget paths that held the grab / focus before this dialog opened, so closing a
    # nested dialog hands modality and focus back to its parent.
    previous_grab = ""
    previous_focus = ""
    # The <Return> handler installed by bind_default (kept so a test can call it).
    return_handler = None


def accent_style():
    """The primary-button style; empty (plain button) when sv-ttk is not installed."""
    return "Accent.TButton" if theme.is_available() else ""


def _is_topmost(window):
    try:
        return bool(int(window.attributes("-topmost")))
    except (tk.TclError, ValueError):
        return False


def create_dialog(parent, title, mode, resizable=False):
    """A hidden, themed, parented dialog; reveal it with :func:`present`.

    Escape and the window's close button close it. It stays above an always-on-top
    parent (otherwise it would open behind it).
    """
    window = DialogWindow(parent)
    window.withdraw()  # hidden until present() has sized and placed it (no flicker)
    window.transient(parent)
    window.title(title)
    window.resizable(resizable, resizable)
    if _is_topmost(parent):
        window.attributes("-topmost", True)
    theme.restyle_toplevel(window, mode)
    window.protocol("WM_DELETE_WINDOW", lambda: close_dialog(window))
    window.bind("<Escape>", lambda _event: close_dialog(window))
    return window


def bind_default(window, action):
    """Enter presses the focused button; with focus elsewhere it runs ``action``.

    ``action`` is the dialog's default (primary) button. A focused button always wins:
    Enter on Cancel must cancel, not save. A multi-line Text keeps Enter for new lines.
    Returns the handler (also stored as ``window.return_handler``).
    """

    def on_return(event):
        widget = event.widget
        widget_class = widget.winfo_class() if hasattr(widget, "winfo_class") else ""
        if widget_class == "Text":
            return None
        if widget_class in ("TButton", "Button"):
            widget.invoke()
        else:
            action()
        return "break"

    window.bind("<Return>", on_return)
    window.return_handler = on_return
    return on_return


def button_row(parent, attach, primary, *secondary):
    """A right-aligned row: one accent primary button, then the secondary ones.

    Each spec is ``(label, semantic icon, command)``; ``attach(button, semantic)`` puts the
    icon on it. Returns ``(frame, primary_button, secondary_buttons)``; the caller places
    the frame. Windows order: primary first, then Cancel/Close.
    """
    frame = ttk.Frame(parent)
    label, semantic, command = primary
    primary_button = attach(ttk.Button(frame, text=label, command=command, style=accent_style()), semantic)
    primary_button.grid(row=0, column=0)
    others = []
    for column, (label, semantic, command) in enumerate(secondary, start=1):
        button = attach(ttk.Button(frame, text=label, command=command), semantic)
        button.grid(row=0, column=column, padx=(SM, 0))
        others.append(button)
    return frame, primary_button, others


# ---- placement ---------------------------------------------------------------
def center_window(window, parent):
    """Size the dialog to its content and center it over ``parent``, inside the work area."""
    parent.update_idletasks()
    window.update_idletasks()
    area = work_area(window, near=parent)
    extras = frame_extras(parent)
    width, height = fit_size(window.winfo_reqwidth(), window.winfo_reqheight(), area, extras)
    x = parent.winfo_rootx() + (max(parent.winfo_width(), parent.winfo_reqwidth()) - width) // 2
    y = parent.winfo_rooty() + (max(parent.winfo_height(), parent.winfo_reqheight()) - height) // 2
    x, y = clamp_into(x, y, width, height, area, extras)
    window.geometry(f"{width}x{height}+{x}+{y}")


def _reclamp(window, area):
    """Nudge a mapped dialog so its real frame is inside ``area``.

    The frame size is exact only once the window is mapped; this corrects the estimate
    :func:`center_window` made before.
    """
    window.update_idletasks()
    border, title = frame_extras(window)
    x, y = clamp_into(window.winfo_x(), window.winfo_y(), window.winfo_width(), window.winfo_height(),
                      area, (border, title))
    if (x, y) != (window.winfo_x(), window.winfo_y()):
        window.geometry(f"+{x}+{y}")


# ---- grab and focus -----------------------------------------------------------
def _current_grab_and_focus(window):
    """Widget paths of the current grab and focus ("" when none)."""
    return str(window.tk.eval("grab current")), str(window.tk.eval("focus"))


def _restore(window, path):
    """The live widget at ``path``, or None when it is gone."""
    if not path:
        return None
    try:
        widget = window.nametowidget(path)
        return widget if widget.winfo_exists() else None
    except (KeyError, tk.TclError):
        return None


def present(window, parent, mode, initial_focus=None, modal=True):
    """Center and reveal a dialog, theme its title bar, focus it and make it modal.

    A modal dialog remembers the grab and focus it interrupts so :func:`close_dialog`
    can restore them when dialogs are nested.
    """
    window.previous_grab, window.previous_focus = _current_grab_and_focus(window)
    theme.apply_widget_tree(window, mode)  # entry fonts etc., before the size is measured
    center_window(window, parent)  # placed while still withdrawn: never flashes at a default spot
    window.deiconify()
    _reclamp(window, work_area(window, near=parent))
    theme.titlebar(window, mode)  # the title bar can only be themed once the window is mapped
    # focus_force: Windows may refuse foreground focus to a fresh window, leaving the keys
    # with the parent.
    window.lift()
    window.focus_force()
    if initial_focus is not None:
        initial_focus.focus_set()
    if modal:
        try:
            window.grab_set()  # only valid once viewable
        except tk.TclError:
            pass  # not viewable (e.g. a hidden parent): the dialog stays non-modal


def close_dialog(window):
    """Release the grab, destroy the dialog, and hand grab and focus back to what it interrupted."""
    previous_grab = getattr(window, "previous_grab", "")
    previous_focus = getattr(window, "previous_focus", "")
    anchor = window.master
    try:
        window.grab_release()
    except tk.TclError:  # the grab was never taken
        pass
    window.destroy()
    grab_owner = _restore(anchor, previous_grab)
    if grab_owner is not None:
        try:
            grab_owner.grab_set()
        except tk.TclError:  # no longer viewable (e.g. it is being closed too)
            pass
    focus_target = _restore(anchor, previous_focus)
    if focus_target is not None:
        focus_target.focus_force()


# ---- confirm and message boxes ------------------------------------------------
def _wrap_length(window):
    """Wrap width for dialog text: about 48 characters, so it follows font and DPI scaling."""
    return tkfont.nametofont(theme.body_font(window)).measure("0") * 48


class ConfirmDialog:
    """A confirmation whose safe answer is the default for Enter and Escape."""

    def __init__(self, parent, mode, attach, title, message, detail, confirm_label, confirm_icon, cancel_label):
        self.confirmed = False
        self.window = window = create_dialog(parent, title, mode)
        body = ttk.Frame(window, padding=LG)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=1, minsize=scaled(window, 320))
        wrap = _wrap_length(window)
        ttk.Label(body, text=message, font=theme.heading_font(window), wraplength=wrap,
                  justify="left").grid(row=0, column=0, sticky="ew")
        if detail:
            ttk.Label(body, text=detail, wraplength=wrap, justify="left").grid(
                row=1, column=0, sticky="ew", pady=(SM, 0))
        buttons = ttk.Frame(body)
        buttons.grid(row=2, column=0, sticky="e", pady=(LG, 0))
        self.confirm_button = attach(ttk.Button(buttons, text=confirm_label, command=self._confirm), confirm_icon)
        self.confirm_button.grid(row=0, column=0)
        # The safe answer is the accent button: a stray Enter or Escape must never destroy files.
        self.cancel_button = attach(
            ttk.Button(buttons, text=cancel_label, command=lambda: close_dialog(window), style=accent_style()),
            "dismiss")
        self.cancel_button.grid(row=0, column=1, padx=(MD, 0))
        bind_default(window, self.cancel_button.invoke)

    def _confirm(self):
        self.confirmed = True
        close_dialog(self.window)


def confirm(parent, mode, attach, title, message, detail="", confirm_label="OK", confirm_icon="dismiss",
            cancel_label="Cancel"):
    """Ask the user to confirm an action; True only when they press the confirm button.

    Cancel is the focused, accent, Enter and Escape button (and what the window's close
    button means). Blocks until the dialog closes.
    """
    dialog = ConfirmDialog(parent, mode, attach, title, message, detail, confirm_label, confirm_icon, cancel_label)
    present(dialog.window, parent, mode, initial_focus=dialog.cancel_button)
    dialog.window.wait_window()
    return dialog.confirmed


class MessageDialog:
    """A one-button notice (the themed showinfo/showwarning/showerror)."""

    def __init__(self, parent, mode, attach, title, message):
        self.window = window = create_dialog(parent, title, mode)
        body = ttk.Frame(window, padding=LG)
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure(0, weight=1, minsize=scaled(window, 320))
        ttk.Label(body, text=message, wraplength=_wrap_length(window), justify="left").grid(
            row=0, column=0, sticky="ew")
        row, self.close_button, _others = button_row(body, attach, ("Close", "dismiss", lambda: close_dialog(window)))
        row.grid(row=1, column=0, sticky="e", pady=(LG, 0))
        bind_default(window, self.close_button.invoke)


def show_message(parent, mode, attach, title, message):
    """Show a themed notice and wait until it is closed."""
    dialog = MessageDialog(parent, mode, attach, title, message)
    present(dialog.window, parent, mode, initial_focus=dialog.close_button)
    dialog.window.wait_window()
