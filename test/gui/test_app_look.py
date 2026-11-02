"""The log blends into the window: no border unless it has the keyboard focus, and no
idle progress bar drawing a second separator line under it."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_app import AppTestCase  # noqa: E402
from gui import theme  # noqa: E402


class LogBlendsInTest(AppTestCase):
    def test_log_never_draws_a_border_even_with_focus(self):
        # By design the log is blended into the window: no frame, not even a focus ring.
        log = self.app.log
        for mode in ("dark", "light"):
            self.app.log_pane.restyle(mode)
            self.assertEqual(int(log.cget("highlightthickness")), 0, mode)
            self.assertEqual(int(log.cget("borderwidth")), 0, mode)

    def test_other_text_widgets_follow_the_same_rule(self):
        import tkinter as tk
        text = tk.Text(self.root)
        theme.restyle_text(text, "dark")
        self.assertEqual(str(text.cget("highlightbackground")), str(text.cget("background")))


class IdleProgressBarTest(AppTestCase):
    def test_progress_bar_shows_only_during_a_run(self):
        self.assertEqual(self.app.progress.winfo_manager(), "")
        self.app._set_running(True)
        self.assertEqual(self.app.progress.winfo_manager(), "pack")
        self.app._set_running(False)
        self.assertEqual(self.app.progress.winfo_manager(), "")


if __name__ == "__main__":
    unittest.main()
