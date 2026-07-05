import os
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cli"))
import helpers


class DeleteSourceTest(unittest.TestCase):
    def _temp_file(self):
        fd, path = tempfile.mkstemp()
        os.close(fd)
        return path

    def test_permanent_delete_removes_file(self):
        path = self._temp_file()
        self.assertTrue(helpers.delete_source(path, use_recycle_bin=False))
        self.assertFalse(os.path.exists(path))

    def test_permanent_delete_missing_file_returns_false(self):
        path = self._temp_file()
        os.remove(path)
        self.assertFalse(helpers.delete_source(path, use_recycle_bin=False))

    def test_recycle_uses_send2trash(self):
        path = self._temp_file()
        calls = []
        fake = types.ModuleType("send2trash")
        fake.send2trash = lambda p: calls.append(p)
        sys.modules["send2trash"] = fake
        try:
            self.assertTrue(helpers.delete_source(path, use_recycle_bin=True))
            self.assertEqual(calls, [path])
        finally:
            del sys.modules["send2trash"]
            os.remove(path)

    def test_recycle_without_send2trash_keeps_file(self):
        path = self._temp_file()
        sys.modules["send2trash"] = None  # forces ImportError on `import send2trash`
        try:
            self.assertFalse(helpers.delete_source(path, use_recycle_bin=True))
            self.assertTrue(os.path.exists(path))
        finally:
            del sys.modules["send2trash"]
            os.remove(path)


if __name__ == "__main__":
    unittest.main()
