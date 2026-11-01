import os
import sys
import tkinter as tk
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))
from gui import menu_popup, workarea  # noqa: E402
from gui.menu_popup import Item, RowList, show_context_menu  # noqa: E402


class PopupTestCase(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"no display for Tk: {exc}")
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        # A test must not steal keyboard focus from whatever the developer is typing in.
        patch = mock.patch.object(tk.Misc, "focus_force")
        patch.start()
        self.addCleanup(patch.stop)

    def rows(self, items, icon=None, invoke=None):
        # Mouse events are only delivered to mapped widgets: show the rows in a borderless
        # window (it is not activated, so it takes no focus from the developer).
        window = tk.Toplevel(self.root)
        window.overrideredirect(True)
        window.geometry("+10+10")
        rows = RowList(tk.Frame(window), "dark", icon=icon, invoke=invoke)
        rows.inner.pack()
        rows.populate(items)
        window.update()
        return rows


class RowListTest(PopupTestCase):
    def test_keyboard_moves_over_enabled_rows_only_and_wraps(self):
        rows = self.rows([Item("a", print), Item("b", print, enabled=False), None, Item("c", print)])
        rows.move(1)
        self.assertEqual(rows.index, 0)
        rows.move(1)
        self.assertEqual(rows.index, 2)   # skipped the disabled row and the separator
        rows.move(1)
        self.assertEqual(rows.index, 0)   # wrapped
        rows.move(-1)
        self.assertEqual(rows.index, 2)

    def test_home_and_end_jump_to_the_first_and_last_enabled_row(self):
        rows = self.rows([Item("a", print, enabled=False), Item("b", print), Item("c", print),
                          Item("d", print, enabled=False)])
        rows.move(1, start=0)
        self.assertEqual(rows.index, 1)
        rows.move(-1, start=-1)
        self.assertEqual(rows.index, 2)

    def test_a_menu_with_nothing_enabled_has_nothing_to_highlight(self):
        rows = self.rows([Item("a", print, enabled=False)])
        rows.move(1)
        self.assertIsNone(rows.index)

    def test_a_disabled_row_never_runs(self):
        ran = []
        rows = self.rows([Item("off", lambda: ran.append("off"), enabled=False)])
        rows.activate(0)
        rows.rows[0].widgets[1].event_generate("<Button-1>")
        self.assertEqual(ran, [])

    def test_clicking_or_pressing_enter_runs_the_row_through_invoke(self):
        ran = []
        rows = self.rows([Item("a", lambda: ran.append("a")), Item("b", lambda: ran.append("b"))],
                         invoke=lambda command: (ran.append("invoke"), command()))
        rows.rows[1].widgets[1].event_generate("<Button-1>")
        rows.move(1, start=0)
        rows.activate()
        self.assertEqual(ran, ["invoke", "b", "invoke", "a"])

    def test_activate_without_a_highlight_does_nothing(self):
        ran = []
        rows = self.rows([Item("a", lambda: ran.append("a"))])
        rows.activate()
        self.assertEqual(ran, [])

    def test_hover_highlights_an_enabled_row_but_not_a_disabled_one(self):
        rows = self.rows([Item("a", print), Item("b", print, enabled=False)])
        rows.rows[0].widgets[1].event_generate("<Enter>")
        self.assertEqual(rows.index, 0)
        rows.rows[1].widgets[1].event_generate("<Enter>")
        self.assertEqual(rows.index, 0)  # unchanged: the disabled row is not a target

    def test_disabled_rows_are_dimmed_and_shortcuts_are_split_off(self):
        rows = self.rows([Item("Open\tCtrl+O", print), Item("Off\tCtrl+X", print, enabled=False)])
        on, off = rows.rows
        self.assertEqual(on.widgets[1].cget("text"), "Open")
        self.assertEqual(on.widgets[2].cget("text"), "Ctrl+O")
        self.assertEqual(str(off.widgets[1].cget("fg")), rows.colors["disabled"])
        self.assertEqual(str(off.widgets[2].cget("fg")), rows.colors["disabled"])
        self.assertEqual(str(on.widgets[1].cget("fg")), rows.colors["fg"])

    def test_icons_use_the_disabled_variant_and_icon_less_rows_stay_aligned(self):
        requested = []

        def icon(semantic, mode, disabled):
            requested.append((semantic, disabled))
            return tk.PhotoImage(master=self.root, width=24, height=16)

        rows = self.rows([Item("a", print, "copy"), Item("b", print, "copy", enabled=False),
                          Item("c", print)], icon=icon)
        self.assertIn(("copy", False), requested)
        self.assertIn(("copy", True), requested)  # the disabled row asked for the disabled tint
        widths = [int(self.root.tk.call("image", "width", row.widgets[1].cget("image"))) for row in rows.rows]
        self.assertEqual(widths, [24, 24, 24])  # the icon-less row got a blank of the same width

    def test_without_an_icon_provider_rows_are_text_only(self):
        rows = self.rows([Item("a", print, "copy")])
        self.assertEqual(str(rows.rows[0].widgets[1].cget("image")), "")


class ShowContextMenuTest(PopupTestCase):
    def test_running_a_row_closes_the_popup_and_runs_the_command_once(self):
        ran = []
        popup = show_context_menu(self.root, "dark", 100, 100, [Item("go", lambda: ran.append(1))])
        popup.rows.activate(0)
        self.assertEqual(ran, [1])
        self.assertFalse(popup.winfo_exists())

    def test_it_is_keyboard_navigable_and_closes_on_escape_and_focus_loss(self):
        popup = show_context_menu(self.root, "dark", 100, 100, [Item("go", print)])
        bound = popup.bind()
        for sequence in ("<Key-Down>", "<Key-Up>", "<Key-Home>", "<Key-End>", "<Key-Return>", "<Key-space>", "<Key-Escape>", "<FocusOut>"):
            self.assertIn(sequence, bound)
        popup.destroy()

    def test_it_is_a_borderless_topmost_window(self):
        popup = show_context_menu(self.root, "dark", 100, 100, [Item("go", print)])
        self.assertTrue(popup.wm_overrideredirect())
        self.assertTrue(popup.attributes("-topmost"))
        popup.destroy()

    def test_it_is_kept_inside_the_work_area(self):
        with mock.patch.object(menu_popup, "work_area", return_value=(0, 0, 300, 200)):
            popup = show_context_menu(self.root, "dark", 290, 190, [Item("a long row of text", print)])
        self.root.update_idletasks()
        self.assertGreaterEqual(popup.winfo_x(), 0)
        self.assertLessEqual(popup.winfo_x() + popup.winfo_reqwidth(), 300)
        self.assertLessEqual(popup.winfo_y() + popup.winfo_reqheight(), 200)
        popup.destroy()

    def test_a_monitor_left_of_the_primary_one_has_negative_coordinates(self):
        with mock.patch.object(menu_popup, "work_area", return_value=(-1920, 0, 0, 1080)):
            popup = show_context_menu(self.root, "dark", -5, 10, [Item("a long row of text", print)])
        self.root.update_idletasks()
        self.assertLessEqual(popup.winfo_x() + popup.winfo_reqwidth(), 0)
        self.assertGreaterEqual(popup.winfo_x(), -1920)
        popup.destroy()


class KeyboardAnchorTest(PopupTestCase):
    def test_anchor_is_under_the_caret_or_near_the_top_left(self):
        text = tk.Text(self.root)
        text.pack()
        x, y = menu_popup.keyboard_anchor(text)
        self.assertIsInstance(x, int)
        self.assertIsInstance(y, int)
        with mock.patch.object(text, "bbox", return_value=None):
            fx, fy = menu_popup.keyboard_anchor(text)
        self.assertEqual((fx, fy), (text.winfo_rootx() + workarea.scaled(text, 8),
                                    text.winfo_rooty() + workarea.scaled(text, 8)))


class WorkAreaTest(unittest.TestCase):
    def test_clamp_keeps_a_box_inside_and_top_left_wins_when_too_big(self):
        area = (0, 0, 800, 600)
        self.assertEqual(workarea.clamp_into(790, 590, 100, 50, area), (700, 550))
        self.assertEqual(workarea.clamp_into(-20, -5, 100, 50, area), (0, 0))
        self.assertEqual(workarea.clamp_into(10, 10, 900, 700, area), (0, 0))
        self.assertEqual(workarea.clamp_into(-1900, 5, 100, 50, (-1920, 0, 0, 1080)), (-1900, 5))


if __name__ == "__main__":
    unittest.main()
