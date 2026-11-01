import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))
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


class GuiSettingsRobustnessTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "gui.ini")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)

    def write(self, text):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def test_unicode_and_percent_values_round_trip(self):
        self.write("[history]\n")
        settings = GuiSettings(self.path)
        settings.set("history", "sources", "C:/архив 100%.zip")
        settings.save()
        self.assertEqual(GuiSettings(self.path).get("history", "sources"), "C:/архив 100%.zip")

    def test_save_keeps_comments_and_only_changes_values(self):
        self.write("; how to use this file\n[gui]\n; keep the window\nkeep_open = True\n")
        settings = GuiSettings(self.path)
        settings.set("gui", "keep_open", False)
        settings.set("window", "geometry", "500x400+0+0")
        settings.save()
        with open(self.path, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("; how to use this file", text)
        self.assertIn("; keep the window", text)
        self.assertIn("keep_open = False", text)
        self.assertIn("[window]", text)

    def test_malformed_file_reads_as_defaults(self):
        self.write("stray line before any section\n[gui]\n")
        self.assertTrue(GuiSettings(self.path).get_bool("gui", "keep_open", True))

    def test_failed_write_leaves_the_file_intact(self):
        self.write("[gui]\nkeep_open = True\n")
        settings = GuiSettings(self.path)
        settings.set("gui", "keep_open", False)
        from unittest import mock
        with mock.patch("gui.settings.os.replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                settings.save()
        with open(self.path, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "[gui]\nkeep_open = True\n")
        self.assertEqual([n for n in os.listdir(self.dir) if n != "gui.ini"], [])


if __name__ == "__main__":
    unittest.main()
