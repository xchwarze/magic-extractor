"""ExtractorApp behaviour, driven headlessly (skipped where Tk has no display)."""
import os
import queue
import shutil
import sys
import tempfile
import time
import tkinter as tk
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))
from gui import app as app_module  # noqa: E402
from gui import runner  # noqa: E402


class AppTestCase(unittest.TestCase):
    """Builds an ExtractorApp whose gui.ini / config.ini live in a temp folder."""

    gui_ini = "[gui]\nkeep_open = True\n"

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.gui_ini_path = os.path.join(self.tmp, "gui.ini")
        self.config_path = os.path.join(self.tmp, "config.ini")
        with open(self.gui_ini_path, "w", encoding="utf-8") as fh:
            fh.write(self.gui_ini)
        with open(self.config_path, "w", encoding="utf-8") as fh:
            fh.write("[settings]\nfix_file_extensions = False\n")
        patches = [
            mock.patch.object(runner, "resolve_gui_config_path", return_value=self.gui_ini_path),
            mock.patch.object(runner, "resolve_config_path", return_value=self.config_path),
        ]
        # No real modal dialog may ever open in a test (it would block the run).
        patches.append(mock.patch.object(app_module.dialogs, "confirm", return_value=False))
        patches.append(mock.patch.object(app_module.dialogs, "show_message"))
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"no display for Tk: {exc}")
        self.root.withdraw()
        self.app = app_module.ExtractorApp(self.root)
        self.root.withdraw()

    def tearDown(self):
        try:
            self.root.destroy()
        except tk.TclError:
            pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def dialogs(self):
        return [w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel) and w.winfo_exists()]


class IconsTest(AppTestCase):
    def test_buttons_and_menu_titles_have_icons(self):
        self.assertNotEqual(str(self.app.ok_btn.cget("image")), "")
        self.assertNotEqual(str(self.app.batch_btn.cget("image")), "")
        self.assertNotEqual(str(self.app.dest_btn.cget("image")), "")
        title, _icon = self.app.menubar._buttons[0]
        self.assertNotEqual(str(title.cget("image")), "")

    def test_theme_toggle_retints_the_icons(self):
        before = str(self.app.ok_btn.cget("image"))
        self.app._toggle_theme()
        self.assertNotEqual(str(self.app.ok_btn.cget("image")), before)


class StartupTest(AppTestCase):
    gui_ini = "stray line before any section\n[gui]\ntheme = system\n"

    def test_malformed_gui_ini_and_unknown_theme_still_start(self):
        self.assertIn(self.app.theme_mode, ("dark", "light"))


class RunLifecycleTest(AppTestCase):
    def pump_until_idle(self, timeout=10):
        deadline = time.monotonic() + timeout
        while self.app._running and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.02)

    def test_backend_that_cannot_start_re_enables_the_buttons(self):
        self.app.source.set(os.path.join(self.tmp, "a.zip"))
        with mock.patch.object(runner, "resolve_backend", return_value=[os.path.join(self.tmp, "missing.exe")]):
            self.app._on_ok()
            self.pump_until_idle()
        self.assertFalse(self.app._running)
        self.assertEqual(str(self.app.ok_btn.cget("state")), "normal")
        self.assertIn("could not run the backend", self.app.log.get("1.0", "end"))

    def test_closing_during_a_run_cancels_it_first(self):
        self.app._set_running(True)
        worker = mock.Mock()
        worker.is_alive.return_value = False  # already stopped: the window closes at once
        self.app.worker = worker
        with mock.patch.object(app_module.dialogs, "confirm", return_value=True):
            self.app._on_close()
        self.assertTrue(self.app.cancel_flag.is_set())
        worker.join.assert_not_called()  # the UI thread never waits on the worker (test_app_close.py)

    def test_closing_during_a_run_can_be_refused(self):
        self.app._set_running(True)
        with mock.patch.object(app_module.dialogs, "confirm", return_value=False):
            self.app._on_close()
        self.assertFalse(self.app.cancel_flag.is_set())
        self.assertTrue(self.root.winfo_exists())
        self.app._set_running(False)

    def test_a_failing_settings_save_never_keeps_the_window_open(self):
        with mock.patch.object(self.app.settings, "save", side_effect=UnicodeEncodeError("x", "", 0, 1, "y")):
            self.app._on_close()
        with self.assertRaises(tk.TclError):
            self.root.winfo_exists()


class BatchTest(AppTestCase):
    def test_batch_picker_queues_jobs_in_the_current_mode(self):
        self.app.mode.set("scan")
        with mock.patch.object(app_module.filedialog, "askopenfilenames", return_value=["C:/x/a.zip"]), \
                mock.patch.object(self.app, "_run_jobs") as run_jobs:
            self.app._on_batch()
        self.assertEqual([job[0] for job in run_jobs.call_args.args[0]], ["scan"])


class LogDrainTest(AppTestCase):
    def test_a_flood_is_drained_in_bounded_batches(self):
        for index in range(2000):
            self.app.log_queue.put(f"line {index}")
        self.app._drain_log()
        self.assertEqual(self.app.log_queue.qsize(), 2000 - self.app.LOG_BATCH)


class PreferencesTest(AppTestCase):
    def open_preferences(self):
        self.app._open_preferences()
        return self.dialogs()[-1]

    def checkbuttons(self, widget):
        found = {}
        for child in widget.winfo_children():
            if child.winfo_class() == "TCheckbutton":
                found[child.cget("text")] = child
            found.update(self.checkbuttons(child))
        return found

    def test_cancel_does_not_change_the_interface_settings(self):
        keep_open = self.app.keep_open.get()
        win = self.open_preferences()
        self.checkbuttons(win)[app_module.GUI_LABELS["keep_open"]].invoke()
        win.destroy()  # Cancel
        self.assertEqual(self.app.keep_open.get(), keep_open)

    def button(self, widget, text):
        for child in widget.winfo_children():
            if child.winfo_class() == "TButton" and child.cget("text") == text:
                return child
            found = self.button(child, text)
            if found is not None:
                return found
        return None

    def test_save_error_is_shown_and_keeps_the_dialog(self):
        win = self.open_preferences()
        with mock.patch.object(app_module.config_io, "write_config", side_effect=PermissionError("read-only")):
            self.button(win, "Save").invoke()
        app_module.dialogs.show_message.assert_called_once()
        self.assertEqual(app_module.dialogs.show_message.call_args.args[3], "Could not save the preferences")
        self.assertTrue(win.winfo_exists())

    def test_dialogs_have_keyboard_bindings(self):
        # Windows will not give a test window keyboard focus, so check the bindings.
        win = self.open_preferences()
        self.assertIn("<Key-Escape>", win.bind())
        self.assertIn("<Key-Return>", win.bind())
        self.assertIn("<Key-Return>", self.root.bind())
        self.assertIn("<Control-Key-comma>", self.root.bind())


if __name__ == "__main__":
    unittest.main()
