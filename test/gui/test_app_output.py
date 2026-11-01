"""The main window's output surfaces: log pane, status line, error reporting (headless Tk)."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_app import AppTestCase  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
