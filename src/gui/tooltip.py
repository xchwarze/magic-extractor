"""Hover and keyboard-focus tooltips (themed, wrapped, kept on screen)."""
import time
import tkinter as tk

from gui import theme
from gui.surfaces import surface
from gui.workarea import clamp_into, scaled, work_area

DEFAULT_DELAY_MS = 500      # a pointer merely crossing the window must not flash tips
WRAP_PX = 340               # wrap width at 96 DPI: long help never makes a screen-wide strip
POINTER_OFFSET = (12, 18)   # popup distance from the pointer, so it never sits under it (<Leave> flicker)
CLICK_FOCUS_WINDOW_S = 0.3  # a click focuses the widget right after ButtonPress: not keyboard navigation
KEY_FOCUS_WINDOW_S = 0.4    # focus counts as keyboard navigation only just after a key press: a
                            # dialog's initial (programmatic) focus must not open a tip nobody asked for
POPUP_SETTLE_S = 0.15       # an <Enter> on the popup this soon after it appeared is the popup appearing
WATCH_MS = 250              # a visible tip checks its widget is still on screen (a tab switch hides it silently)
PAD_X = 8
PAD_Y = 6


class Tooltip:
    """A help popup for one widget.

    It appears after ``delay`` ms of hovering, or when the widget takes keyboard focus (so the
    help is not hover-only), and goes away on leave, click, key press, focus loss, unmap or
    destroy. It is a plain override-redirect window: no grab, no focus, no taskbar entry.
    ``text`` may be changed at any time; an empty text shows nothing.
    """

    _active = None         # only one tooltip is ever on screen; a new one retires the previous
    _key_at = float("-inf")

    def __init__(self, widget, text, delay=DEFAULT_DELAY_MS):
        self.widget = widget
        self.text = text
        self.delay = delay
        self.popup = None
        self._job = None
        self._clicked_at = float("-inf")
        self._shown_at = float("-inf")
        self._watch_keys(widget.winfo_toplevel())
        for sequence, handler in (
            ("<Enter>", self._on_enter), ("<Motion>", self._on_motion), ("<FocusIn>", self._on_focus),
            ("<Leave>", self._hide_event), ("<FocusOut>", self._hide_event), ("<ButtonPress>", self._on_click),
            ("<KeyPress>", self._hide_event), ("<Unmap>", self._hide_event), ("<Destroy>", self._hide_event),
        ):
            widget.bind(sequence, handler, add="+")

    @property
    def visible(self):
        return self.popup is not None

    def _schedule(self, x, y, above):
        self._cancel()
        try:
            self._job = self.widget.after(self.delay, lambda: self.show(x, y, above))
        except tk.TclError:  # widget already destroyed
            self._job = None

    def _cancel(self):
        if self._job is not None:
            try:
                self.widget.after_cancel(self._job)
            except tk.TclError:  # destroyed with the job pending
                pass
            self._job = None

    def _on_enter(self, event):
        dx, dy = POINTER_OFFSET
        self._schedule(event.x_root + dx, event.y_root + dy, event.y_root - dx)

    def _on_motion(self, event):
        # restart the wait while the pointer is still travelling inside the widget
        if self.popup is None and self._job is not None:
            self._on_enter(event)

    def _on_click(self, event):
        self._clicked_at = time.monotonic()
        self._hide_event(event)

    @staticmethod
    def _watch_keys(window):
        """Remember when the last key was pressed in ``window`` (bound once per window)."""
        if getattr(window, "_tooltip_key_watch", False):
            return
        window._tooltip_key_watch = True
        window.bind("<KeyPress>", Tooltip._note_key, add="+")

    @staticmethod
    def _note_key(_event):
        Tooltip._key_at = time.monotonic()

    def _on_focus(self, _event):
        now = time.monotonic()
        if now - self._clicked_at < CLICK_FOCUS_WINDOW_S or now - Tooltip._key_at > KEY_FOCUS_WINDOW_S:
            return
        widget = self.widget
        x, y = widget.winfo_rootx(), widget.winfo_rooty()
        gap = scaled(widget, 4)
        self._schedule(x + POINTER_OFFSET[0], y + widget.winfo_height() + gap, y - gap)

    def _hide_event(self, _event):
        self.hide()

    def show(self, x, y, above=None):
        """Show the popup with its top-left at ``(x, y)``, pulled back into the work area of the
        widget's monitor; when it would overflow the bottom edge it goes above ``above``."""
        self._cancel()
        if Tooltip._active is not None and Tooltip._active is not self:
            Tooltip._active.hide()
        self.hide()
        if not self.text:
            return
        widget = self.widget
        try:
            if not widget.winfo_exists():
                return
            mode = theme.current(widget)
            colors = {**theme.palette(mode), **surface(mode)}
            popup = tk.Toplevel(widget)
            popup.withdraw()
            popup.overrideredirect(True)
            popup.attributes("-topmost", True)
            popup.configure(background=colors["border"], padx=1, pady=1)  # the hairline border
            tk.Label(popup, text=self.text, justify="left", wraplength=scaled(widget, WRAP_PX),
                     background=colors["bg"], foreground=colors["fg"], font=theme.body_font(widget),
                     padx=PAD_X, pady=PAD_Y).pack(fill="x")
            popup.update_idletasks()
            width, height = popup.winfo_reqwidth(), popup.winfo_reqheight()
            area = work_area(popup, widget)
            if y + height > area[3]:
                y = (above if above is not None else y) - height
            x, y = clamp_into(x, y, width, height, area)
            popup.geometry(f"+{x}+{y}")
            # a popup under the pointer would swallow the click meant for the widget below it
            popup.bind("<Enter>", self._on_popup_enter)
            popup.deiconify()
            popup.lift()
        except tk.TclError:  # widget torn down while the popup was being built
            return
        self.popup = popup
        self._shown_at = time.monotonic()
        Tooltip._active = self
        self._watch()

    def _on_popup_enter(self, _event):
        # Windows also reports <Enter> when the popup appears under a stationary pointer
        if time.monotonic() - self._shown_at > POPUP_SETTLE_S:
            self.hide()

    def _watch(self):
        """Retire the popup once its widget is no longer visible (tab switched, window hidden)."""
        if self.popup is None:
            return
        try:
            if self.widget.winfo_viewable():
                self.widget.after(WATCH_MS, self._watch)
                return
        except tk.TclError:  # widget destroyed
            pass
        self.hide()

    def hide(self):
        """Cancel a pending show and remove the popup."""
        self._cancel()
        popup, self.popup = self.popup, None
        if Tooltip._active is self:
            Tooltip._active = None
        if popup is not None:
            try:
                popup.destroy()
            except tk.TclError:  # already gone with its parent
                pass
