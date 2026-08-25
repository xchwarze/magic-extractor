import os
import sys
import tempfile
import unittest
import unittest.mock

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

    def test_carve_with_dest_and_options(self):
        opts = {"password": "pw", "fast_check": True, "debug": True}
        cmd = runner.build_command(self.PREFIX, "carve", "firmware.bin", "out", opts)
        self.assertEqual(cmd, ["magic-extractor.exe", "carve", "firmware.bin", "out",
                               "--password", "pw", "--fast-check", "--debug"])

    def test_carve_ignores_extract_only_options(self):
        opts = {"recursive": True, "max_depth": 9, "bruteforce": True,
                "delete_source": True}
        cmd = runner.build_command(self.PREFIX, "carve", "firmware.bin", None, opts)
        self.assertEqual(cmd, ["magic-extractor.exe", "carve", "firmware.bin"])

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

    def test_fast_check_off_adds_no_flag(self):
        cmd = runner.build_command(self.PREFIX, "extract", "a.7z", None, {"fast_check": False})
        self.assertEqual(cmd, ["magic-extractor.exe", "extract", "a.7z"])

    def test_fast_check_on_adds_flag(self):
        cmd = runner.build_command(self.PREFIX, "extract", "a.7z", None, {"fast_check": True})
        self.assertEqual(cmd, ["magic-extractor.exe", "extract", "a.7z", "--fast-check"])

    def test_scan_ignores_dest_and_extract_flags(self):
        opts = {"recursive": True, "max_depth": 9, "bruteforce": True, "password": "pw"}
        cmd = runner.build_command(self.PREFIX, "scan", "a.7z", "out", opts)
        self.assertEqual(cmd, ["magic-extractor.exe", "identify", "a.7z"])

    def test_delete_source_flag(self):
        cmd = runner.build_command(self.PREFIX, "extract", "a.7z", None, {"delete_source": True})
        self.assertEqual(cmd, ["magic-extractor.exe", "extract", "a.7z", "--delete-source"])

    def test_delete_source_omitted_when_false(self):
        cmd = runner.build_command(self.PREFIX, "extract", "a.7z", None, {"delete_source": False})
        self.assertEqual(cmd, ["magic-extractor.exe", "extract", "a.7z"])

    def test_scan_ignores_delete_source(self):
        cmd = runner.build_command(self.PREFIX, "scan", "a.7z", None, {"delete_source": True})
        self.assertEqual(cmd, ["magic-extractor.exe", "identify", "a.7z"])

    def test_debug_flag_extract(self):
        cmd = runner.build_command(self.PREFIX, "extract", "a.7z", None, {"debug": True})
        self.assertEqual(cmd, ["magic-extractor.exe", "extract", "a.7z", "--debug"])

    def test_debug_flag_scan(self):
        cmd = runner.build_command(self.PREFIX, "scan", "a.7z", None, {"debug": True})
        self.assertEqual(cmd, ["magic-extractor.exe", "identify", "a.7z", "--debug"])

    def test_debug_omitted_when_false(self):
        cmd = runner.build_command(self.PREFIX, "extract", "a.7z", None, {"debug": False})
        self.assertEqual(cmd, ["magic-extractor.exe", "extract", "a.7z"])

    def test_scan_without_fast_check(self):
        cmd = runner.build_command(self.PREFIX, "scan", "a.7z", None, {"fast_check": False})
        self.assertEqual(cmd, ["magic-extractor.exe", "identify", "a.7z"])

    def test_scan_fast_check_adds_flag(self):
        cmd = runner.build_command(self.PREFIX, "scan", "a.7z", None, {"fast_check": True})
        self.assertEqual(cmd, ["magic-extractor.exe", "identify", "a.7z", "--fast-check"])


class ReadVersionTest(unittest.TestCase):
    def test_reads_repo_root_version_file(self):
        with unittest.mock.patch.object(runner, "_repo_root", return_value=tempfile.gettempdir()):
            version_path = os.path.join(tempfile.gettempdir(), "VERSION")
            with open(version_path, "w", encoding="utf-8") as version_fh:
                version_fh.write("9.9.9\n")
            try:
                self.assertEqual(runner.read_version(), "9.9.9")
            finally:
                os.remove(version_path)

    def test_falls_back_when_missing(self):
        with unittest.mock.patch.object(runner, "_repo_root", return_value=tempfile.gettempdir()):
            missing_path = os.path.join(tempfile.gettempdir(), "VERSION")
            self.assertFalse(os.path.exists(missing_path))
            self.assertEqual(runner.read_version(), "dev")


if __name__ == "__main__":
    unittest.main()
