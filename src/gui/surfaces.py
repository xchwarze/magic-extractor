"""Colours of the self-drawn surfaces (log pane, popup menus, tooltips, status line).

sv-ttk skins the ttk widgets; these are plain Tk widgets, so they take their colours
from here. The shared ones (bg, fg, border, accent, select_fg, ...) come from
``theme.palette`` so there is one source for them; this module only adds what the
surfaces need on top. Every text colour keeps the 4.5:1 contrast target on the surface
it sits on (a test checks it).
"""
from gui import theme

# Only what theme.palette does not carry. "muted" here is the secondary text of popup
# rows (shortcuts), readable on both the popup bg and the hover row, so it is darker
# in light mode than theme's Muted.TLabel colour (which sits on sv-ttk's surface).
_EXTRA = {
    "dark": {
        "hover": "#2d2d2d",        # hovered / keyboard-selected menu row
        "disabled": "#8a8a8a",     # text of a disabled menu row or label
        "muted": "#a0a0a0",        # shortcuts in popups
        "error": "#ff817a",        # failure text
    },
    "light": {
        "hover": "#e5e5e5",
        "disabled": "#767676",
        "muted": "#595959",
        "error": "#b3261e",
    },
}


def surface(mode):
    """The colours for ``mode`` ("dark"; anything else is light)."""
    key = "dark" if mode == "dark" else "light"
    colors = dict(theme.palette(key))
    colors.update(_EXTRA[key])
    return colors
