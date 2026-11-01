"""Safe window restore (B5): the saved geometry is only reused when it is safe.

The test root stays withdrawn, so its state is patched where a test needs a normal,
maximized or minimized window.
"""
import tkinter as tk
import unittest
from unittest import mock

from test_app import AppTestCase
from gui import geometry


def screen_of(root):
    return (root.winfo_vrootx(), root.winfo_vrooty(),
            root.winfo_vrootx() + root.winfo_vrootwidth(), root.winfo_vrooty() + root.winfo_vrootheight())


class SaveGeometryTest(AppTestCase):
    gui_ini = "[gui]\nkeep_open = True\n[window]\nremember_geometry = True\ngeometry = 720x520+100+80\n"

    def saved_geometry(self):
        return self.app.settings.get("window", "geometry")

    def test_a_normal_window_saves_where_it_is(self):
        with mock.patch.object(self.root, "state", return_value="normal"), \
                mock.patch.object(self.root, "geometry", return_value="800x600+40+30"):
            self.app._save_settings()
        self.assertEqual(self.saved_geometry(), "800x600+40+30")

    def test_a_maximized_window_keeps_the_previous_geometry(self):
        with mock.patch.object(self.root, "state", return_value="zoomed"), \
                mock.patch.object(self.root, "geometry", return_value="1920x1040+-8+-8"):
            self.app._save_settings()
        self.assertEqual(self.saved_geometry(), "720x520+100+80")

    def test_a_minimized_window_never_saves_its_parked_position(self):
        with mock.patch.object(self.root, "state", return_value="iconic"), \
                mock.patch.object(self.root, "geometry", return_value="460x360+-32000+-32000"):
            self.app._save_settings()
        self.assertEqual(self.saved_geometry(), "720x520+100+80")

    def test_it_is_not_saved_when_remembering_is_off(self):
        self.app.settings.set("window", "remember_geometry", "False")
        with mock.patch.object(self.root, "state", return_value="normal"), \
                mock.patch.object(self.root, "geometry", return_value="800x600+40+30"):
            self.app._save_settings()
        self.assertEqual(self.saved_geometry(), "720x520+100+80")


class RestoreGeometryTest(AppTestCase):
    """The saved geometry decides where the window opens."""

    def open_with(self, geometry_text):
        self.app.settings.set("window", "geometry", geometry_text)
        # A withdrawn window does not report a requested size back, so capture the request.
        with mock.patch.object(self.root, "geometry") as request:
            self.app._apply_window_prefs()
        (requested,), _kwargs = request.call_args
        return geometry.parse_geometry(requested)

    def test_a_saved_spot_on_a_current_monitor_is_reused(self):
        self.assertEqual(self.open_with("720x520+100+80"), (720, 520, 100, 80))

    def test_a_spot_on_an_unplugged_monitor_falls_back_to_the_centre(self):
        left, top, right, bottom = screen_of(self.root)
        width, height, x, y = self.open_with(f"720x520+{right + 3000}+{top + 50}")
        self.assertGreaterEqual(x, left)
        self.assertLessEqual(x + width, right)
        self.assertGreaterEqual(y, top)
        self.assertLessEqual(y + height, bottom)

    def test_a_spot_left_of_every_monitor_falls_back_to_the_centre(self):
        left, _top, right, _bottom = screen_of(self.root)
        width, _height, x, _y = self.open_with(f"720x520+{left - 4000}+50")
        self.assertGreaterEqual(x, left)
        self.assertLessEqual(x + width, right)

    def test_garbage_in_the_ini_falls_back_to_the_centre(self):
        width, height, x, y = self.open_with("garbage")
        left, top, right, bottom = screen_of(self.root)
        self.assertTrue(left <= x and x + width <= right and top <= y and y + height <= bottom)

    def test_a_saved_size_below_what_the_content_needs_is_raised_to_it(self):
        min_width, min_height = self.root.minsize()
        width, height, _x, _y = self.open_with("200x100+100+80")
        self.assertEqual((width, height), (min_width, min_height))

    def test_a_saved_size_larger_than_the_screen_is_cut_down(self):
        left, top, right, bottom = screen_of(self.root)
        width, height, _x, _y = self.open_with("90000x90000+0+0")
        self.assertLessEqual(width, right - left)
        self.assertLessEqual(height, bottom - top)


class MinimumSizeTest(AppTestCase):
    """The minimum comes from what the controls need, not from a fixed 460x360."""

    def rows(self):
        body = self.app.log.master
        return [w for w in body.winfo_children() if w is not self.app.log]

    def test_the_minimum_fits_the_widest_row_of_controls(self):
        self.root.update_idletasks()
        min_width, _min_height = self.root.minsize()
        self.assertGreaterEqual(min_width, max(row.winfo_reqwidth() for row in self.rows()))

    def test_the_minimum_fits_all_the_controls_and_a_few_log_rows(self):
        self.root.update_idletasks()
        _min_width, min_height = self.root.minsize()
        controls = sum(row.winfo_reqheight() for row in self.rows()) + self.app.menubar.winfo_reqheight()
        self.assertGreater(min_height, controls)

    def test_the_log_pane_does_not_force_the_window_to_stay_large(self):
        self.root.update_idletasks()
        min_width, min_height = self.root.minsize()
        self.assertLess(min_width, self.root.winfo_reqwidth())
        self.assertLess(min_height, self.root.winfo_reqheight())

    def test_measuring_leaves_the_log_pane_as_it_was(self):
        # the measuring trick asks the Text for 1 column x a few rows, then must give its size back
        self.assertGreater(int(self.app.log.cget("width")), 20)
        self.assertGreater(int(self.app.log.cget("height")), 8)

    def test_the_minimum_is_set_without_main_py(self):
        self.assertNotEqual(self.root.minsize(), (1, 1))


if __name__ == "__main__":
    unittest.main()
