import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))
from gui import config_io


class ConfigIoTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".ini")
        os.close(fd)

    def tearDown(self):
        os.remove(self.path)

    def test_read_existing(self):
        with open(self.path, "w") as fh:
            fh.write("[settings]\nopen_output_folder = False\ncheck_free_space = True\n")
        values = config_io.read_config(self.path)
        self.assertEqual(values["open_output_folder"], "False")
        self.assertEqual(values["check_free_space"], "True")

    def test_read_missing_section_returns_empty(self):
        with open(self.path, "w") as fh:
            fh.write("[other]\nx = 1\n")
        self.assertEqual(config_io.read_config(self.path), {})

    def test_write_creates_section(self):
        config_io.write_config(self.path, {"check_unicode": True})
        self.assertEqual(config_io.read_config(self.path)["check_unicode"], "True")

    def test_write_preserves_unrelated_keys(self):
        with open(self.path, "w") as fh:
            fh.write("[settings]\nopen_output_folder = False\nfast_check = True\n")
        config_io.write_config(self.path, {"open_output_folder": True})
        values = config_io.read_config(self.path)
        self.assertEqual(values["open_output_folder"], "True")
        self.assertEqual(values["fast_check"], "True")  # untouched



class ConfigBoolTest(unittest.TestCase):
    def test_reads_booleans_like_the_cli(self):
        values = {"a": "true", "b": "YES", "c": "1", "d": "False", "e": "off"}
        self.assertEqual([config_io.config_bool(values, k) for k in "abcde"],
                         [True, True, True, False, False])

    def test_missing_key_uses_the_cli_default(self):
        self.assertTrue(config_io.config_bool({}, "delete_to_recycle_bin"))
        self.assertFalse(config_io.config_bool({}, "check_unicode"))


if __name__ == "__main__":
    unittest.main()
