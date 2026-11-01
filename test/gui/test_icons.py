import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))
from gui import icons  # noqa: E402
from gui.icons import catalog  # noqa: E402


class CatalogTest(unittest.TestCase):
    def test_one_glyph_per_meaning(self):
        glyphs = list(catalog.GLYPHS.values())
        self.assertEqual(len(glyphs), len(set(glyphs)))

    def test_nearest_size_follows_the_display_scaling(self):
        self.assertEqual(catalog.nearest_size(16), 16)
        self.assertEqual(catalog.nearest_size(20 * 1.25), 24)  # 125%: 25 px -> 24
        self.assertEqual(catalog.nearest_size(16 * 1.25), 20)  # 125%: 20 px

    def test_unknown_icon_or_size_is_rejected(self):
        with self.assertRaises(ValueError):
            catalog.asset_name("no-such-icon", 16)
        with self.assertRaises(ValueError):
            catalog.asset_name("run", 18)


class AssetsTest(unittest.TestCase):
    def test_every_icon_is_baked_for_every_theme_size_and_state(self):
        folder = icons.assets_dir()
        self.assertIsNotNone(folder, "run tools/generate_icons.py")
        missing = [
            os.path.join(mode, catalog.asset_name(semantic, size, variant))
            for mode in catalog.THEMES
            for semantic in catalog.GLYPHS
            for size in catalog.SIZES
            for variant in catalog.variants_for(semantic)
            if not os.path.isfile(os.path.join(folder, mode, catalog.asset_name(semantic, size, variant)))
        ]
        self.assertEqual(missing, [])

    def test_no_stale_assets(self):
        folder = icons.assets_dir()
        expected = {catalog.asset_name(s, z, v) for s in catalog.GLYPHS for z in catalog.SIZES
                    for v in catalog.variants_for(s)}
        for mode in catalog.THEMES:
            self.assertEqual(set(os.listdir(os.path.join(folder, mode))) - expected, set())


class WithoutAssetsTest(unittest.TestCase):
    def test_buttons_stay_text_only_without_assets(self):
        try:
            import tkinter as tk
            from tkinter import ttk
            root = tk.Tk()
        except Exception as exc:
            self.skipTest(f"no display for Tk: {exc}")
        try:
            root.withdraw()
            button = ttk.Button(root, text="OK")
            with mock.patch.object(icons, "assets_dir", return_value=None):
                icons.ButtonIcons(root).attach(button, "run", "dark")
            self.assertEqual(str(button.cget("image")), "")
        finally:
            root.destroy()


if __name__ == "__main__":
    unittest.main()
