"""The main window's output surfaces: log pane, status line, error reporting (headless Tk)."""
import os
import sys
import threading
import time
import tkinter as tk
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_app import AppTestCase  # noqa: E402
from gui import app as app_module  # noqa: E402


def line_count(text):
    """Lines the Text holds (it always ends with the newline of the last one)."""
    return int(text.index("end-1c").split(".")[0]) - 1


class LogPaneTest(AppTestCase):
    def test_the_log_is_read_only_but_stays_focusable(self):
        # state="disabled" would drop it from Tab order and block selecting with the keyboard.
        self.assertEqual(str(self.app.log.cget("state")), "normal")
        self.assertIn("<Key>", self.app.log.bind())

    def test_the_log_never_grows_without_bound(self):
        self.app._append("\n".join(f"line {i}" for i in range(6000)))
        self.assertLessEqual(line_count(self.app.log), self.app.log_pane.max_lines)
        self.assertTrue(self.app.log.get("1.0", "2.0").startswith("line 1000"))  # oldest dropped first

    def test_a_reader_scrolled_up_is_not_pulled_to_the_end(self):
        self.app._append("first")
        self.root.update_idletasks()  # the first line's own scroll is done; the reader then moves up
        with mock.patch.object(self.app.log, "winfo_viewable", return_value=True), \
                mock.patch.object(self.app.log, "yview", return_value=(0.1, 0.5)), \
                mock.patch.object(self.app.log, "see") as see:
            self.app._append("new output")
            self.root.update_idletasks()
        see.assert_not_called()

    def test_a_reader_at_the_end_follows_it_once_per_burst(self):
        self.app._append("first")
        self.root.update_idletasks()
        with mock.patch.object(self.app.log, "winfo_viewable", return_value=True), \
                mock.patch.object(self.app.log, "yview", return_value=(0.5, 1.0)), \
                mock.patch.object(self.app.log, "see") as see:
            for index in range(5):
                self.app._append(f"burst {index}")
            self.root.update_idletasks()
        see.assert_called_once_with("end")

    def test_clear_brings_the_placeholder_back(self):
        self.app._append("something")
        self.app._clear_log()
        self.assertIn("Ready", self.app.log.get("1.0", "end"))
        self.assertTrue(self.app.log_pane.is_empty)

    def test_output_replaces_the_placeholder(self):
        self.app._append("hello")
        text = self.app.log.get("1.0", "end")
        self.assertIn("hello", text)
        self.assertNotIn("Ready", text)

    def test_the_log_uses_a_monospace_font(self):
        self.assertEqual(str(self.app.log.cget("font")), "TkFixedFont")

    def test_a_theme_toggle_recolors_the_log_and_keeps_a_selection_readable(self):
        before = str(self.app.log.cget("bg"))
        self.app._toggle_theme()
        self.assertNotEqual(str(self.app.log.cget("bg")), before)
        self.assertNotEqual(str(self.app.log.cget("inactiveselectbackground")), "")


class LogMenuTest(AppTestCase):
    def setUp(self):
        super().setUp()
        # A test must not steal keyboard focus from whatever the developer is typing in.
        patch = mock.patch.object(tk.Misc, "focus_force")
        patch.start()
        self.addCleanup(patch.stop)

    def open_menu(self):
        self.app._show_log_menu(50, 50)
        return self.dialogs()[-1].rows

    def labels(self, rows):
        return [(row.widgets[1].cget("text"), row.enabled) for row in rows.rows]

    def test_every_row_is_disabled_while_the_log_only_shows_the_placeholder(self):
        rows = self.open_menu()
        self.assertEqual(self.labels(rows), [("Copy selection", False), ("Copy all", False),
                                             ("Save as...", False), ("Clear", False)])

    def test_rows_enable_with_output_and_with_a_selection(self):
        self.app._append("alpha\nbeta")
        self.assertEqual([enabled for _, enabled in self.labels(self.open_menu())],
                         [False, True, True, True])  # nothing selected yet
        self.dialogs()[-1].destroy()
        self.app.log.tag_add("sel", "1.0", "1.5")
        self.assertTrue(self.labels(self.open_menu())[0][1])

    def test_every_row_carries_an_icon(self):
        rows = self.open_menu()
        for row in rows.rows:
            self.assertNotEqual(str(row.widgets[1].cget("image")), "")

    def test_right_click_and_the_keyboard_keys_are_bound(self):
        bound = self.app.log.bind()
        for sequence in ("<Button-3>", "<Shift-Key-F10>", "<Key-App>"):
            self.assertIn(sequence, bound)

    def test_right_click_opens_the_menu(self):
        self.app.log.event_generate("<Button-3>", x=5, y=5)
        self.assertEqual(len(self.dialogs()), 1)

    def test_copy_all_puts_the_output_on_the_clipboard_without_the_placeholder(self):
        self.app._append("alpha")
        with mock.patch.object(self.root, "clipboard_clear"), \
                mock.patch.object(self.root, "clipboard_append") as append:
            self.app._copy_log_all()
        append.assert_called_once_with("alpha\n")

    def test_copy_selection_copies_only_the_selection(self):
        self.app._append("alpha beta")
        self.app.log.tag_add("sel", "1.6", "1.10")
        with mock.patch.object(self.root, "clipboard_clear"), \
                mock.patch.object(self.root, "clipboard_append") as append:
            self.app._copy_log_selection()
        append.assert_called_once_with("beta")

    def test_a_locked_clipboard_is_reported_not_raised(self):
        self.app._append("alpha")
        with mock.patch.object(self.root, "clipboard_clear", side_effect=tk.TclError("locked")), \
                self.assertLogs(level="WARNING"):
            self.app._copy_log_all()
        self.assertIn("could not copy", self.app.log.get("1.0", "end").lower())

    def test_save_as_writes_the_output_as_utf8(self):
        line = "extracting архив.zip"
        self.app._append(line)
        target = os.path.join(self.tmp, "saved.log")
        with mock.patch.object(app_module.filedialog, "asksaveasfilename", return_value=target):
            self.app._save_log_as()
        with open(target, encoding="utf-8") as handle:
            self.assertIn(line, handle.read())

    def test_cancelling_save_as_writes_nothing(self):
        self.app._append("alpha")
        with mock.patch.object(app_module.filedialog, "asksaveasfilename", return_value=""), \
                mock.patch.object(app_module, "save_text") as save:
            self.app._save_log_as()
        save.assert_not_called()

    def test_a_save_that_fails_is_reported_in_the_log(self):
        self.app._append("alpha")
        with mock.patch.object(app_module.filedialog, "asksaveasfilename", return_value=self.tmp), \
                self.assertLogs(level="ERROR"):  # the target is a folder
            self.app._save_log_as()
        self.assertIn("could not save", self.app.log.get("1.0", "end"))

    def test_clear_from_the_menu_empties_the_log(self):
        self.app._append("alpha")
        self.open_menu().activate(3)
        self.assertTrue(self.app.log_pane.is_empty)


class RunStatusTest(AppTestCase):
    """The status line and the busy indicator follow a (batch) run; the worker only uses queues."""

    def setUp(self):
        super().setUp()
        patch = mock.patch.object(app_module.runner, "resolve_backend", return_value=["backend"])
        patch.start()
        self.addCleanup(patch.stop)
        self.release = threading.Event()
        self.addCleanup(self.release.set)

    def jobs(self, *names):
        return [("extract", os.path.join(self.tmp, name), "") for name in names]

    def pump(self, until, timeout=10):
        deadline = time.monotonic() + timeout
        while not until() and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.assertTrue(until(), "timed out waiting for the run")

    def fake_streaming(self, codes, hold=None):
        """run_streaming stand-in: exit code per source file name; waits on ``hold`` for one of them."""
        def run(argv, on_line, should_cancel, poll_seconds=0.2):
            name = os.path.basename(argv[2])
            on_line(f"working on {name}")
            if name == hold:
                while not self.release.is_set() and not should_cancel():
                    time.sleep(0.01)
                if should_cancel():
                    return -1
            return codes[name]
        return run

    def test_status_follows_the_job_and_the_summary_counts_the_results(self):
        codes = {"a.zip": 0, "b.zip": 0, "c.zip": 1}
        with mock.patch.object(app_module.runner, "run_streaming", self.fake_streaming(codes, hold="b.zip")):
            self.app._run_jobs(self.jobs("a.zip", "b.zip", "c.zip"))
            self.pump(lambda: "2 of 3: b.zip" in self.app.status.full)
            self.assertEqual(str(self.app.progress.cget("mode")), "indeterminate")  # busy indicator
            self.assertTrue(self.app._running)
            self.release.set()
            self.pump(lambda: not self.app._running)
        self.assertEqual(self.app.status.full, "2 extracted, 1 failed")
        self.assertEqual(self.app.status.level, "warning")
        self.assertEqual(str(self.app.progress.cget("mode")), "determinate")
        self.assertEqual(float(self.app.progress.cget("value")), 0.0)

    def test_a_single_run_names_the_file_in_both_phases(self):
        codes = {"only.zip": 0}
        with mock.patch.object(app_module.runner, "run_streaming", self.fake_streaming(codes, hold="only.zip")):
            self.app._run_jobs(self.jobs("only.zip"))
            self.assertEqual(self.app.status.full, "Extracting only.zip")
            self.release.set()
            self.pump(lambda: not self.app._running)
        self.assertEqual(self.app.status.full, "Extracted: only.zip")
        self.assertEqual(self.app.status.level, "info")

    def test_a_failed_single_run_is_an_error(self):
        with mock.patch.object(app_module.runner, "run_streaming", self.fake_streaming({"bad.zip": 2})):
            self.app._run_jobs(self.jobs("bad.zip"))
            self.pump(lambda: not self.app._running)
        self.assertEqual(self.app.status.full, "Failed: bad.zip (exit code 2)")
        self.assertEqual(self.app.status.level, "error")

    def test_cancelling_reports_what_was_done_and_what_was_not(self):
        codes = {"a.zip": 0, "b.zip": 0, "c.zip": 0}
        with mock.patch.object(app_module.runner, "run_streaming", self.fake_streaming(codes, hold="b.zip")):
            self.app._run_jobs(self.jobs("a.zip", "b.zip", "c.zip"))
            self.pump(lambda: "2 of 3: b.zip" in self.app.status.full)
            self.app._on_cancel()
            self.assertEqual(self.app.status.full, "Cancelling...")
            self.pump(lambda: not self.app._running)
        self.assertEqual(self.app.status.full, "Cancelled: 1 extracted, 2 not run")

    def test_a_job_that_cannot_even_build_its_command_counts_as_failed(self):
        with mock.patch.object(app_module.runner, "build_command", side_effect=ValueError("bad option")):
            self.app._run_jobs(self.jobs("a.zip"))
            self.pump(lambda: not self.app._running)
        self.assertEqual(self.app.status.level, "error")
        self.assertIn("bad option", self.app.log.get("1.0", "end"))

    def test_the_worker_never_updates_a_widget_from_its_own_thread(self):
        # Status and log are fed through the queues and applied by _drain_log, on the main thread.
        threads = []
        real_status, real_append = self.app.status.set, self.app.log_pane.append

        def status_set(*args, **kwargs):
            threads.append(threading.current_thread())
            return real_status(*args, **kwargs)

        def log_append(*args, **kwargs):
            threads.append(threading.current_thread())
            return real_append(*args, **kwargs)

        codes = {"a.zip": 0, "b.zip": 0}
        with mock.patch.object(self.app.status, "set", status_set), \
                mock.patch.object(self.app.log_pane, "append", log_append), \
                mock.patch.object(app_module.runner, "run_streaming", self.fake_streaming(codes)):
            self.app._run_jobs(self.jobs("a.zip", "b.zip"))
            self.pump(lambda: not self.app._running)
        self.assertTrue(threads)
        self.assertEqual({thread for thread in threads}, {threading.main_thread()})
        self.assertEqual(self.app.status.full, "2 extracted")

    def test_queueing_a_file_says_how_many_wait(self):
        self.app.source.set(os.path.join(self.tmp, "q.zip"))
        self.app._on_batch()
        self.assertIn("Queued q.zip: 1 waiting", self.app.status.full)

    def test_a_copy_that_fails_turns_the_status_red(self):
        self.app._append("alpha")
        with mock.patch.object(self.root, "clipboard_clear", side_effect=tk.TclError("locked")), \
                self.assertLogs(level="WARNING"):
            self.app._copy_log_all()
        self.assertEqual(self.app.status.level, "error")


class CallbackErrorTest(AppTestCase):
    def test_a_failing_callback_is_logged_and_shown_not_lost(self):
        # In the windowed exe Tk's default report goes to a stderr that does not exist.
        self.root.after(0, lambda: 1 / 0)
        with self.assertLogs(level="ERROR") as logs:
            self.root.update()
        self.assertIn("ZeroDivisionError", "\n".join(logs.output))
        self.assertEqual(self.app.status.level, "error")
        self.assertIn("ZeroDivisionError", self.app.status.full)
        self.assertIn("[error] internal error: ZeroDivisionError", self.app.log.get("1.0", "end"))

    def test_the_log_file_is_named_when_there_is_one(self):
        with mock.patch.object(app_module.logging_setup, "log_path", return_value="X:/gui.log"), \
                self.assertLogs(level="ERROR"):
            self.app._report_callback_exception(ValueError, ValueError("boom"), None)
        self.assertIn("(details in X:/gui.log)", self.app.log.get("1.0", "end"))

    def test_the_hook_never_raises_even_with_the_window_gone(self):
        self.app.log_pane.frame.destroy()
        with self.assertLogs(level="ERROR"):
            self.app._report_callback_exception(ValueError, ValueError("boom"), None)


class RunLockTest(AppTestCase):
    """While a run is active the risky menu entries and their shortcuts are off."""

    def setUp(self):
        super().setUp()
        patch = mock.patch.object(tk.Misc, "focus_force")
        patch.start()
        self.addCleanup(patch.stop)

    def edit_menu_entries(self):
        bar = self.app.menubar
        index = bar._titles.index("Edit")
        bar._open(bar._buttons[index][0], "Edit")
        entries = {row.widgets[1].cget("text"): row.enabled for row in bar._popup.rows.rows}
        bar.close()
        return entries

    def test_risky_entries_are_disabled_during_a_run_and_back_after(self):
        before = self.edit_menu_entries()
        self.assertTrue(all(before.values()))
        self.app._set_running(True)
        during = self.edit_menu_entries()
        for name in ("Run options...", "Preferences...", "Add to Explorer menu", "Remove from Explorer menu"):
            self.assertFalse(during[name], name)
        self.assertTrue(during["Toggle dark mode"])
        self.app._set_running(False)
        self.assertEqual(self.edit_menu_entries(), before)

    def test_their_shortcuts_are_ignored_during_a_run(self):
        with mock.patch.object(self.app, "_open_preferences") as prefs, \
                mock.patch.object(self.app, "_open_run_options") as options, \
                mock.patch.object(self.app, "_toggle_theme") as toggle:
            self.app._set_running(True)
            for method in ("_open_preferences", "_open_run_options", "_toggle_theme"):
                self.app._shortcut(method)
            prefs.assert_not_called()
            options.assert_not_called()
            toggle.assert_called_once()  # not a risky one
            self.app._set_running(False)
            self.app._shortcut("_open_preferences")
            prefs.assert_called_once()

    def test_the_bound_shortcut_goes_through_the_guard(self):
        self.app._set_running(True)
        with mock.patch.object(self.app, "_open_preferences") as prefs:
            self.root.event_generate("<Control-comma>")
        prefs.assert_not_called()
        self.app._set_running(False)

    def test_f10_is_bound_for_the_menu_bar(self):
        self.assertIn("<Key-F10>", self.root.bind())


class StatusLayoutTest(AppTestCase):
    def test_the_bar_and_the_line_sit_under_the_log_and_start_idle(self):
        self.assertEqual(self.app.status.full, "Ready")
        self.assertEqual(str(self.app.progress.cget("mode")), "determinate")
        self.assertGreater(self.app.status.label.winfo_y(), -1)
        self.assertEqual(self.app.status.label.master, self.app.progress.master)


if __name__ == "__main__":
    unittest.main()
