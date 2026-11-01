"""The log pane: a read-only, scrollable, bounded text area for the run output.

Why not a ``state="disabled"`` Text: a disabled Text is skipped by Tab, cannot take
focus on click and shows no caret, so the output could not be selected with the
keyboard. It stays ``normal`` and only the keys that edit are swallowed.
"""
import tkinter as tk

from gui import theme
from gui.autoscroll import AutoScrollbar
from gui.surfaces import surface

MAX_LINES = 5000  # oldest lines beyond this are dropped, so a long session stays light

_EDITING_KEYSYMS = frozenset(("BackSpace", "Delete", "Return", "KP_Enter"))
# Ctrl+<letter> bindings of the Text class that change text: delete char/line end,
# backspace, open line, transpose, paste, cut, redo, undo.
_EDITING_CONTROL_LETTERS = frozenset("dhkotvxyz")
_SHIFT = 0x1
_CONTROL = 0x4
_ALT = 0x20000  # Windows: the Alt state bit

# Virtual events whose class bindings would still edit a state="normal" Text.
_MUTATING_EVENTS = ("<<Paste>>", "<<PasteSelection>>", "<<Cut>>", "<<Clear>>", "<<Undo>>", "<<Redo>>")


def is_editing_key(state, keysym, char):
    """True for a key press that would change the text of a Text (it must be swallowed).

    Navigation, selection (Shift+arrows, Ctrl+A) and copy (Ctrl+C, Ctrl+Insert) are not
    editing; neither are Alt accelerators.
    """
    state = state if isinstance(state, int) else 0
    keysym = str(keysym)
    if state & _ALT:
        return False
    if state & _CONTROL:
        return keysym in _EDITING_KEYSYMS or keysym.lower() in _EDITING_CONTROL_LETTERS
    if keysym == "Insert":
        return bool(state & _SHIFT)  # Shift+Insert pastes; Insert alone only toggles overwrite
    if keysym == "Delete" and state & _SHIFT:
        return True  # Shift+Delete cuts
    if keysym in _EDITING_KEYSYMS:
        return True
    char = str(char)
    return bool(char) and char.isprintable()


def make_readonly(text):
    """Make ``text`` a read-only, focusable, selectable, copyable pane (see the module note)."""

    def on_key(event):
        return "break" if is_editing_key(event.state, event.keysym, event.char) else None

    def focus_next(event):
        following = event.widget.tk_focusNext()
        if following is not None:
            following.focus_set()
        return "break"  # Tab leaves the pane instead of inserting a tab

    def focus_prev(event):
        preceding = event.widget.tk_focusPrev()
        if preceding is not None:
            preceding.focus_set()
        return "break"

    def select_all(_event):
        text.tag_add("sel", "1.0", "end-1c")
        return "break"

    text.bind("<Key>", on_key)
    text.bind("<Tab>", focus_next)
    text.bind("<Shift-Tab>", focus_prev)
    text.bind("<ISO_Left_Tab>", focus_prev)
    text.bind("<Control-a>", select_all)
    for sequence in _MUTATING_EVENTS:
        text.bind(sequence, lambda _event: "break")
    return text


class LogPane:
    """A read-only monospace text with an auto-hiding scrollbar and a placeholder.

    ``frame`` is what the caller packs or grids; ``text`` is the Text itself (drop
    targets, focus and tests use it). Lines are added with :meth:`append`.
    """

    def __init__(self, parent, placeholder, mode, max_lines=MAX_LINES):
        self.placeholder = placeholder
        self.max_lines = max_lines
        self._empty = True
        self._scroll_job = None
        self.frame = tk.Frame(parent, borderwidth=0, highlightthickness=0)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(0, weight=1)
        # TkFixedFont follows the OS and the display scaling; tool output lines up in columns.
        self.text = tk.Text(self.frame, height=14, wrap="word", undo=False,
                            font="TkFixedFont", padx=8, pady=6)
        self.text.grid(row=0, column=0, sticky="nsew")
        make_readonly(self.text)
        scrollbar = AutoScrollbar(self.frame, orient="vertical", command=self.text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.text.configure(yscrollcommand=scrollbar.set)
        self.restyle(mode)
        self.show_placeholder()

    # ---- content ---------------------------------------------------------
    @property
    def is_empty(self):
        """True while the placeholder (not output) is shown."""
        return self._empty

    def show_placeholder(self):
        """Replace everything with the placeholder hint."""
        self._cancel_scroll()
        self.text.delete("1.0", "end")
        self.text.insert("1.0", self.placeholder, ("hint",))
        self._empty = True

    clear = show_placeholder

    def append(self, content):
        """Add ``content`` as new line(s); the placeholder gives way to the first output.

        The oldest lines beyond ``max_lines`` are dropped. The view follows the end only
        when the reader was already there (scrolling up to read is not undone), and it
        scrolls once per burst of appends, when Tk next goes idle.
        """
        text = self.text
        # An unmapped Text never updates its view fractions: keep following then.
        at_end = (self._scroll_job is not None or self._empty or not text.winfo_viewable()
                  or text.yview()[1] >= 1.0)
        if self._empty:
            text.delete("1.0", "end")
            self._empty = False
        text.insert("end", content + "\n")
        excess = int(text.index("end-1c").split(".")[0]) - 1 - self.max_lines
        if excess > 0:
            text.delete("1.0", f"{excess + 1}.0")
        if at_end and self._scroll_job is None:
            self._scroll_job = text.after_idle(self._scroll_to_end)

    def _scroll_to_end(self):
        self._scroll_job = None
        try:
            self.text.see("end")
        except tk.TclError:  # the pane was destroyed before the idle moment
            pass

    def _cancel_scroll(self):
        if self._scroll_job is not None:
            try:
                self.text.after_cancel(self._scroll_job)
            except tk.TclError:
                pass
            self._scroll_job = None

    def get_all(self):
        """The output text ("" while the placeholder is shown)."""
        return "" if self._empty else self.text.get("1.0", "end-1c")

    def selected_text(self):
        """The selected text ("" when nothing is selected or only the placeholder shows)."""
        if self._empty:
            return ""
        try:
            return self.text.get("sel.first", "sel.last")
        except tk.TclError:
            return ""

    # ---- look ------------------------------------------------------------
    def restyle(self, mode):
        """Colour the Text for ``mode`` (sv-ttk does not skin it)."""
        theme.restyle_text(self.text, mode)
        colors = surface(mode)
        self.text.config(
            relief="flat", borderwidth=0, highlightthickness=1,
            highlightbackground=colors["border"], highlightcolor=colors["accent"],  # focus ring
            selectbackground=colors["accent"], selectforeground=colors["select_fg"],
            # keep a selection readable while another widget (or a popup menu) has focus
            inactiveselectbackground=colors["border"],
        )
