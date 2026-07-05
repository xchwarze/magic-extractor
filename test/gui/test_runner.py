import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gui import runner


class BuildCommandTest(unittest.TestCase):
    PREFIX = ["magic-extractor.exe"]

    def test_extract_minimal(self):
        cmd = runner.build_command(self.PREFIX, "extract", "a.7z", None, {})
        self.assertEqual(cmd, ["magic-extractor.exe", "extract", "a.7z"])

    def test_extract_with_dest(self):
        cmd = runner.build_command(self.PREFIX, "extract", "a.7z", "out", {})
        self.assertEqual(cmd, ["magic-extractor.exe", "extract", "a.7z", "out"])

    def test_blank_dest_omitted(self):
        cmd = runner.build_command(self.PREFIX, "extract", "a.7z", "", {})
        self.assertEqual(cmd, ["magic-extractor.exe", "extract", "a.7z"])

    def test_dest_precedes_flags(self):
        opts = {"bruteforce": True}
        cmd = runner.build_command(self.PREFIX, "extract", "a.7z", "out", opts)
        self.assertEqual(cmd, ["magic-extractor.exe", "extract", "a.7z", "out", "-b"])

    def test_password_included_when_set(self):
        cmd = runner.build_command(self.PREFIX, "extract", "a.7z", None, {"password": "pw"})
        self.assertEqual(cmd, ["magic-extractor.exe", "extract", "a.7z", "--password", "pw"])

    def test_password_omitted_when_blank(self):
        cmd = runner.build_command(self.PREFIX, "extract", "a.7z", None, {"password": ""})
        self.assertEqual(cmd, ["magic-extractor.exe", "extract", "a.7z"])

    def test_recursive_adds_max_depth(self):
        cmd = runner.build_command(self.PREFIX, "extract", "a.7z", None,
                                   {"recursive": True, "max_depth": 3})
        self.assertEqual(cmd, ["magic-extractor.exe", "extract", "a.7z", "-r", "--max-depth", "3"])

    def test_fast_check_off_adds_flag(self):
        cmd = runner.build_command(self.PREFIX, "extract", "a.7z", None, {"fast_check": False})
        self.assertEqual(cmd, ["magic-extractor.exe", "extract", "a.7z", "--no-fast-check"])

    def test_fast_check_on_no_flag(self):
        cmd = runner.build_command(self.PREFIX, "extract", "a.7z", None, {"fast_check": True})
        self.assertEqual(cmd, ["magic-extractor.exe", "extract", "a.7z"])

    def test_scan_ignores_dest_and_extract_flags(self):
        opts = {"recursive": True, "max_depth": 9, "bruteforce": True, "password": "pw"}
        cmd = runner.build_command(self.PREFIX, "scan", "a.7z", "out", opts)
        self.assertEqual(cmd, ["magic-extractor.exe", "identify", "a.7z"])


if __name__ == "__main__":
    unittest.main()
