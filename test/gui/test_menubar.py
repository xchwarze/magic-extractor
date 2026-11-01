import os
import sys
import time
import tkinter as tk
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))
from gui import menu_popup  # noqa: E402
from gui.menubar import MenuBar  # noqa: E402


class MenuBarTestCase(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"no display for Tk: {exc}")
        self.root.geometry("500x100+20+20")
        # A test must not steal keyboard focus from whatever the developer is typing in.
        patch = mock.patch.object(tk.Misc, "focus_force")
        patch.start()
        self.addCleanup(patch.stop)
        self.addCleanup(self.root.destroy)
        self.ran = []
        self.bar = MenuBar(self.root, "dark")
        self.bar.pack(fill="x")
        self.bar.add_menu("File", [("Open...\tCtrl+O", self.record("open")), None, ("Exit", self.record("exit"))])
        self.bar.add_menu("Edit", [("Preferences...", self.record("prefs")), ("Theme", self.record("theme"))])
        self.root.update()

    def record(self, name):
        return lambda: self.ran.append(name)

    def label(self, index):
        return self.bar._buttons[index][0]

    def open(self, index, keyboard=False):
        self.bar._on_button(self.label(index), self.bar._titles[index], keyboard=keyboard)
        return self.bar._popup

    def row_texts(self, popup):
        return [(row.widgets[1].cget("text"), row.enabled) for row in popup.rows.rows]


class DropdownTest(MenuBarTestCase):
    def test_a_click_opens_the_dropdown_and_a_second_click_closes_it(self):
        popup = self.open(0)
        self.assertIsNotNone(popup)
        self.assertEqual(self.row_texts(popup), [("Open...", True), ("Exit", True)])
        self.open(0)
        self.assertIsNone(self.bar._popup)

    def test_the_click_that_closed_a_menu_does_not_reopen_it(self):
        self.open(0)
        self.bar.close()  # what the popup's <FocusOut> does when the label is clicked
        self.open(0)
        self.assertIsNone(self.bar._popup)
        time.sleep(0.02)
        self.root.update()  # the suppression ends on the next event-loop turn
        self.open(0)
        self.assertIsNotNone(self.bar._popup)

    def test_opening_another_menu_closes_the_first(self):
        first = self.open(0)
        second = self.open(1)
        self.assertFalse(first.winfo_exists())
        self.assertTrue(second.winfo_exists())

    def test_the_shortcut_is_a_separate_dimmed_column(self):
        popup = self.open(0)
        self.assertEqual(popup.rows.rows[0].widgets[2].cget("text"), "Ctrl+O")

    def test_running_an_entry_closes_the_dropdown_first(self):
        popup = self.open(0)
        popup.rows.activate(1)
        self.assertEqual(self.ran, ["exit"])
        self.assertIsNone(self.bar._popup)


class KeyboardTest(MenuBarTestCase):
    def test_f10_focuses_the_first_label_and_remembers_where_it_came_from(self):
        with mock.patch.object(self.label(0), "focus_set") as focus:
            result = self.bar._on_f10(None)
        self.assertEqual(result, "break")
        focus.assert_called_once()

    def test_escape_on_the_bar_hands_the_focus_back(self):
        target = tk.Entry(self.root)
        target.pack()
        self.bar._return_focus = target
        with mock.patch.object(target, "focus_set") as focus:
            self.bar._leave_bar()
        focus.assert_called_once()
        self.assertIsNone(self.bar._return_focus)

    def test_left_and_right_move_between_labels_and_wrap(self):
        with mock.patch.object(self.bar, "focus_get", return_value=self.label(1)), \
                mock.patch.object(self.label(0), "focus_set") as first:
            self.bar._focus_relative(1)  # past the last one: wraps to the first
        first.assert_called_once()

    def test_opening_with_the_keyboard_highlights_the_first_enabled_row(self):
        self.bar.set_entry_state(["Preferences..."], "disabled")
        popup = self.open(1, keyboard=True)
        self.assertEqual(popup.rows.index, 1)  # the disabled first row is skipped

    def test_a_mouse_open_highlights_nothing_yet(self):
        self.assertIsNone(self.open(0).rows.index)

    def test_left_and_right_inside_a_dropdown_open_the_neighbouring_menu(self):
        self.open(0)
        self.bar._step_open_menu(1)
        self.assertIs(self.bar._popup_owner, self.label(1))
        self.assertEqual(self.bar._popup.rows.index, 0)
        self.bar._step_open_menu(1)  # wraps back to File
        self.assertIs(self.bar._popup_owner, self.label(0))

    def test_the_labels_are_not_in_the_tab_order_but_show_a_focus_ring(self):
        for index in (0, 1):
            self.assertEqual(str(self.label(index).cget("takefocus")), "0")
            self.assertEqual(int(self.label(index).cget("highlightthickness")), 1)

    def test_the_dropdown_binds_the_menu_keys(self):
        bound = self.open(0).bind()
        for sequence in ("<Key-Down>", "<Key-Up>", "<Key-Home>", "<Key-End>", "<Key-Return>", "<Key-space>",
                         "<Key-Escape>", "<Key-Left>", "<Key-Right>", "<FocusOut>"):
            self.assertIn(sequence, bound)

    def test_f10_is_bound_on_the_window_and_unbound_with_the_bar(self):
        self.assertIn("<Key-F10>", self.root.bind())
        self.bar.destroy()
        self.assertNotIn("<Key-F10>", self.root.bind())


class DisabledEntryTest(MenuBarTestCase):
    def test_a_disabled_entry_is_dimmed_and_does_not_run(self):
        self.bar.set_entry_state(["Preferences..."], "disabled")
        popup = self.open(1)
        self.assertEqual(self.row_texts(popup), [("Preferences...", False), ("Theme", True)])
        popup.rows.activate(0)
        popup.rows.rows[0].widgets[1].event_generate("<Button-1>")
        self.assertEqual(self.ran, [])
        popup.rows.activate(1)
        self.assertEqual(self.ran, ["theme"])

    def test_entries_are_matched_by_text_without_the_shortcut(self):
        self.bar.set_entry_state(["Open..."], "disabled")
        self.assertEqual(self.row_texts(self.open(0))[0], ("Open...", False))

    def test_enabling_again_restores_the_entry(self):
        self.bar.set_entry_state(["Preferences..."], "disabled")
        self.bar.set_entry_state(["Preferences..."], "normal")
        self.assertEqual(self.row_texts(self.open(1))[0], ("Preferences...", True))

    def test_changing_state_closes_an_open_dropdown(self):
        self.open(1)
        self.bar.set_entry_state(["Preferences..."], "disabled")
        self.assertIsNone(self.bar._popup)


class OnScreenAndThemeTest(MenuBarTestCase):
    def test_the_dropdown_is_kept_inside_the_work_area(self):
        # a label near the right edge of a small screen: the dropdown must slide left
        with mock.patch.object(menu_popup, "work_area", return_value=(0, 0, self.label(1).winfo_rootx() + 30, 700)):
            popup = self.open(1)
        self.root.update_idletasks()
        self.assertLess(popup.winfo_x(), self.label(1).winfo_rootx())
        self.assertLessEqual(popup.winfo_x() + popup.winfo_reqwidth(), self.label(1).winfo_rootx() + 30)

    def test_a_theme_change_recolors_the_labels_and_rebuilds_the_open_dropdown(self):
        popup = self.open(0)
        dark_row = popup.rows.rows[0].widgets[1].cget("bg")
        self.bar.recolor("light")
        self.assertEqual(str(self.label(0).cget("bg")), "#ffffff")
        rebuilt = self.bar._popup
        self.assertIsNotNone(rebuilt)
        self.assertIsNot(rebuilt, popup)
        self.assertFalse(popup.winfo_exists())
        self.assertNotEqual(str(rebuilt.rows.rows[0].widgets[1].cget("bg")), str(dark_row))


if __name__ == "__main__":
    unittest.main()
