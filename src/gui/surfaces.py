"""Colours of the self-drawn surfaces that ``theme.palette`` does not carry.

sv-ttk skins the ttk widgets; the log pane, the popup menus, the tooltips and the
status line are plain Tk widgets, so they take their colours from here. Every value
is neutral (background, border, hover, disabled text) or has a meaning (accent for
keyboard focus and selection, ``error`` for failures), and the text ones keep the
4.5:1 contrast target on the surface they sit on (a test checks it). Same dark and
light bases as ``theme.DARK`` / ``theme.LIGHT``.
"""

SURFACES = {
    "dark": {
        "border": "#3a3a3a",       # hairline around inputs and popups
        "hover": "#2d2d2d",        # hovered / keyboard-selected menu row
        "disabled": "#8a8a8a",     # text of a disabled menu row or label
        "accent": "#57c8ff",       # keyboard focus ring (sv-ttk's accent)
        "select_fg": "#000000",    # text drawn on the accent selection
        "error": "#ff817a",        # failure text
    },
    "light": {
        "border": "#d6d6d6",
        "hover": "#e5e5e5",
        "disabled": "#767676",
        "accent": "#005fb8",
        "select_fg": "#ffffff",
        "error": "#b3261e",
    },
}


def surface(mode):
    """The colours for ``mode`` ("dark"; anything else is light)."""
    return SURFACES["dark" if mode == "dark" else "light"]
