"""Dark/light theming for the GUI.

Wraps sv-ttk (Sun Valley ttk theme) for ttk widgets, recolors the few non-ttk
widgets (the log Text, Toplevel dialogs) by hand, and darkens the Windows title
bar. All third-party imports degrade gracefully: if sv-ttk / darkdetect /
pywinstyles are missing, the GUI still runs with the default ttk look.
"""
import sys

try:
    import sv_ttk
except ImportError:  # theme optional
    sv_ttk = None

try:
    import darkdetect
except ImportError:
    darkdetect = None

# Palette for non-ttk widgets sv-ttk does not skin.
DARK = {"bg": "#1c1c1c", "fg": "#fafafa"}
LIGHT = {"bg": "#ffffff", "fg": "#000000"}


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
    """Apply mode ('dark'/'light') to ttk widgets + the Windows title bar."""
    if sv_ttk is not None:
        sv_ttk.set_theme(mode)
    _title_bar(root, mode)


def toggle(root):
    """Flip theme; return the new mode."""
    new_mode = "light" if current(root) == "dark" else "dark"
    apply(root, new_mode)
    return new_mode


def palette(mode):
    """Return {'bg':..., 'fg':...} for the given mode."""
    return DARK if mode == "dark" else LIGHT


def restyle_text(widget, mode):
    """Recolor a tk.Text (not covered by sv-ttk)."""
    colors = palette(mode)
    widget.config(bg=colors["bg"], fg=colors["fg"], insertbackground=colors["fg"])


def restyle_toplevel(win, mode):
    """Recolor a Toplevel background to match the theme."""
    win.config(bg=palette(mode)["bg"])


def _title_bar(root, mode):
    """Dark title bar on Windows; no-op elsewhere and on any failure."""
    if sys.platform != "win32":
        return
    try:
        import pywinstyles
        pywinstyles.apply_style(root, "dark" if mode == "dark" else "normal")
        return
    except Exception:
        pass
    # Fallback: raw DWM attribute (DWMWA_USE_IMMERSIVE_DARK_MODE = 20).
    try:
        import ctypes
        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        value = ctypes.c_int(2 if mode == "dark" else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd, 20, ctypes.byref(value), ctypes.sizeof(value)
        )
    except Exception:
        pass
