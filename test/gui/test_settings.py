import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gui.settings import GuiSettings


class GuiSettingsTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".ini")
        os.close(fd)

    def tearDown(self):
        os.remove(self.path)

    def test_defaults_when_missing(self):
        s = GuiSettings(self.path)
        self.assertEqual(s.get("gui", "theme", "auto"), "auto")
        self.assertTrue(s.get_bool("gui", "keep_open", True))
        self.assertEqual(s.get_int("defaults", "max_depth", 5), 5)

    def test_roundtrip_preserves_other_keys(self):
        with open(self.path, "w") as fh:
            fh.write("[defaults]\nmode = scan\nmax_depth = 7\n")
        s = GuiSettings(self.path)
        s.set("defaults", "lock_destination", True)
        s.save()

        reloaded = GuiSettings(self.path)
        self.assertEqual(reloaded.get("defaults", "mode"), "scan")     # untouched
        self.assertEqual(reloaded.get_int("defaults", "max_depth"), 7)  # untouched
        self.assertTrue(reloaded.get_bool("defaults", "lock_destination"))

    def test_creates_section_on_set(self):
        s = GuiSettings(self.path)
        s.set("window", "geometry", "460x360+10+10")
        s.save()
        self.assertEqual(GuiSettings(self.path).get("window", "geometry"), "460x360+10+10")


if __name__ == "__main__":
    unittest.main()
