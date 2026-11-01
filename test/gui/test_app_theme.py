"""Follow the Windows light/dark setting live, with a System/Light/Dark choice (B7).

The Windows setting is faked by patching theme.system_mode: no test touches the registry.
"""
import tkinter as tk
import types
import unittest
from unittest import mock

from test_app import AppTestCase, app_module
from gui import dialogs, theme


def walk(widget):
    yield widget
    for child in widget.winfo_children():
        yield from walk(child)


class ResolveModeTest(unittest.TestCase):
    def test_system_follows_the_windows_setting(self):
        with mock.patch.object(theme, "system_mode", return_value="light"):
            self.assertEqual(theme.resolve_mode("auto"), "light")
            self.assertEqual(theme.resolve_mode("system"), "light")
        with mock.patch.object(theme, "system_mode", return_value="dark"):
            self.assertEqual(theme.resolve_mode("auto"), "dark")

    def test_a_pinned_theme_ignores_the_windows_setting(self):
        with mock.patch.object(theme, "system_mode", return_value="dark"):
            self.assertEqual(theme.resolve_mode("light"), "light")
        with mock.patch.object(theme, "system_mode", return_value="light"):
            self.assertEqual(theme.resolve_mode("dark"), "dark")

    def test_unknown_or_empty_values_mean_system(self):
        for value in (None, "", "  ", "neon", "Dark Mode"):
            self.assertEqual(theme.normalize(value), "auto", value)
        self.assertEqual(theme.normalize(" DARK "), "dark")
        self.assertEqual(theme.normalize("System"), "auto")

    def test_system_mode_reads_darkdetect_and_defaults_to_dark(self):
        fake = types.SimpleNamespace(theme=lambda: "Light")
        with mock.patch.object(theme, "darkdetect", fake):
            self.assertEqual(theme.system_mode(), "light")
        with mock.patch.object(theme, "darkdetect", types.SimpleNamespace(theme=lambda: None)):
            self.assertEqual(theme.system_mode(), "dark")
        with mock.patch.object(theme, "darkdetect", None):
            self.assertEqual(theme.system_mode(), "dark")

    def test_a_failing_registry_read_defaults_to_dark(self):
        def broken():
            raise OSError("registry")

        with mock.patch.object(theme, "darkdetect", types.SimpleNamespace(theme=broken)):
            self.assertEqual(theme.system_mode(), "dark")


class LiveThemeTest(AppTestCase):
    """The window follows Windows while the preference is System."""

    gui_ini = "[gui]\ntheme = auto\nkeep_open = True\n"

    def setUp(self):
        # The system is "dark" while the app is built; tests flip it afterwards.
        self.system = mock.patch.object(theme, "system_mode", return_value="dark")
        self.system.start()
        self.addCleanup(self.system.stop)
        super().setUp()

    def set_system(self, mode):
        theme.system_mode.return_value = mode

    def test_it_starts_in_the_system_theme(self):
        self.assertEqual(self.app.theme_pref, "auto")
        self.assertEqual(self.app.theme_mode, "dark")

    def test_a_windows_switch_is_followed_without_a_restart(self):
        before = str(self.app.ok_btn.cget("image"))
        self.set_system("light")
        self.app._poll_system_theme()
        self.assertEqual(self.app.theme_mode, "light")
        self.assertEqual(theme.current(self.root), "light")
        self.assertEqual(str(self.app.log.cget("bg")), theme.palette("light")["bg"])
        self.assertNotEqual(str(self.app.ok_btn.cget("image")), before)  # the icons were re-tinted
        self.set_system("dark")
        self.app._poll_system_theme()
        self.assertEqual(self.app.theme_mode, "dark")
        self.assertEqual(str(self.app.log.cget("bg")), theme.palette("dark")["bg"])

    def test_nothing_is_reapplied_while_the_system_theme_is_unchanged(self):
        with mock.patch.object(self.app, "_apply_theme") as apply_theme:
            self.app._poll_system_theme()
        apply_theme.assert_not_called()

    def test_the_poll_reschedules_itself_every_two_seconds(self):
        with mock.patch.object(self.root, "after") as after:
            self.app._poll_system_theme()
        after.assert_called_once_with(2000, self.app._poll_system_theme)

    def test_the_poll_is_started_when_the_app_is_built(self):
        # Without it the window would only look at Windows at startup (the old behaviour).
        root = tk.Tk()
        self.addCleanup(root.destroy)
        root.withdraw()
        scheduled = []
        with mock.patch.object(root, "after", side_effect=lambda ms, *_args: scheduled.append(ms) or "id"):
            app_module.ExtractorApp(root)
        self.assertIn(2000, scheduled)

    def test_a_pinned_theme_is_not_moved_by_windows(self):
        self.app.theme_pref = "dark"
        self.set_system("light")
        with mock.patch.object(self.app, "_apply_theme") as apply_theme:
            self.app._poll_system_theme()  # not even a pointless re-skin every two seconds
        apply_theme.assert_not_called()
        self.assertEqual(self.app.theme_mode, "dark")

    def test_a_switch_waits_while_a_dialog_is_open_then_applies(self):
        # A dialog's colours are fixed when it is built; re-skinning half of it would look broken.
        self.app._open_run_options()
        win = self.dialogs()[-1]
        self.set_system("light")
        self.app._poll_system_theme()
        self.assertEqual(self.app.theme_mode, "dark")
        dialogs.close_dialog(win)
        self.app._poll_system_theme()
        self.assertEqual(self.app.theme_mode, "light")

    def test_the_poll_survives_a_destroyed_window(self):
        self.root.destroy()
        self.app._poll_system_theme()  # must not raise


class PinTest(AppTestCase):
    gui_ini = "[gui]\ntheme = auto\nkeep_open = True\n"

    def setUp(self):
        self.system = mock.patch.object(theme, "system_mode", return_value="dark")
        self.system.start()
        self.addCleanup(self.system.stop)
        super().setUp()

    def test_ctrl_t_flips_and_pins_the_theme(self):
        self.app._toggle_theme()
        self.assertEqual((self.app.theme_pref, self.app.theme_mode), ("light", "light"))
        theme.system_mode.return_value = "dark"
        self.app._poll_system_theme()
        self.assertEqual(self.app.theme_mode, "light")  # pinned: Windows no longer moves it

    def test_the_preference_is_saved_whether_or_not_it_was_toggled(self):
        self.app._save_settings()
        self.assertEqual(self.app.settings.get("gui", "theme"), "auto")
        self.app._toggle_theme()
        self.app._save_settings()
        self.assertEqual(self.app.settings.get("gui", "theme"), "light")

    def test_ctrl_t_does_nothing_behind_an_open_dialog(self):
        self.app._about()
        self.app._toggle_theme()
        self.assertEqual(self.app.theme_pref, "auto")


class PreferencesThemeTest(AppTestCase):
    gui_ini = "[gui]\ntheme = dark\nkeep_open = True\n"

    def setUp(self):
        self.system = mock.patch.object(theme, "system_mode", return_value="light")
        self.system.start()
        self.addCleanup(self.system.stop)
        super().setUp()

    def open_preferences(self):
        self.app._open_preferences()
        return self.dialogs()[-1]

    def radios(self, win):
        return {w.cget("text"): w for w in walk(win) if w.winfo_class() == "TRadiobutton"}

    def button(self, win, text):
        return next(w for w in walk(win) if w.winfo_class() == "TButton" and w.cget("text") == text)

    def test_preferences_offers_system_light_and_dark_with_the_current_one_selected(self):
        win = self.open_preferences()
        radios = self.radios(win)
        for label in ("System", "Light", "Dark"):
            self.assertIn(label, radios)
        self.assertEqual(self.app.theme_pref, "dark")
        self.assertEqual(win.getvar(str(radios["Dark"].cget("variable"))), "dark")

    def test_saving_a_new_choice_applies_it_at_once_and_stores_it(self):
        win = self.open_preferences()
        self.radios(win)["Light"].invoke()
        self.button(win, "Save").invoke()
        self.assertEqual((self.app.theme_pref, self.app.theme_mode), ("light", "light"))
        self.assertEqual(theme.current(self.root), "light")
        self.assertEqual(self.app.settings.get("gui", "theme"), "light")

    def test_cancel_keeps_the_theme(self):
        win = self.open_preferences()
        self.radios(win)["Light"].invoke()
        self.button(win, "Cancel").invoke()
        self.assertEqual((self.app.theme_pref, self.app.theme_mode), ("dark", "dark"))

    def test_system_is_the_way_back_to_automatic(self):
        win = self.open_preferences()
        self.radios(win)["System"].invoke()
        self.button(win, "Save").invoke()
        self.assertEqual(self.app.theme_pref, "auto")
        self.assertEqual(self.app.theme_mode, "light")  # what the (faked) Windows setting says
        self.assertEqual(self.app.settings.get("gui", "theme"), "auto")
        theme.system_mode.return_value = "dark"
        self.app._poll_system_theme()
        self.assertEqual(self.app.theme_mode, "dark")  # and it follows Windows again

    def test_the_dialog_closes_before_the_new_theme_is_applied(self):
        win = self.open_preferences()
        self.radios(win)["Light"].invoke()
        seen = []
        with mock.patch.object(self.app, "_apply_theme", side_effect=lambda: seen.append(win.winfo_exists())):
            self.button(win, "Save").invoke()
        self.assertEqual(seen, [0])


if __name__ == "__main__":
    unittest.main()
