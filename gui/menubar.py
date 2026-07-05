"""A fully self-drawn menu bar.

Native tk.Menu bars and dropdowns are rendered by the OS on Windows and ignore
bg/fg, so they never follow a dark theme. This bar and its dropdowns are drawn
from ordinary widgets we fully control, so dark mode is consistent everywhere.
"""
import tkinter as tk

from gui import theme


class MenuBar(tk.Frame):
    """A horizontal strip of menu labels; each opens a self-drawn dropdown."""

    def __init__(self, parent, mode):
        super().__init__(parent)
        self.mode = mode
        self._buttons = []          # top-level label widgets
        self._popup = None          # open dropdown Toplevel (or None)
        self._popup_owner = None    # the button that opened it
        self._suppress = None       # button whose reopen to swallow (one click)
        self.config(bg=self._bg)

    # ---- colors ----------------------------------------------------------
    @property
    def _bg(self):
        return theme.palette(self.mode)["bg"]

    @property
    def _fg(self):
        return theme.palette(self.mode)["fg"]

    @property
    def _hover(self):
        return "#2d2d2d" if self.mode == "dark" else "#e5e5e5"

    # ---- public API ------------------------------------------------------
    def add_menu(self, label, items):
        """items: list of (text, command); a None entry renders a separator."""
        btn = tk.Label(self, text=label, padx=10, pady=4, bg=self._bg, fg=self._fg)
        btn.pack(side="left")
        btn.bind("<Button-1>", lambda e, b=btn, it=items: self._on_button(b, it))
        btn.bind("<Enter>", lambda e, b=btn: b.config(bg=self._hover))
        btn.bind("<Leave>", lambda e, b=btn: b.config(bg=self._bg))
        self._buttons.append(btn)

    def recolor(self, mode):
        """Re-apply colors after a theme toggle."""
        self.mode = mode
        self.config(bg=self._bg)
        for btn in self._buttons:
            btn.config(bg=self._bg, fg=self._fg)

    # ---- dropdown handling ----------------------------------------------
    def _on_button(self, btn, items):
        # A click that just closed this menu (via FocusOut) must not reopen it.
        if self._suppress is btn:
            return
        if self._popup is not None and self._popup_owner is btn:
            self._close()
            return
        self._close()
        self._open(btn, items)

    def _open(self, btn, items):
        top = tk.Toplevel(self)
        top.wm_overrideredirect(True)
        top.config(bg=self._hover)  # 1px border color
        inner = tk.Frame(top, bg=self._bg)
        inner.pack(padx=1, pady=1)

        for item in items:
            if item is None:
                tk.Frame(inner, height=1, bg=self._hover).pack(fill="x", padx=4, pady=3)
                continue
            text, command = item
            row = tk.Label(inner, text=text, anchor="w", padx=18, pady=5,
                           bg=self._bg, fg=self._fg)
            row.pack(fill="x")
            row.bind("<Enter>", lambda e, r=row: r.config(bg=self._hover))
            row.bind("<Leave>", lambda e, r=row: r.config(bg=self._bg))
            row.bind("<Button-1>", lambda e, c=command: self._invoke(c))

        top.update_idletasks()
        x = btn.winfo_rootx()
        y = btn.winfo_rooty() + btn.winfo_height()
        top.wm_geometry(f"+{x}+{y}")
        top.bind("<FocusOut>", lambda e: self._close())
        top.bind("<Escape>", lambda e: self._close())
        self._popup = top
        self._popup_owner = btn
        top.focus_force()

    def _invoke(self, command):
        self._close()
        command()

    def _close(self):
        if self._popup is None:
            return
        owner = self._popup_owner
        self._popup.destroy()
        self._popup = None
        self._popup_owner = None
        # Swallow the same click's reopen when it lands on the owning button.
        self._suppress = owner
        self.after(1, self._clear_suppress)

    def _clear_suppress(self):
        self._suppress = None
