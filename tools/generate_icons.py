"""Bake the GUI's button icons into pre-tinted PNGs (dev tool, not shipped).

Usage (from the repo root, with the icon tooling installed)::

    pip install "tkinter-icons[fluent]>=5.1" "pillow>=10"
    python tools/generate_icons.py

Reads src/gui/icons/catalog.py (semantic name -> Microsoft Fluent System Icons
Regular glyph, sizes 16/20/24) and writes src/gui/icons/assets/<light|dark>/
<name>-<size>[-disabled].png. The GUI loads those PNGs with tk.PhotoImage, so at
runtime it needs neither the icon font, tkinter-icons nor Pillow; light and dark
mode come from the two pre-tinted sets.

Only the glyph coverage (alpha) comes from the renderer; the tint is applied here
with the exact button text colour. The output is deterministic (no metadata), so
re-running gives byte-identical files. Re-run after changing the catalog or its
colours, and commit the PNGs.
"""
import argparse
import io
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from gui.icons import catalog  # noqa: E402

DEFAULT_OUTPUT = os.path.join(ROOT, "src", "gui", "icons", "assets")


def bake(renderer, semantic, size, color):
    """One icon as PNG bytes: the glyph coverage filled with ``color``."""
    from PIL import Image

    mask = renderer.render_pil(catalog.glyph_name(semantic, size), size=size, style="regular").getchannel("A")
    canvas = Image.new("RGBA", mask.size, color)
    canvas.putalpha(mask)
    encoded = io.BytesIO()
    canvas.save(encoded, format="PNG", optimize=True, compress_level=9)
    return encoded.getvalue()


def generate(output):
    try:
        import PIL.Image  # noqa: F401
        from tkinter_icons import FluentIcon
    except ImportError:
        sys.exit('missing icon tooling: pip install "tkinter-icons[fluent]>=5.1" "pillow>=10"')
    written = []
    for mode in catalog.THEMES:
        folder = os.path.join(output, mode)
        shutil.rmtree(folder, ignore_errors=True)
        os.makedirs(folder)
        for semantic in catalog.GLYPHS:
            for size in catalog.SIZES:
                for variant in catalog.VARIANTS:
                    color = catalog.BUTTON_FOREGROUNDS[mode][variant]
                    target = os.path.join(folder, catalog.asset_name(semantic, size, variant))
                    with open(target, "wb") as fh:
                        fh.write(bake(FluentIcon, semantic, size, color))
                    written.append(target)
    return written


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="target folder (default: %(default)s)")
    written = generate(os.path.abspath(parser.parse_args(argv).output))
    total = sum(os.path.getsize(path) for path in written)
    print(f"wrote {len(written)} icons ({total / 1024:.1f} KiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
