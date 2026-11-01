"""Theme fixes (B6): entry fonts in dialogs, selection colours, title bar, muted labels, no redundant re-apply."""
import sys
import unittest
from unittest import mock
from tkinter import ttk

import tkinter as tk

from test_app import AppTestCase
from gui import dialogs, theme


def luminance(color):
    channels = [int(color.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground, background):
    high, low = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def walk(widget):
    yield widget
    for child in widget.winfo_children():
        yield from walk(child)


class EntryFontTest(AppTestCase):
    """sv-ttk only swaps entry fonts on <<ThemeChanged>>: entries made later keep the small default."""

    def test_entries_in_run_options_use_the_theme_font(self):
        self.app._open_run_options()
        win = self.dialogs()[-1]
        entries = [w for w in walk(win) if w.winfo_class() in ("TEntry", "TSpinbox", "TCombobox")]
        self.assertGreaterEqual(len(entries), 2)  # Max depth and Password
        for entry in entries:
            self.assertEqual(str(entry.cget("font")), "SunValleyBodyFont", entry)

    def test_the_main_window_entries_use_it_too(self):
        for entry in (self.app.source_entry, self.app.dest_entry):
            self.assertEqual(str(entry.cget("font")), "SunValleyBodyFont")


class TextStyleTest(AppTestCase):
    def test_the_selection_uses_the_theme_accent_in_both_modes(self):
        for mode in ("dark", "light"):
            theme.restyle_text(self.app.log, mode)
            colors = theme.palette(mode)
            self.assertEqual(self.app.log.cget("selectbackground"), colors["accent"], mode)
            self.assertEqual(self.app.log.cget("selectforeground"), colors["select_fg"], mode)
            # a selection stays visible while another widget has focus
            self.assertEqual(self.app.log.cget("inactiveselectbackground"), colors["border"], mode)

    def test_the_selected_text_is_readable_on_the_accent(self):
        for mode in ("dark", "light"):
            colors = theme.palette(mode)
            self.assertGreaterEqual(contrast(colors["select_fg"], colors["accent"]), 4.5, mode)

    def test_the_text_has_a_flat_one_pixel_border_that_marks_focus(self):
        for mode in ("dark", "light"):
            theme.restyle_text(self.app.log, mode)
            colors = theme.palette(mode)
            self.assertEqual(str(self.app.log.cget("relief")), "flat")
            self.assertEqual(int(self.app.log.cget("borderwidth")), 0)
            self.assertEqual(int(self.app.log.cget("highlightthickness")), 1)
            self.assertEqual(self.app.log.cget("highlightbackground"), colors["border"])
            self.assertEqual(self.app.log.cget("highlightcolor"), colors["accent"])

    def test_the_log_keeps_its_hint_colour(self):
        theme.restyle_text(self.app.log, "dark")
        self.assertEqual(str(self.app.log.tag_cget("hint", "foreground")), theme.palette("dark")["hint"])


class CanvasTest(AppTestCase):
    def test_a_dialogs_scroll_canvas_matches_the_ttk_surface_in_both_modes(self):
        # Preferences scrolls inside a Canvas; a white canvas on sv-ttk's #fafafa surface shows a seam.
        for mode in ("light", "dark"):
            theme.apply(self.root, mode)
            self.app.theme_mode = mode
            self.app._open_preferences()
            win = self.dialogs()[-1]
            canvases = [w for w in walk(win) if w.winfo_class() == "Canvas"]
            self.assertTrue(canvases)
            surface = str(ttk.Style(self.root).lookup(".", "background"))
            for canvas in canvases:
                self.assertEqual(str(canvas.cget("bg")), surface, mode)
            dialogs.close_dialog(win)


class MutedLabelTest(AppTestCase):
    def test_muted_labels_have_a_readable_colour_in_both_themes(self):
        style = ttk.Style(self.root)
        for mode in ("light", "dark"):
            theme.apply(self.root, mode)
            surface = str(style.lookup(".", "background"))
            muted = str(style.lookup("Muted.TLabel", "foreground"))
            self.assertEqual(muted, theme.palette(mode)["muted"], mode)
            self.assertGreaterEqual(contrast(muted, surface), 4.5, (mode, muted, surface))

    def test_about_shows_its_tagline_muted(self):
        self.app._about()
        styles = {str(w.cget("style")) for w in walk(self.dialogs()[-1]) if w.winfo_class() == "TLabel"}
        self.assertIn("Muted.TLabel", styles)


class ApplyTest(AppTestCase):
    def test_applying_the_theme_already_set_does_not_set_it_again(self):
        theme.apply(self.root, "dark")
        with mock.patch.object(theme.sv_ttk, "set_theme") as set_theme:
            theme.apply(self.root, "dark")
        set_theme.assert_not_called()

    def test_switching_the_theme_sets_it_once(self):
        theme.apply(self.root, "dark")
        with mock.patch.object(theme.sv_ttk, "set_theme", wraps=theme.sv_ttk.set_theme) as set_theme:
            theme.apply(self.root, "light")
        self.assertEqual(set_theme.call_count, 1)
        self.assertEqual(theme.current(self.root), "light")


@unittest.skipUnless(sys.platform == "win32", "Windows title bar")
class TitleBarTest(AppTestCase):
    def setUp(self):
        super().setUp()
        try:
            import pywinstyles  # noqa: F401
        except ImportError:
            self.skipTest("pywinstyles not installed")

    def test_pywinstyles_gets_the_window_handle_not_the_widget(self):
        # Given a widget it calls window.update(), re-entering the event loop mid-build.
        import pywinstyles
        with mock.patch.object(pywinstyles, "apply_style") as apply_style:
            theme.titlebar(self.root, "dark")
        apply_style.assert_called_once()
        handle, style = apply_style.call_args.args
        self.assertIsInstance(handle, int)
        self.assertNotIsInstance(handle, bool)
        self.assertEqual(style, "dark")

    def test_theming_a_title_bar_never_runs_the_event_loop(self):
        with mock.patch.object(self.root, "update") as update:
            theme.titlebar(self.root, "light")
        update.assert_not_called()


if __name__ == "__main__":
    unittest.main()
