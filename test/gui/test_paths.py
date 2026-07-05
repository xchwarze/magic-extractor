import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gui import paths


class DefaultOutputDirTest(unittest.TestCase):
    def test_with_extension(self):
        self.assertEqual(
            paths.default_output_dir(os.path.join("dl", "app.zip")),
            os.path.join("dl", "app"),
        )

    def test_multi_dot_extension(self):
        # splitext strips only the last extension
        self.assertEqual(
            paths.default_output_dir(os.path.join("dl", "app.tar.gz")),
            os.path.join("dl", "app.tar"),
        )

    def test_no_extension(self):
        self.assertEqual(
            paths.default_output_dir(os.path.join("dl", "archive")),
            os.path.join("dl", "archive_extracted"),
        )

    def test_collision_with_existing_file_uses_underscores(self):
        with tempfile.TemporaryDirectory() as d:
            # source app.1.0.zip -> stem 'app.1.0'; create a file at that path
            colliding = os.path.join(d, "app.1.0")
            with open(colliding, "w") as fh:
                fh.write("x")
            result = paths.default_output_dir(os.path.join(d, "app.1.0.zip"))
            self.assertEqual(result, os.path.join(d, "app_1_0"))


if __name__ == "__main__":
    unittest.main()
