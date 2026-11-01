import os
import sys
import tkinter as tk
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))
from gui.autoscroll import AutoScrollbar  # noqa: E402
from gui.log_pane import LogPane, is_editing_key  # noqa: E402

SHIFT, CONTROL, ALT = 0x1, 0x4, 0x20000


class EditingKeyTest(unittest.TestCase):
    def test_typing_and_deleting_are_blocked(self):
        for keysym, char in (("a", "a"), ("space", " "), ("BackSpace", "\b"), ("Delete", "\x7f"),
                             ("Return", "\r"), ("KP_Enter", "\r"), ("eacute", "é")):
            self.assertTrue(is_editing_key(0, keysym, char), keysym)

    def test_navigation_and_selection_keys_are_allowed(self):
        for state, keysym in ((0, "Left"), (0, "Right"), (0, "Up"), (0, "Home"), (0, "End"),
                              (0, "Prior"), (0, "Next"), (SHIFT, "Right"), (SHIFT, "End"),
                              (CONTROL, "Home"), (CONTROL, "End"), (CONTROL, "a"), (CONTROL, "c"),
                              (CONTROL, "Insert"), (0, "Insert"), (0, "F10"), (SHIFT, "F10"),
                              (0, "Escape")):
            self.assertFalse(is_editing_key(state, keysym, ""), (state, keysym))

    def test_control_shortcuts_that_edit_are_blocked(self):
        for letter in "vxzyhdkot":
            self.assertTrue(is_editing_key(CONTROL, letter, ""), letter)
        self.assertTrue(is_editing_key(CONTROL, "Return", ""))
        self.assertTrue(is_editing_key(SHIFT, "Insert", ""))   # paste
        self.assertTrue(is_editing_key(SHIFT, "Delete", ""))   # cut

    def test_alt_accelerators_are_left_alone(self):
        self.assertFalse(is_editing_key(ALT, "f", "f"))


class TkTestCase(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"no display for Tk: {exc}")
        self.root.withdraw()
        self.addCleanup(self.root.destroy)


class LogPaneTest(TkTestCase):
    def pane(self, **kwargs):
        pane = LogPane(self.root, "Nothing yet", "dark", **kwargs)
        pane.frame.pack()
        return pane

    def test_starts_with_the_placeholder_which_is_not_output(self):
        pane = self.pane()
        self.assertTrue(pane.is_empty)
        self.assertIn("Nothing yet", pane.text.get("1.0", "end"))
        self.assertEqual(pane.get_all(), "")

    def test_selecting_the_placeholder_copies_nothing(self):
        pane = self.pane()
        pane.text.tag_add("sel", "1.0", "end-1c")
        self.assertEqual(pane.selected_text(), "")

    def test_selected_text_and_get_all_return_the_output(self):
        pane = self.pane()
        pane.append("alpha")
        pane.append("beta")
        self.assertEqual(pane.get_all(), "alpha\nbeta\n")
        pane.text.tag_add("sel", "2.0", "2.4")
        self.assertEqual(pane.selected_text(), "beta")

    def test_oldest_lines_are_dropped_beyond_the_limit(self):
        pane = self.pane(max_lines=10)
        pane.append("\n".join(str(i) for i in range(25)))
        lines = pane.get_all().splitlines()
        self.assertEqual(lines, [str(i) for i in range(15, 25)])

    def test_clear_returns_to_the_placeholder_and_cancels_a_pending_scroll(self):
        pane = self.pane()
        pane.append("x")
        pane.clear()
        self.assertTrue(pane.is_empty)
        self.assertIsNone(pane._scroll_job)
        self.assertEqual(pane.get_all(), "")

    def test_a_pane_destroyed_before_the_idle_scroll_does_not_raise(self):
        pane = self.pane()
        pane.append("x")
        pane.frame.destroy()
        self.root.update_idletasks()  # the queued scroll runs against a dead widget

    def test_restyle_gives_the_selection_a_readable_inactive_colour(self):
        pane = self.pane()
        pane.restyle("light")
        self.assertEqual(str(pane.text.cget("bg")), "#ffffff")
        self.assertEqual(str(pane.text.cget("inactiveselectbackground")), "#d6d6d6")


class AutoScrollbarTest(TkTestCase):
    def test_hidden_when_everything_fits_and_back_when_it_overflows(self):
        frame = tk.Frame(self.root)
        frame.pack()
        bar = AutoScrollbar(frame)
        bar.grid(row=0, column=1)
        bar.set(0.0, 1.0)
        self.assertEqual(bar.grid_info(), {})
        bar.set(0.0, 0.4)
        self.assertEqual(bar.grid_info()["column"], 1)
        bar.set(0.0, 1.0)
        self.assertEqual(bar.grid_info(), {})


if __name__ == "__main__":
    unittest.main()
