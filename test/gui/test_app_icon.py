import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))
from gui import app_icon


class IconPathTest(unittest.TestCase):
    def test_source_run_uses_the_repo_asset(self):
        path = app_icon.icon_path()
        self.assertIsNotNone(path)
        self.assertEqual(os.path.basename(os.path.dirname(path)), "assets")
        self.assertTrue(os.path.isfile(path))

    def test_frozen_run_uses_the_bundled_copy(self):
        bundle = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(bundle, "assets"))
            bundled = os.path.join(bundle, "assets", app_icon.ICON_NAME)
            open(bundled, "wb").close()
            with mock.patch.object(sys, "frozen", True, create=True), \
                    mock.patch.object(sys, "_MEIPASS", bundle, create=True):
                self.assertEqual(app_icon.icon_path(), bundled)
        finally:
            import shutil
            shutil.rmtree(bundle, ignore_errors=True)

    def test_missing_icon_keeps_the_default(self):
        root = mock.Mock()
        with mock.patch.object(app_icon, "icon_path", return_value=None):
            app_icon.apply(root)
        root.iconbitmap.assert_not_called()

    def test_icon_applies_to_every_window(self):
        root = mock.Mock()
        with mock.patch.object(app_icon, "icon_path", return_value="x.ico"):
            app_icon.apply(root)
        root.iconbitmap.assert_called_once_with(default="x.ico")


if __name__ == "__main__":
    unittest.main()
