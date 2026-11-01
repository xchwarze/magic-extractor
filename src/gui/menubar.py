"""A fully self-drawn menu bar.

Native tk.Menu bars and dropdowns are rendered by the OS on Windows and ignore
bg/fg, so they never follow a dark theme. This bar and its dropdowns are drawn
from ordinary widgets we fully control, so dark mode is consistent everywhere.
"""
import tkinter as tk

from gui import theme


class MenuBar(tk.Frame):
    """A horizontal strip of menu labels; each opens a self-drawn dropdown."""

    def __init__(self, parent, mode, icon=None):
        """icon(semantic, mode) -> a 16 px tk image or None (no icon assets)."""
        super().__init__(parent)
        self.mode = mode
        self._icon = icon or (lambda _semantic, _mode: None)
        self._buttons = []          # (top-level label widget, icon semantic or None)
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

    @property
    def _hint(self):
        return theme.palette(self.mode)["hint"]

    def _image(self, semantic):
        return self._icon(semantic, self.mode) if semantic else None

    # ---- public API ------------------------------------------------------
    def add_menu(self, label, items, icon=None):
        """
        items: list of (text, command[, icon]); a None entry renders a separator.
        A text of "Label\tShortcut" shows the shortcut right-aligned and dimmed.
        icon: semantic name of the title's icon (gui/icons/catalog.py).
        """
        btn = tk.Label(self, text=label, padx=10, pady=4, bg=self._bg, fg=self._fg,
                       font=theme.body_font(self))
        self._set_image(btn, icon)
        btn.pack(side="left")
        btn.bind("<Button-1>", lambda e, b=btn, it=items: self._on_button(b, it))
        btn.bind("<Enter>", lambda e, b=btn: b.config(bg=self._hover))
        btn.bind("<Leave>", lambda e, b=btn: b.config(bg=self._bg))
        self._buttons.append((btn, icon))

    def _set_image(self, label, semantic):
        image = self._image(semantic)
        if image is not None:
            label.config(image=image, compound="left")
            label._icon_ref = image  # keep it alive

    def recolor(self, mode):
        """Re-apply colors (and icon tints) after a theme toggle."""
        self.mode = mode
        self.config(bg=self._bg)
        for btn, icon in self._buttons:
            btn.config(bg=self._bg, fg=self._fg)
            self._set_image(btn, icon)

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
        # Stay above the main window even when it is set always-on-top; an
        # overrideredirect popup is otherwise drawn behind a -topmost root.
        top.attributes("-topmost", True)
        top.config(bg=self._hover)  # 1px border color
        inner = tk.Frame(top, bg=self._bg)
        inner.pack(padx=1, pady=1)

        # the first item icon, if any: icon-less rows get a blank of the same size
        has_icons = next((self._image(item[2]) for item in items
                          if item and len(item) > 2 and self._image(item[2])), None)
        for item in items:
            if item is None:
                tk.Frame(inner, height=1, bg=self._hover).pack(fill="x", padx=4, pady=3)
                continue
            text, command = item[0], item[1]
            semantic = item[2] if len(item) > 2 else None
            label, _, shortcut = text.partition("\t")
            row = tk.Frame(inner, bg=self._bg)
            row.pack(fill="x")
            title = tk.Label(row, text=label, anchor="w", padx=12, pady=5, bg=self._bg, fg=self._fg,
                             font=theme.body_font(self))
            image = self._image(semantic)
            if image is None and has_icons:
                # keep the text of icon-less rows aligned with the others
                image = tk.PhotoImage(master=row, width=has_icons.width(), height=has_icons.height())
            if image is not None:
                title.config(image=image, compound="left")
                title._icon_ref = image
            title.pack(side="left", fill="x", expand=True)
            parts = [row, title]
            if shortcut:
                hint = tk.Label(row, text=shortcut, anchor="e", padx=12, pady=5, bg=self._bg, fg=self._hint,
                                font=theme.body_font(self))
                hint.pack(side="right")
                parts.append(hint)
            for widget in parts:
                widget.bind("<Enter>", lambda e, ws=parts: [w.config(bg=self._hover) for w in ws])
                widget.bind("<Leave>", lambda e, ws=parts: [w.config(bg=self._bg) for w in ws])
                widget.bind("<Button-1>", lambda e, c=command: self._invoke(c))

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
