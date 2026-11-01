"""Semantic icon names, the Fluent glyph behind each, sizes, themes and file names.

Views ask for an icon by what it means ("run", "browse"), never by glyph name, so a
metaphor changes here once and the same action keeps the same picture everywhere.
Tk-free, so the generator (tools/generate_icons.py) and the tests can import it.
"""

# Fluent ships each glyph on a 16/20/24 px grid; anything else would be resampled.
SIZES = (16, 20, 24)
COMPACT = 16   # icon-only buttons (the "..." browse buttons)
REGULAR = 20   # buttons with a text label

# semantic name -> Microsoft Fluent System Icons (Regular) name, without the size suffix.
# Every glyph must exist on all three grids (16, 20, 24); one glyph per meaning.
GLYPHS = {
    # buttons
    "run": "play",                 # OK: start the extraction / scan / carve
    "dismiss": "dismiss",          # Cancel and Close: both just leave
    "batch": "stack",              # Batch queue
    "browse_file": "document",     # pick the source file
    "browse": "folder-open",       # pick the destination folder
    "save": "save",                # Preferences: Save
    # menu bar titles
    "menu_file": "folder",
    "menu_edit": "edit",
    "menu_help": "question-circle",
}

NORMAL = ""
DISABLED = "disabled"
VARIANTS = (NORMAL, DISABLED)
THEMES = ("light", "dark")

# Text colour of a ttk button per theme and state (sv-ttk 2.6 light/dark themes);
# the PNGs are tinted with these so an icon matches its label.
BUTTON_FOREGROUNDS = {
    "dark": {NORMAL: "#fafafa", DISABLED: "#7a7a7a"},
    "light": {NORMAL: "#1c1c1c", DISABLED: "#a2a2a2"},
}


def nearest_size(wanted):
    """The size step closest to ``wanted`` pixels (ties go to the larger step)."""
    return min(SIZES, key=lambda step: (abs(step - wanted), -step))


def glyph_name(semantic, size):
    """The Fluent icon name for ``semantic`` at ``size``, e.g. ``folder-open-20``."""
    if size not in SIZES:
        raise ValueError(f"icon size must be one of {SIZES}, got {size}")
    try:
        return f"{GLYPHS[semantic]}-{size}"
    except KeyError:
        raise ValueError(f"unknown icon {semantic!r}") from None


def asset_name(semantic, size, variant=NORMAL):
    """File name of a baked icon, e.g. ``browse-16.png`` or ``run-20-disabled.png``."""
    glyph_name(semantic, size)  # validates name and size
    return f"{semantic}-{size}{'-' + variant if variant else ''}.png"
