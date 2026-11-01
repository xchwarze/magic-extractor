"""gui/main.py start-up, without opening a real window (everything that makes one is mocked)."""
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))
from gui import main as gui_main  # noqa: E402


class StartupFailureTest(unittest.TestCase):
    def run_main(self, **overrides):
        root = mock.Mock()
        root.winfo_fpixels.return_value = 96.0
        patches = {
            "_enable_dpi_awareness": mock.DEFAULT, "_make_root": mock.Mock(return_value=root),
            "ExtractorApp": mock.Mock(),
        }
        patches.update(overrides)
        with mock.patch.multiple(gui_main, **patches), \
                mock.patch.object(gui_main.app_icon, "set_app_user_model_id"), \
                mock.patch.object(gui_main.app_icon, "apply"), \
                mock.patch.object(gui_main.logging_setup, "configure") as configure, \
                mock.patch.object(gui_main.logging_setup, "report_fatal") as fatal:
            code = gui_main.main()
        return code, root, configure, fatal

    def test_logging_is_configured_before_anything_else_can_fail(self):
        order = []
        _code, _root, configure, _fatal = self.run_main(
            _enable_dpi_awareness=mock.Mock(side_effect=lambda: order.append("dpi")))
        configure.assert_called_once()
        self.assertEqual(order, ["dpi"])

    def test_a_window_that_cannot_start_is_reported_not_swallowed_silently(self):
        code, root, _configure, fatal = self.run_main(
            ExtractorApp=mock.Mock(side_effect=RuntimeError("no theme")))
        self.assertEqual(code, 1)
        fatal.assert_called_once()
        self.assertIn("no theme", fatal.call_args.args[1])
        root.mainloop.assert_not_called()

    def test_a_normal_start_enters_the_main_loop(self):
        code, root, _configure, fatal = self.run_main()
        self.assertEqual(code, 0)
        root.mainloop.assert_called_once()
        fatal.assert_not_called()


if __name__ == "__main__":
    unittest.main()
