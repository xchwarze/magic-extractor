import os
import sys
import time
import tkinter as tk
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))
from gui import tooltip  # noqa: E402
from gui.tooltip import Tooltip  # noqa: E402


class TooltipTestCase(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"no display for Tk: {exc}")
        # A tooltip retires itself once its widget is not on screen, so the window must be
        # mapped; borderless windows are not activated, so the developer's focus is left alone.
        self.root.overrideredirect(True)
        self.root.geometry("160x60+5+5")
        self.root.update()
        self.addCleanup(self.root.destroy)
        self.addCleanup(setattr, Tooltip, "_active", None)
        self.button = tk.Button(self.root, text="x")
        self.button.pack()
        self.tip = Tooltip(self.button, "Helpful words", delay=10)
        self.root.update()

    def popups(self, widget=None):
        return [w for w in (widget or self.button).winfo_children() if isinstance(w, tk.Toplevel)]


class ShowHideTest(TooltipTestCase):
    def test_show_opens_a_borderless_topmost_popup_with_the_text(self):
        self.tip.show(100, 100)
        popup = self.popups()[0]
        self.assertTrue(self.tip.visible)
        self.assertTrue(popup.wm_overrideredirect())
        self.assertTrue(popup.attributes("-topmost"))
        label = popup.winfo_children()[0]
        self.assertEqual(label.cget("text"), "Helpful words")

    def test_hide_removes_it(self):
        self.tip.show(100, 100)
        self.tip.hide()
        self.assertFalse(self.tip.visible)
        self.assertEqual(self.popups(), [])

    def test_an_empty_text_shows_nothing(self):
        self.tip.text = ""
        self.tip.show(100, 100)
        self.assertEqual(self.popups(), [])
        self.assertFalse(self.tip.visible)

    def test_only_one_tooltip_is_on_screen(self):
        second = tk.Button(self.root, text="y")
        second.pack()
        self.root.update()
        other = Tooltip(second, "Other", delay=10)
        self.tip.show(100, 100)
        other.show(120, 120)
        self.assertFalse(self.tip.visible)
        self.assertTrue(other.visible)
        self.assertEqual(self.popups(), [])
        self.assertEqual(len(self.popups(second)), 1)

    def test_it_is_kept_inside_the_work_area(self):
        with mock.patch.object(tooltip, "work_area", return_value=(0, 0, 400, 300)):
            self.tip.show(395, 295)
        popup = self.popups()[0]
        self.root.update_idletasks()
        self.assertLessEqual(popup.winfo_x() + popup.winfo_reqwidth(), 400)
        self.assertLessEqual(popup.winfo_y() + popup.winfo_reqheight(), 300)

    def test_near_the_bottom_it_flips_above_the_anchor(self):
        with mock.patch.object(tooltip, "work_area", return_value=(0, 0, 1000, 300)):
            self.tip.show(100, 290, above=250)
        popup = self.popups()[0]
        self.root.update_idletasks()
        self.assertLessEqual(popup.winfo_y() + popup.winfo_reqheight(), 250 + 1)

    def test_the_popup_is_themed(self):
        self.tip.show(100, 100)
        label = self.popups()[0].winfo_children()[0]
        self.assertEqual(str(label.cget("background")), "#ffffff")  # light palette (no sv-ttk theme applied)
        self.assertEqual(str(label.cget("foreground")), "#000000")


class TriggerTest(TooltipTestCase):
    def test_hover_shows_it_after_the_delay_and_leaving_hides_it(self):
        self.button.event_generate("<Enter>", x=1, y=1, rootx=50, rooty=50)
        self.assertIsNotNone(self.tip._job)
        deadline = time.monotonic() + 2
        while not self.tip.visible and time.monotonic() < deadline:
            self.root.update()
            time.sleep(0.01)
        self.assertTrue(self.tip.visible)
        self.button.event_generate("<Leave>")
        self.assertFalse(self.tip.visible)

    def test_leaving_before_the_delay_cancels_it(self):
        self.button.event_generate("<Enter>", x=1, y=1)
        self.button.event_generate("<Leave>")
        self.assertIsNone(self.tip._job)

    def test_keyboard_focus_after_a_key_press_schedules_it(self):
        Tooltip._key_at = time.monotonic()
        self.tip._on_focus(None)
        self.assertIsNotNone(self.tip._job)

    def test_programmatic_focus_without_a_key_press_does_not(self):
        Tooltip._key_at = float("-inf")
        self.tip._on_focus(None)
        self.assertIsNone(self.tip._job)

    def test_focus_right_after_a_click_is_not_keyboard_navigation(self):
        Tooltip._key_at = time.monotonic()
        self.tip._clicked_at = time.monotonic()
        self.tip._on_focus(None)
        self.assertIsNone(self.tip._job)

    def test_a_click_hides_it(self):
        self.tip.show(100, 100)
        self.button.event_generate("<ButtonPress-1>")
        self.assertFalse(self.tip.visible)

    def test_destroying_the_widget_with_a_tip_up_leaves_no_popup(self):
        self.tip.show(100, 100)
        popup = self.tip.popup
        self.button.destroy()
        self.assertFalse(self.tip.visible)
        self.assertFalse(popup.winfo_exists())

    def test_a_widget_that_is_not_on_screen_retires_its_tip(self):
        self.tip.show(100, 100)
        self.root.withdraw()  # the window goes away without any event reaching the button
        self.tip._watch()
        self.assertFalse(self.tip.visible)


if __name__ == "__main__":
    unittest.main()
