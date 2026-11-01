"""Window placement maths (pure functions, no display needed)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))
from gui import geometry  # noqa: E402

AREA = (0, 0, 1920, 1040)  # a 1080p monitor without its taskbar


class ClampIntoTest(unittest.TestCase):
    def test_a_window_that_fits_is_left_alone(self):
        self.assertEqual(geometry.clamp_into(100, 80, 400, 300, AREA), (100, 80))

    def test_a_dialog_hanging_off_the_right_and_bottom_edges_is_pulled_back(self):
        x, y = geometry.clamp_into(1800, 1000, 400, 300, AREA, extras=(8, 31))
        self.assertEqual(x, 1920 - 400 - 2 * 8)
        self.assertEqual(y, 1040 - 300 - 31 - 8)

    def test_a_dialog_above_or_left_of_the_area_is_pulled_in(self):
        self.assertEqual(geometry.clamp_into(-50, -20, 400, 300, AREA), (0, 0))

    def test_the_area_need_not_start_at_the_origin(self):
        secondary = (1920, 0, 3840, 1080)  # a monitor to the right of the primary
        self.assertEqual(geometry.clamp_into(1500, 10, 400, 300, secondary), (1920, 10))

    def test_a_window_taller_than_the_area_sticks_to_the_top(self):
        self.assertEqual(geometry.clamp_into(10, 500, 400, 5000, AREA), (10, 0))


class FitSizeTest(unittest.TestCase):
    def test_content_that_fits_keeps_its_size(self):
        self.assertEqual(geometry.fit_size(500, 400, AREA), (500, 400))

    def test_a_tall_dialog_is_capped_at_the_share_of_the_work_area(self):
        width, height = geometry.fit_size(500, 5000, AREA, extras=(8, 31))
        self.assertEqual(width, 500)
        self.assertEqual(height, int(1040 * geometry.MAX_SCREEN_SHARE))


if __name__ == "__main__":
    unittest.main()
