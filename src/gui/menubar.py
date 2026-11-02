"""A fully self-drawn menu bar (its dropdown rows are gui/menu_popup.py).

Native tk.Menu bars and dropdowns are rendered by the OS on Windows and ignore bg/fg, so
they never follow a dark theme. This bar and its dropdowns are drawn from ordinary widgets
we fully control, so dark mode is consistent everywhere.

Keyboard: ``F10`` focuses the bar (Escape gives the focus back), Left/Right move between the
labels, Enter / Space / Down open a menu. Inside a dropdown Up/Down/Home/End move over the
enabled rows, Enter or Space runs one, Left/Right step to the neighbouring menu and Escape
closes it. Entries can be disabled (``set_entry_state``): they are dimmed and cannot be run
from the mouse or the keyboard.
"""
import tkinter as tk

from gui import theme
from gui.menu_popup import Item, RowList, bind_navigation, make_popup, place
from gui.surfaces import surface


class MenuBar(tk.Frame):
    """A horizontal strip of menu labels; each opens a self-drawn dropdown."""

    def __init__(self, parent, mode, icon=None):
        """icon(semantic, mode) -> a 16 px tk image or None (no icon assets)."""
        super().__init__(parent, borderwidth=0, highlightthickness=0)
        self.mode = mode
        self._icon = icon or (lambda _semantic, _mode: None)
        self._buttons = []          # (top-level label widget, icon semantic or None)
        self._titles = []           # label texts, parallel to _buttons
        self._groups = {}           # title -> [Item or None]
        self._disabled = set()      # entry names (the text before any tab) that cannot run
        self._popup = None          # open dropdown Toplevel (or None)
        self._popup_owner = None    # the label that opened it
        self._suppress = None       # label whose reopen to swallow (one click)
        self._suppress_job = None   # the pending after() that ends the suppression
        self._return_focus = None   # widget to refocus after F10 navigation
        self.config(bg=self._bg)
        self.bind("<Escape>", lambda _event: self.close())
        # F10 must work wherever focus is, so it lives on the window, not on the bar.
        toplevel = self.winfo_toplevel()
        self._f10 = (toplevel, toplevel.bind("<F10>", self._on_f10, add="+"))
        self.bind("<Destroy>", self._on_destroy)

    # ---- colors ----------------------------------------------------------
    @property
    def _bg(self):
        return theme.palette(self.mode)["bg"]

    @property
    def _fg(self):
        return theme.palette(self.mode)["fg"]

    @property
    def _hover(self):
        return surface(self.mode)["hover"]

    def _image(self, semantic):
        return self._icon(semantic, self.mode) if semantic else None

    # ---- public API ------------------------------------------------------
    def add_menu(self, label, items, icon=None):
        """items: list of ``(text, command)``; a None entry renders a separator.
        A text of "Label\tShortcut" shows the shortcut right-aligned and dimmed.
        icon: semantic name of the title's icon (gui/icons/catalog.py)."""
        self._groups[label] = [None if item is None else Item(item[0], item[1]) for item in items]
        btn = tk.Label(self, text=label, padx=10, pady=4, bg=self._bg, fg=self._fg,
                       font=theme.body_font(self), takefocus=False,
                       # the accent ring keeps keyboard focus visible while the label is not in Tab order
                       highlightthickness=1, highlightbackground=self._bg,
                       highlightcolor=surface(self.mode)["accent"])
        self._set_image(btn, icon)
        btn.pack(side="left")
        btn.bind("<Button-1>", lambda _e, b=btn, name=label: self._on_button(b, name))
        btn.bind("<Enter>", lambda _e, b=btn: b.config(bg=self._hover))
        btn.bind("<Leave>", lambda _e, b=btn: b.config(bg=self._bg))
        btn.bind("<FocusIn>", lambda _e, b=btn: b.config(bg=self._hover))
        btn.bind("<FocusOut>", lambda _e, b=btn: b.config(bg=self._bg))
        for key in ("<Return>", "<space>", "<Down>"):
            btn.bind(key, lambda _e, b=btn, name=label: self._on_button(b, name, keyboard=True))
        btn.bind("<Left>", lambda _e: self._focus_relative(-1))
        btn.bind("<Right>", lambda _e: self._focus_relative(1))
        btn.bind("<Escape>", lambda _e: self._leave_bar())
        self._buttons.append((btn, icon))
        self._titles.append(label)

    def set_entry_state(self, names, state):
        """Enable ("normal") or disable ("disabled") the dropdown entries called ``names``
        (their text without the shortcut, e.g. "Preferences..."). An open dropdown is closed."""
        names = set(names)
        if state == "disabled":
            self._disabled |= names
        else:
            self._disabled -= names
        self.close()

    def _set_image(self, label, semantic):
        image = self._image(semantic)
        if image is not None:
            label.config(image=image, compound="left")
            label._icon_ref = image  # keep it alive

    def recolor(self, mode):
        """Re-apply colors (and icon tints) after a theme toggle; an open dropdown is rebuilt."""
        self.mode = mode
        accent = surface(mode)["accent"]
        self.config(bg=self._bg)
        for btn, icon in self._buttons:
            btn.config(bg=self._bg, fg=self._fg, highlightbackground=self._bg, highlightcolor=accent)
            self._set_image(btn, icon)
        if self._popup is not None:
            owner = self._popup_owner
            title = self._titles[self._owner_index(owner)]
            self.close()
            self._suppress = None
            self._open(owner, title)

    def focus_first(self):
        """Give keyboard focus to the first menu label."""
        if self._buttons:
            self._buttons[0][0].focus_set()

    def close(self):
        """Close the open dropdown, if any, and arm the one-click reopen suppression."""
        if self._popup is None:
            return
        owner, popup = self._popup_owner, self._popup
        self._popup = None
        self._popup_owner = None
        try:
            popup.destroy()
        except tk.TclError:  # already destroyed
            pass
        # Clicking the owner label first moves focus off the popup (<FocusOut> closes it) and
        # only then delivers <Button-1>, which would reopen the menu the user meant to toggle
        # shut. Swallow that one click, then clear on the next event-loop turn.
        self._suppress = owner
        if self._suppress_job is not None:
            self.after_cancel(self._suppress_job)
        self._suppress_job = self.after(1, self._clear_suppress)

    # ---- keyboard --------------------------------------------------------
    def _on_f10(self, _event):
        """Enter the bar via F10, remembering the widget to restore on Escape."""
        try:
            self._return_focus = self.focus_get()
        except KeyError:  # Tk reports a widget name Tkinter cannot resolve
            self._return_focus = None
        self.focus_first()
        return "break"

    def _leave_bar(self):
        """Escape from the bar: hand the focus back to where F10 was pressed."""
        target, self._return_focus = self._return_focus, None
        if target is not None:
            try:
                target.focus_set()
            except tk.TclError:  # the previous widget no longer exists
                self.winfo_toplevel().focus_set()

    def _on_destroy(self, event):
        """Remove the window-level F10 binding so it cannot outlive the bar."""
        if event.widget is not self:  # <Destroy> also fires for the children
            return
        toplevel, funcid = self._f10
        if self._suppress_job is not None:
            self.after_cancel(self._suppress_job)
            self._suppress_job = None
        try:
            toplevel.unbind("<F10>", funcid)
        except tk.TclError:  # the toplevel is going away too
            pass

    def _owner_index(self, button):
        return next(i for i, (btn, _icon) in enumerate(self._buttons) if btn is button)

    def _focus_relative(self, delta):
        """Move focus to the neighbouring label, wrapping around."""
        if not self._buttons:
            return
        try:
            focused = self.focus_get()
        except KeyError:
            focused = None
        index = next((i for i, (btn, _icon) in enumerate(self._buttons) if btn is focused), 0)
        self._buttons[(index + delta) % len(self._buttons)][0].focus_set()

    def _step_open_menu(self, delta):
        """Left/Right inside a dropdown: open the neighbouring menu."""
        owner = self._popup_owner
        if owner is None:
            return
        neighbour = self._buttons[(self._owner_index(owner) + delta) % len(self._buttons)][0]
        title = self._titles[self._owner_index(neighbour)]
        self.close()
        self._suppress = None
        neighbour.focus_set()
        self._open(neighbour, title, keyboard=True)

    # ---- dropdown handling ----------------------------------------------
    def _items(self, title):
        """The dropdown rows with the current enabled state."""
        def with_state(item):
            return item._replace(enabled=item.text.partition("\t")[0] not in self._disabled)

        return [item if item is None else with_state(item) for item in self._groups.get(title, ())]

    def _on_button(self, button, title, keyboard=False):
        """Toggle the dropdown for ``button`` (``keyboard`` preselects its first enabled row)."""
        # a click that just closed this menu (via FocusOut) must not reopen it
        if self._suppress is button:
            return
        if self._popup is not None and self._popup_owner is button:
            self.close()
            return
        self.close()
        self._open(button, title, keyboard=keyboard)

    def _open(self, button, title, keyboard=False):
        popup, inner = make_popup(self, self.mode)
        rows = RowList(inner, self.mode, invoke=self._invoke)
        rows.populate(self._items(title))
        popup.rows = rows  # reachable for keyboard tests
        place(popup, button.winfo_rootx(), button.winfo_rooty() + button.winfo_height(), near=button)
        popup.bind("<FocusOut>", lambda _event: self.close())
        bind_navigation(popup, rows, self.close, side=self._step_open_menu)
        self._popup = popup
        self._popup_owner = button
        popup.update_idletasks()
        popup.focus_force()
        if keyboard:
            rows.move(1, start=0)

    def _invoke(self, command):
        self.close()
        command()

    def _clear_suppress(self):
        self._suppress = None
        self._suppress_job = None
