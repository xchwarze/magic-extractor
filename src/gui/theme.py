"""Dark/light theming for the GUI.

Wraps sv-ttk (Sun Valley ttk theme) for ttk widgets, recolors the few non-ttk
widgets (the log Text, Toplevel dialogs) by hand, and darkens the Windows title
bar. All third-party imports degrade gracefully: if sv-ttk / darkdetect /
pywinstyles are missing, the GUI still runs with the default ttk look.
"""
import sys
import tkinter as tk

try:
    import sv_ttk
except ImportError:  # theme optional
    sv_ttk = None

try:
    import darkdetect
except ImportError:
    darkdetect = None

# Palette for non-ttk widgets sv-ttk does not skin.
# hint/link pass the 4.5:1 contrast target on their bg (WCAG AA body text); muted is the
# secondary text of ttk labels (Muted.TLabel) and passes it on sv-ttk's own surface, which is
# #fafafa in light mode (hint, made for the white Text, is 4.49:1 there). accent is sv-ttk's
# accent, border a hairline, select_fg the text drawn on the accent (a selection).
DARK = {"bg": "#1c1c1c", "fg": "#fafafa", "hint": "#a0a0a0", "link": "#6ea8fe",
        "muted": "#a0a0a0", "border": "#3a3a3a", "accent": "#57c8ff", "select_fg": "#000000"}
LIGHT = {"bg": "#ffffff", "fg": "#000000", "hint": "#6c757d", "link": "#0a58ca",
         "muted": "#666666", "border": "#d6d6d6", "accent": "#005fb8", "select_fg": "#ffffff"}
THEMES = ("auto", "dark", "light")


def is_available():
    """True when sv-ttk is installed (real theming possible)."""
    return sv_ttk is not None


def initial_mode():
    """OS theme via darkdetect; fall back to dark."""
    if darkdetect is not None:
        detected = darkdetect.theme()
        if detected:
            return detected.lower()
    return "dark"


def current(root):
    """Current mode string ('dark'/'light'); 'light' when sv-ttk absent."""
    if sv_ttk is not None:
        return sv_ttk.get_theme()
    return "light"


def apply(root, mode):
    """Apply mode ('dark'/'light') to ttk widgets + the Windows title bar + native menus."""
    if sv_ttk is not None:
        # A set_theme to the theme already in use would re-fire <<ThemeChanged>> and
        # re-skin every widget for nothing.
        if sv_ttk.get_theme(root) != mode:
            sv_ttk.set_theme(mode, root)
    _muted_label_style(root, mode)  # ttk styles are per theme: redo it after every switch
    _title_bar(root, mode)
    _dark_menu_popups(mode)


def toggle(root):
    """Flip theme; return the new mode."""
    new_mode = "light" if current(root) == "dark" else "dark"
    apply(root, new_mode)
    return new_mode


# Bootstrap 5.3 "alert-warning" colors (light / dark color mode).
ALERT_WARNING = {
    "light": {"bg": "#fff3cd", "fg": "#664d03", "border": "#ffe69c"},
    "dark": {"bg": "#332701", "fg": "#ffda6a", "border": "#997404"},
}


def alert_colors(mode):
    """Return {'bg', 'fg', 'border'} for a warning alert in the given mode."""
    return ALERT_WARNING["dark" if mode == "dark" else "light"]


_applied_font_factor = {}


def scale_theme_fonts(root):
    """
    Scale sv-ttk's fonts with the display scaling. They are pixel-sized
    (negative sizes), which Tk's scaling never reaches, so in a DPI-aware
    process ttk text would stay at 100% while geometry and Tk's own fonts grow.
    No-op at 96 DPI or without sv-ttk; safe to call repeatedly (never compounds).
    """
    from tkinter import font

    try:
        factor = float(root.winfo_fpixels("1i")) / 96.0
        applied = _applied_font_factor.get(str(root), 1.0)
        if abs(factor - applied) < 0.01:
            return
        for name in font.names(root):
            if not name.startswith("SunValley"):
                continue  # only sv-ttk's fonts are pixel-sized
            named = font.nametofont(name, root=root)
            size = int(named.cget("size"))
            if size < 0:
                named.configure(size=round(size / applied * factor))
        _applied_font_factor[str(root)] = factor
    except Exception:  # never let font tuning stop the GUI
        pass


def body_font(widget):
    """The theme's body font, so Tk-only widgets (menus, alerts) match ttk text."""
    from tkinter import font

    try:
        if "SunValleyBodyFont" in font.names(widget):
            return "SunValleyBodyFont"
    except Exception:
        pass
    return "TkDefaultFont"


def heading_font(widget):
    """The theme's strong body font for a dialog's lead sentence."""
    from tkinter import font

    try:
        if "SunValleyBodyStrongFont" in font.names(widget):
            return "SunValleyBodyStrongFont"
    except Exception:
        pass
    return "TkHeadingFont"


def palette(mode):
    """Return {'bg':..., 'fg':...} for the given mode."""
    return DARK if mode == "dark" else LIGHT


def restyle_text(widget, mode):
    """Recolor a tk.Text (not covered by sv-ttk): colors, selection and a flat border."""
    colors = palette(mode)
    widget.config(
        bg=colors["bg"], fg=colors["fg"], insertbackground=colors["fg"],
        selectbackground=colors["accent"], selectforeground=colors["select_fg"],
        # a selection stays visible while another widget has the focus
        inactiveselectbackground=colors["border"],
        # Tk's default 3D relief clashes with Sun Valley: a flat 1 px frame, accent when focused
        relief="flat", borderwidth=0, highlightthickness=1,
        highlightbackground=colors["border"], highlightcolor=colors["accent"],
    )
    widget.tag_config("hint", foreground=colors["hint"])


def restyle_canvas(widget):
    """Match a tk.Canvas to the ttk surface it sits on (sv-ttk's, not the Text palette's)."""
    from tkinter import ttk

    try:
        widget.config(bg=ttk.Style(widget).lookup(".", "background") or palette(current(widget))["bg"])
    except tk.TclError:
        pass


def apply_widget_tree(widget, mode):
    """Theme what sv-ttk leaves out, below ``widget``: Text and Canvas colors, and the entry font.

    sv-ttk swaps the font of Entry/Combobox/Spinbox only on <<ThemeChanged>>, so widgets
    created later (a dialog's Password box, the Max depth spinner) would keep the smaller
    default font. Call it once a dialog is built, before it is measured.
    """
    try:
        widget_class = str(widget.winfo_class())
        children = widget.winfo_children()
    except tk.TclError:  # destroyed while walking
        return
    if widget_class == "Text":
        restyle_text(widget, mode)
    elif widget_class == "Canvas":
        restyle_canvas(widget)
    elif widget_class in ("TEntry", "TCombobox", "TSpinbox") and sv_ttk is not None:
        try:
            widget.tk.call("config_entry_font", widget)  # sv-ttk's own proc
        except tk.TclError:
            pass
    for child in children:
        apply_widget_tree(child, mode)


def _muted_label_style(root, mode):
    """``Muted.TLabel``: a TLabel in the secondary-text color (sv-ttk has none)."""
    from tkinter import ttk

    try:
        ttk.Style(root).configure("Muted.TLabel", foreground=palette(mode)["muted"])
    except tk.TclError:
        pass


def restyle_toplevel(win, mode):
    """Recolor a Toplevel background to match the theme."""
    win.config(bg=palette(mode)["bg"])


def titlebar(win, mode):
    """Darken/lighten a window's title bar (Windows). Call once the window is
    mapped. No-op elsewhere and on any failure."""
    _title_bar(win, mode)


def restyle_menu(menu, mode):
    """Recolor a tk.Menu dropdown (sv-ttk does not skin menus)."""
    colors = palette(mode)
    active_bg = "#2d2d2d" if mode == "dark" else "#e5e5e5"
    menu.config(
        bg=colors["bg"], fg=colors["fg"],
        activebackground=active_bg, activeforeground=colors["fg"],
        borderwidth=0,
    )


def _dark_menu_popups(mode):
    """
    Make native Win32 menus (the OS-rendered tk.Menu dropdowns, which ignore
    bg/fg) render dark, via the undocumented uxtheme app-mode API. Best-effort:
    the ordinals exist on Win10 1809+; any failure is silently ignored.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        uxtheme = ctypes.windll.uxtheme
        set_preferred_app_mode = uxtheme[135]  # SetPreferredAppMode
        set_preferred_app_mode.argtypes = [ctypes.c_int]
        set_preferred_app_mode.restype = ctypes.c_int
        # 2 = ForceDark, 1 = AllowDark, 0 = Default
        set_preferred_app_mode(2 if mode == "dark" else 0)
        uxtheme[136]()  # FlushMenuThemes
    except Exception:
        pass


def _frame_hwnd(win):
    """HWND of the native frame around a Tk window (``winfo_id`` is its client child).

    update_idletasks realizes the window without running event handlers.
    """
    import ctypes
    from ctypes import wintypes

    win.update_idletasks()
    user32 = ctypes.WinDLL("user32", use_last_error=True)  # private: own prototypes
    user32.GetParent.restype = wintypes.HWND
    user32.GetParent.argtypes = (wintypes.HWND,)
    return int(user32.GetParent(win.winfo_id()) or win.winfo_id())


def _title_bar(root, mode):
    """Dark title bar on Windows; no-op elsewhere and on any failure."""
    if sys.platform != "win32":
        return
    try:
        hwnd = _frame_hwnd(root)
    except (AttributeError, OSError, tk.TclError):
        return
    # pywinstyles gets the HWND, not the widget: given a widget it calls root.update(),
    # which re-enters the event loop (queued callbacks run in the middle of building the
    # window) and forces a full layout and paint pass.
    try:
        import pywinstyles
        pywinstyles.apply_style(hwnd, "dark" if mode == "dark" else "normal")
        return
    except Exception:
        pass
    # Fallback: raw DWM attribute (DWMWA_USE_IMMERSIVE_DARK_MODE = 20).
    try:
        import ctypes
        value = ctypes.c_int(2 if mode == "dark" else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(value), ctypes.sizeof(value)
        )
    except Exception:
        pass
