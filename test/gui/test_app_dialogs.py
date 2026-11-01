"""Dialog behaviour: Enter presses the focused button, not the default one.

Windows will not give a test window keyboard focus, so keys are tested by calling the
installed <Return> handler, not with event_generate.
"""
import tkinter as tk
import types
import unittest
from tkinter import ttk
from unittest import mock

from test_app import AppTestCase
from gui import config_io, dialogs


def event_on(widget):
    return types.SimpleNamespace(widget=widget)


class FindButtons:
    def button(self, widget, text):
        for child in widget.winfo_children():
            if child.winfo_class() == "TButton" and child.cget("text") == text:
                return child
            found = self.button(child, text)
            if found is not None:
                return found
        return None


class EnterKeyTest(AppTestCase):
    """B2: Enter presses the focused button; only elsewhere does it run the default."""

    def make_window(self):
        window = tk.Toplevel(self.root)
        window.withdraw()
        calls = []
        default = ttk.Button(window, command=lambda: calls.append("default"))
        other = ttk.Button(window, command=lambda: calls.append("other"))
        entry = ttk.Entry(window)
        handler = dialogs.bind_default(window, default.invoke)
        return window, calls, handler, other, entry

    def test_enter_on_another_button_presses_that_button_not_the_default(self):
        _window, calls, handler, other, _entry = self.make_window()
        self.assertEqual(handler(event_on(other)), "break")
        self.assertEqual(calls, ["other"])

    def test_enter_in_a_field_runs_the_default(self):
        _window, calls, handler, _other, entry = self.make_window()
        handler(event_on(entry))
        self.assertEqual(calls, ["default"])

    def test_enter_in_a_multi_line_text_is_left_for_a_new_line(self):
        window, calls, handler, _other, _entry = self.make_window()
        self.assertIsNone(handler(event_on(tk.Text(window))))
        self.assertEqual(calls, [])


class PreferencesEnterTest(AppTestCase, FindButtons):
    def open_preferences(self):
        self.app._open_preferences()
        return self.dialogs()[-1]

    def test_enter_on_cancel_cancels_instead_of_saving(self):
        win = self.open_preferences()
        with mock.patch.object(config_io, "write_config") as write_config:
            win.return_handler(event_on(self.button(win, "Cancel")))
        write_config.assert_not_called()
        self.assertFalse(win.winfo_exists())

    def test_enter_with_focus_elsewhere_saves(self):
        win = self.open_preferences()
        with mock.patch.object(config_io, "write_config") as write_config:
            win.return_handler(event_on(win))
        write_config.assert_called_once()
        self.assertFalse(win.winfo_exists())


if __name__ == "__main__":
    unittest.main()
