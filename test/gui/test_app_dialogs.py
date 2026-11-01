"""Themed modal dialogs: a safe default for Enter, one copy at a time, kept on screen.

No test here opens a blocking dialog: the confirm/message functions are patched by
AppTestCase, and the dialog classes are built (hidden) and driven through their handlers.
Windows will not give a test window keyboard focus, so keys are tested by calling the
installed <Return> handler, not with event_generate.
"""
import types
import unittest
from unittest import mock
from tkinter import ttk

from test_app import AppTestCase, app_module
from gui import config_io, dialogs, geometry


REAL_CONFIRM = dialogs.confirm  # AppTestCase patches dialogs.confirm; this is the real one


def event_on(widget):
    return types.SimpleNamespace(widget=widget)


def plain(button, _semantic):
    return button  # no icons needed to test behaviour


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
        window = dialogs.create_dialog(self.root, "T", "light")
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
        import tkinter as tk
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


class ConfirmDialogTest(AppTestCase):
    """B1/B4: the safe answer is what Enter and Escape give."""

    def make(self, **kwargs):
        return dialogs.ConfirmDialog(self.root, "light", plain, "Delete source files?", "Delete them?",
                                     kwargs.get("detail", ""), "Delete sources", "delete", "Keep sources")

    def test_enter_keeps_the_files(self):
        dialog = self.make()
        dialog.window.return_handler(event_on(dialog.window))
        self.assertFalse(dialog.confirmed)
        self.assertFalse(dialog.window.winfo_exists())

    def test_enter_on_the_delete_button_still_deletes(self):
        # Only when the user deliberately moved focus to it.
        dialog = self.make()
        dialog.window.return_handler(event_on(dialog.confirm_button))
        self.assertTrue(dialog.confirmed)

    def test_the_close_button_of_the_window_keeps_the_files(self):
        dialog = self.make()
        dialog.window.tk.call(dialog.window.protocol("WM_DELETE_WINDOW"))
        self.assertFalse(dialog.confirmed)
        self.assertFalse(dialog.window.winfo_exists())

    def test_escape_is_bound_and_the_safe_button_is_the_accent_one(self):
        dialog = self.make()
        self.assertTrue(dialog.window.bind("<Escape>"))
        self.assertEqual(str(dialog.cancel_button.cget("style")), dialogs.accent_style())
        self.assertNotEqual(str(dialog.confirm_button.cget("style")), "Accent.TButton")

    def test_the_safe_button_gets_the_initial_focus(self):
        with mock.patch.object(dialogs, "present") as present, \
                mock.patch.object(dialogs.DialogWindow, "wait_window"):
            REAL_CONFIRM(self.root, "light", plain, "T", "M", confirm_label="Go", confirm_icon="delete",
                         cancel_label="Keep")
        self.assertEqual(present.call_args.kwargs["initial_focus"].cget("text"), "Keep")


class ResolveDeleteTest(AppTestCase):
    def test_ask_mode_asks_and_follows_the_answer(self):
        self.app.opt_delete.set("ask")
        self.assertFalse(self.app._resolve_delete())  # the patched confirm answers "keep"
        app_module.dialogs.confirm.assert_called_once()
        app_module.dialogs.confirm.return_value = True
        self.assertTrue(self.app._resolve_delete())

    def test_keep_and_delete_modes_never_ask(self):
        self.app.opt_delete.set("keep")
        self.assertFalse(self.app._resolve_delete())
        self.app.opt_delete.set("delete")
        self.assertTrue(self.app._resolve_delete())
        app_module.dialogs.confirm.assert_not_called()


class ModalDialogsTest(AppTestCase):
    def grab(self):
        return str(self.root.tk.eval("grab current"))

    def test_run_options_is_modal(self):
        self.app._open_run_options()
        self.assertEqual(self.grab(), str(self.dialogs()[-1]))

    def test_a_shortcut_does_not_stack_a_second_dialog(self):
        self.app._open_run_options()
        self.app._open_run_options()
        self.app._open_preferences()
        self.app._about()
        self.assertEqual(len(self.dialogs()), 1)

    def test_closing_a_dialog_releases_the_grab_and_allows_the_next_one(self):
        self.app._open_run_options()
        dialogs.close_dialog(self.dialogs()[-1])
        self.assertEqual(self.grab(), "")
        self.app._about()
        self.assertEqual(len(self.dialogs()), 1)

    def test_closing_a_nested_dialog_hands_the_grab_back_to_its_parent(self):
        self.app._open_run_options()
        parent_dialog = self.dialogs()[-1]
        nested = dialogs.create_dialog(parent_dialog, "Nested", "light")
        ttk.Label(nested, text="x").pack()
        dialogs.present(nested, parent_dialog, "light")
        self.assertEqual(self.grab(), str(nested))
        dialogs.close_dialog(nested)
        self.assertEqual(self.grab(), str(parent_dialog))

    def test_a_dialog_opened_near_the_screen_corner_stays_inside_the_work_area(self):
        left, top, right, bottom = geometry.work_area(self.root, near=self.root)
        self.root.geometry(f"400x300+{right - 120}+{bottom - 100}")
        self.root.update_idletasks()
        self.app._open_preferences()
        win = self.dialogs()[-1]
        win.update_idletasks()
        position = win.geometry().split("+", 1)[1].split("+")
        x, y = int(position[0]), int(position[1])
        self.assertLessEqual(x + win.winfo_reqwidth(), right)
        self.assertLessEqual(y + win.winfo_reqheight(), bottom)
        self.assertGreaterEqual(x, left)
        self.assertGreaterEqual(y, top)


class ThemedMessagesTest(AppTestCase):
    def test_no_native_message_box_is_left_in_the_app(self):
        # The native boxes stay light in dark mode and cannot show our icons.
        self.assertFalse(hasattr(app_module, "messagebox"))

    def test_a_notice_is_a_themed_dialog_with_a_close_button_for_enter(self):
        dialog = dialogs.MessageDialog(self.root, "dark", plain, "Error", "Something failed")
        handler = dialog.window.return_handler
        handler(event_on(dialog.window))
        self.assertFalse(dialog.window.winfo_exists())


if __name__ == "__main__":
    unittest.main()
