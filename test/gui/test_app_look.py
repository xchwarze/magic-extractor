"""The log blends into the window (no border), the progress bar is always shown and left
full after a run, and option caveats are tooltip icons, not inline alert boxes."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_app import AppTestCase  # noqa: E402
from gui import option_warnings, theme  # noqa: E402


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


class ProgressBarTest(AppTestCase):
    def test_the_bar_is_always_shown_empty_before_the_first_run(self):
        self.assertEqual(self.app.progress.winfo_manager(), "pack")
        self.assertEqual(float(self.app.progress.cget("value")), 0.0)

    def test_the_bar_moves_during_a_run_and_stays_full_after_it(self):
        self.app._set_running(True)
        self.assertEqual(str(self.app.progress.cget("mode")), "indeterminate")
        self.app._on_run_finished(all_ok=False)  # failed: the window stays open
        self.assertEqual(self.app.progress.winfo_manager(), "pack")
        self.assertEqual(str(self.app.progress.cget("mode")), "determinate")
        self.assertEqual(float(self.app.progress.cget("value")), float(self.app.progress.cget("maximum")))


class OptionTipTest(AppTestCase):
    """Option caveats are an info/warning icon with a tooltip, not an inline alert box
    (a non-resizable dialog cannot grow to fit wrapped alert text)."""

    def open_run_options(self):
        self.app._open_run_options()
        return [w for w in self.root.winfo_children() if w.winfo_class() == "Toplevel" and w.winfo_exists()][-1]

    def tips(self, widget):
        found = []
        for child in widget.winfo_children():
            if getattr(child, "option_key", None):
                found.append(child)
            found.extend(self.tips(child))
        return found

    def test_no_inline_alert_box_any_more(self):
        win = self.open_run_options()

        def labels(widget):
            for child in widget.winfo_children():
                if child.winfo_class() == "Label" and str(child.cget("text")).startswith("\u26a0"):
                    yield child
                yield from labels(child)
        self.app.opt_recursive.set(True)
        self.root.update_idletasks()
        self.assertEqual(list(labels(win)), [])

    def test_the_tip_icon_turns_into_a_warning_when_the_option_is_risky(self):
        win = self.open_run_options()
        tip = next(t for t in self.tips(win) if t.option_key == "recursive")
        self.app.opt_recursive.set(False)
        safe_image = str(tip.cget("image"))
        self.app.opt_recursive.set(True)
        self.assertNotEqual(str(tip.cget("image")), safe_image)
        self.assertEqual(tip.tooltip.text, option_warnings.OPTION_WARNINGS["recursive"][1])

    def test_tips_can_be_reached_with_the_keyboard(self):
        win = self.open_run_options()
        for tip in self.tips(win):
            self.assertTrue(str(tip.cget("takefocus")) in ("1", "True", "true"), tip.option_key)


if __name__ == "__main__":
    unittest.main()
