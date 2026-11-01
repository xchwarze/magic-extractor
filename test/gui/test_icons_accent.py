"""Icons on the accent (primary) button have their own tints."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))
from gui import icons  # noqa: E402
from gui.icons import catalog  # noqa: E402


class CatalogTest(unittest.TestCase):
    def test_only_accent_icons_have_the_accent_variants(self):
        self.assertEqual(catalog.variants_for("save"), (catalog.NORMAL, catalog.DISABLED, catalog.ACCENT, catalog.ACCENT_DISABLED))
        self.assertEqual(catalog.variants_for("batch"), (catalog.NORMAL, catalog.DISABLED))

    def test_every_accent_icon_is_a_known_icon(self):
        self.assertLessEqual(catalog.ACCENT_ICONS, set(catalog.GLYPHS))

    def test_the_dialog_button_icons_exist(self):
        # confirm: delete / stop / dismiss; Preferences: save; message dialogs: dismiss.
        for name in ("delete", "stop", "dismiss", "save"):
            self.assertIn(name, catalog.GLYPHS)
        self.assertLessEqual({"save", "dismiss"}, catalog.ACCENT_ICONS)  # shown on Accent.TButton


class AccentButtonTest(unittest.TestCase):
    def setUp(self):
        try:
            import tkinter as tk
            from tkinter import ttk
            self.root = tk.Tk()
        except Exception as exc:
            self.skipTest(f"no display for Tk: {exc}")
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.ttk = ttk
        try:
            import sv_ttk
        except ImportError:
            self.skipTest("sv-ttk not installed")
        self.sv_ttk = sv_ttk

    def image_of(self, button):
        return str(button.cget("image")[0])

    def test_an_accent_button_gets_the_accent_tint_and_a_plain_one_does_not(self):
        self.sv_ttk.set_theme("dark")
        helper = icons.ButtonIcons(self.root)
        plain = helper.attach(self.ttk.Button(self.root, text="Save"), "save", "dark")
        accent = helper.attach(self.ttk.Button(self.root, text="Save", style="Accent.TButton"), "save", "dark")
        size = icons.icon_size(self.root, catalog.REGULAR)
        gap = round(icons.GAP * icons.dpi_scale(self.root))
        self.assertEqual(self.image_of(plain), str(helper.photo("dark", "save", size, catalog.NORMAL, gap)))
        self.assertEqual(self.image_of(accent), str(helper.photo("dark", "save", size, catalog.ACCENT, gap)))
        self.assertNotEqual(self.image_of(plain), self.image_of(accent))

    def test_retheming_keeps_the_accent_tint(self):
        self.sv_ttk.set_theme("light")
        helper = icons.ButtonIcons(self.root)
        accent = helper.attach(self.ttk.Button(self.root, text="Close", style="Accent.TButton"), "dismiss", "light")
        helper.retheme("dark")
        size = icons.icon_size(self.root, catalog.REGULAR)
        gap = round(icons.GAP * icons.dpi_scale(self.root))
        self.assertEqual(self.image_of(accent), str(helper.photo("dark", "dismiss", size, catalog.ACCENT, gap)))

    def test_the_baked_tints_match_sv_ttk(self):
        # The PNGs are tinted with constants; fail when sv-ttk's button colours drift from them.
        style = self.ttk.Style(self.root)
        for mode in catalog.THEMES:
            self.sv_ttk.set_theme(mode)
            for name, normal, disabled in (("TButton", catalog.NORMAL, catalog.DISABLED),
                                           ("Accent.TButton", catalog.ACCENT, catalog.ACCENT_DISABLED)):
                self.assertEqual(str(style.lookup(name, "foreground", ("!disabled",))),
                                 catalog.BUTTON_FOREGROUNDS[mode][normal], (mode, name))
                self.assertEqual(str(style.lookup(name, "foreground", ("disabled",))),
                                 catalog.BUTTON_FOREGROUNDS[mode][disabled], (mode, name))


if __name__ == "__main__":
    unittest.main()
