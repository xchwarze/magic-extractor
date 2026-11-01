"""The main window's output surfaces: log pane, status line, error reporting (headless Tk)."""
import os
import sys
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
        with mock.patch.object(self.root, "clipboard_clear", side_effect=tk.TclError("locked")):
            self.app._copy_log_all()
        self.assertIn("could not copy", self.app.log.get("1.0", "end"))

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
        with mock.patch.object(app_module.filedialog, "asksaveasfilename", return_value=self.tmp):  # a folder
            self.app._save_log_as()
        self.assertIn("could not save", self.app.log.get("1.0", "end"))

    def test_clear_from_the_menu_empties_the_log(self):
        self.app._append("alpha")
        self.open_menu().activate(3)
        self.assertTrue(self.app.log_pane.is_empty)


if __name__ == "__main__":
    unittest.main()
