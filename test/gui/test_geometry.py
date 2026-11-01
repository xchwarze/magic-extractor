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


class ParseGeometryTest(unittest.TestCase):
    def test_a_tk_geometry_string_is_split_into_size_and_position(self):
        self.assertEqual(geometry.parse_geometry("702x502+609+289"), (702, 502, 609, 289))

    def test_a_monitor_left_of_or_above_the_primary_gives_negative_coordinates(self):
        self.assertEqual(geometry.parse_geometry("500x400+-1800+-20"), (500, 400, -1800, -20))

    def test_junk_is_rejected(self):
        for text in ("", "garbage", "702x502", "+10+10", "702x502+10", "0x0+1+1x"):
            self.assertIsNone(geometry.parse_geometry(text), text)


class VisiblePositionTest(unittest.TestCase):
    """A saved position is only reused while the window stays reachable on a current monitor."""

    SCREEN = (0, 0, 1920, 1080)

    def test_a_position_on_screen_is_kept(self):
        self.assertEqual(geometry.visible_position((100, 80), (700, 500), self.SCREEN), (100, 80))

    def test_a_monitor_unplugged_on_the_right_means_no_position(self):
        self.assertIsNone(geometry.visible_position((2500, 100), (700, 500), self.SCREEN))

    def test_a_monitor_unplugged_on_the_left_means_no_position(self):
        self.assertIsNone(geometry.visible_position((-1900, 100), (700, 500), self.SCREEN))

    def test_a_monitor_unplugged_below_means_no_position(self):
        self.assertIsNone(geometry.visible_position((100, 1500), (700, 500), self.SCREEN))

    def test_a_second_monitor_on_the_left_is_a_valid_place(self):
        both = (-1920, 0, 1920, 1080)
        self.assertEqual(geometry.visible_position((-1800, 100), (700, 500), both), (-1800, 100))

    def test_a_window_mostly_off_the_right_edge_is_pulled_back_to_keep_its_title_bar(self):
        x, y = geometry.visible_position((1900, 100), (700, 500), self.SCREEN)
        self.assertLessEqual(x, 1920 - 120)
        self.assertEqual(y, 100)

    def test_the_title_bar_never_ends_up_below_the_screen(self):
        _x, y = geometry.visible_position((100, 1070), (700, 500), self.SCREEN)
        self.assertLessEqual(y, 1080 - 40)


if __name__ == "__main__":
    unittest.main()
