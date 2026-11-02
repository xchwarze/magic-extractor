"""Regressions from the CLI review (cli-design / windows-python-tooling / rabbit lenses)."""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src", "cli"))
import arguments  # noqa: E402
import carving  # noqa: E402
import config as config_module  # noqa: E402
import extraction  # noqa: E402
import helpers  # noqa: E402
from formats import base_extractor  # noqa: E402
from formats.base_extractor import BaseExtractor  # noqa: E402
from formats.format_7z import Format7zHandler  # noqa: E402
from formats.format_uharc import FormatUharcHandler  # noqa: E402


class TempDirTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, rel, text=""):
        path = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path


class MergeNeverReplacesTheSourceTest(TempDirTest):
    def test_archive_in_the_output_folder_survives_a_merge(self):
        archive = self.write("outer.zip", "THE ORIGINAL ARCHIVE")

        def extract(handler):
            with open(os.path.join(handler.extract_directory, "outer.zip"), "w") as fh:
                fh.write("a file inside the archive")
            return True

        handler_class = type("Inner", (BaseExtractor,), {"extract": extract})
        args = argparse.Namespace(file_path=archive, output_dir=self.tmp, password=None,
                                  fast_check=False, recursive=False, merge_output=True)
        with mock.patch.object(extraction, "find_candidate_handlers", return_value=[handler_class]):
            self.assertTrue(extraction.process_extraction(args))

        with open(archive, encoding="utf-8") as fh:
            self.assertEqual(fh.read(), "THE ORIGINAL ARCHIVE")
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "outer (1).zip")))


class ConfigToleranceTest(TempDirTest):
    def load(self, text):
        path = os.path.join(self.tmp, "config.ini")
        with open(path, "wb") as fh:
            fh.write(text)
        config_module.Config._instance = None
        try:
            return config_module.Config(path)
        finally:
            config_module.Config._instance = None

    def test_unknown_boolean_uses_the_fallback_not_false(self):
        config = self.load(b"[settings]\ndelete_to_recycle_bin = Ture\nempty =\n")
        with self.assertLogs(level="WARNING"):
            self.assertTrue(config.get("settings", "delete_to_recycle_bin", fallback=True, type=bool))
        with self.assertLogs(level="WARNING"):
            self.assertTrue(config.get("settings", "empty", fallback=True, type=bool))

    def test_utf8_bom_is_accepted(self):
        config = self.load(b"\xef\xbb\xbf[settings]\nfast_check = yes\n")
        self.assertTrue(config.get("settings", "fast_check", type=bool))

    def test_malformed_file_falls_back_to_defaults(self):
        with self.assertLogs(level="WARNING"):
            config = self.load(b"[settings]\nfast_check = yes\nfast_check = no\n")
        self.assertIsNone(config.get("settings", "fast_check", type=bool))

    def test_save_failure_is_reported_not_raised(self):
        config = self.load(b"[settings]\n")
        config.config_file_path = os.path.join(self.tmp, "missing-folder", "config.ini")
        with self.assertLogs(level="ERROR"):
            self.assertFalse(config.save())


class ExitCodesTest(TempDirTest):
    def test_failed_source_deletion_fails_the_run(self):
        archive = self.write("a.zip")
        args = argparse.Namespace(file_path=archive, delete_source=True, delete_to_recycle_bin=True)
        with mock.patch.object(extraction, "process_extraction", return_value=extraction.Outcome.OK), \
                mock.patch.object(extraction, "delete_source", return_value=False):
            self.assertFalse(extraction.run_extract(args))

    def test_folder_without_files_fails(self):
        os.makedirs(os.path.join(self.tmp, "only-a-subfolder"))
        args = argparse.Namespace(file_path=self.tmp, output_dir=None)
        with self.assertLogs(level="ERROR"):
            self.assertFalse(helpers.run_per_file(args, lambda _args: True))


class StaleStagingTest(TempDirTest):
    def test_staging_of_a_killed_run_is_removed_and_does_not_count_as_content(self):
        dead = subprocess.Popen([sys.executable, "-c", "pass"])
        dead.wait()
        stale = os.path.join(self.tmp, "out", f"{base_extractor.STAGING_PREFIX}{dead.pid}_abc")
        os.makedirs(stale)
        self.write(os.path.join("out", os.path.basename(stale), "partial.bin"), "x")
        args = argparse.Namespace(file_path=os.path.join(self.tmp, "a.zip"),
                                  output_dir=os.path.join(self.tmp, "out"))

        path, _created = extraction.resolve_output_dir(args)

        self.assertEqual(path, os.path.join(self.tmp, "out"))  # not a dated folder
        self.assertFalse(os.path.exists(stale))

    def test_staging_of_a_running_process_is_kept(self):
        live = os.path.join(self.tmp, "out", f"{base_extractor.STAGING_PREFIX}{os.getpid()}_abc")
        os.makedirs(live)
        base_extractor.remove_stale_staging(os.path.join(self.tmp, "out"))
        self.assertTrue(os.path.isdir(live))


class AnsiToolsTest(TempDirTest):
    def test_ascii_path_for_a_non_ascii_file(self):
        source = self.write("архив.ace", "payload")
        with base_extractor.ascii_path(source) as safe:
            self.assertTrue(all(ord(char) < 128 for char in safe))
            with open(safe, encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "payload")

    def test_ascii_folder_without_short_names_moves_the_output_back(self):
        target = os.path.join(self.tmp, "выход")
        os.makedirs(target)
        with mock.patch.object(base_extractor, "_short_folder", side_effect=lambda folder: folder):
            with base_extractor.ascii_folder(target) as workdir:
                self.assertTrue(all(ord(char) < 128 for char in workdir))
                with open(os.path.join(workdir, "out.txt"), "w") as fh:
                    fh.write("x")
        self.assertEqual(os.listdir(target), ["out.txt"])

    def test_uharc_tries_the_next_version_when_one_is_missing(self):
        archive = self.write("a.uha")
        handler = FormatUharcHandler(cli_args=argparse.Namespace(file_path=archive, output_dir=None,
                                                                 password=None), bin_path="bin")
        handler.extract_directory = self.tmp
        calls = []

        def run(command, workdir=None):
            calls.append(os.path.basename(command[0]))
            if len(calls) == 1:
                raise FileNotFoundError("missing exe")
            return ""

        with mock.patch.object(handler, "run_command", side_effect=run):
            self.assertTrue(handler.extract())
        self.assertEqual(len(calls), 2)


class SecretsAndEncodingTest(unittest.TestCase):
    def test_password_is_masked_in_the_debug_command(self):
        handler = BaseExtractor(cli_args=argparse.Namespace(file_path="a.7z", output_dir=None,
                                                            password="S3cretPW"), bin_path="bin")
        shown = handler.shown_command(["7z.exe", "x", "-pS3cretPW", "a.7z", "S3cretPW"])
        self.assertNotIn("S3cretPW", shown)

    def test_7z_listing_is_utf8(self):
        handler = Format7zHandler(cli_args=argparse.Namespace(file_path="a.zip", output_dir=None,
                                                              password=None), bin_path="bin")
        with mock.patch.object(handler, "run_command", return_value="ok") as run_command:
            handler.list_contents()
        command = run_command.call_args.args[0]
        self.assertIn("-sccUTF-8", command)
        self.assertEqual(run_command.call_args.kwargs.get("encoding"), "utf-8")


class CarveErrorsTest(TempDirTest):
    def test_unwritable_output_is_an_error_not_a_traceback(self):
        source = self.write("sfx.exe", "MZ" + "x" * 64)
        blocker = self.write("not-a-folder", "file in the way")
        args = argparse.Namespace(file_path=source, output_dir=os.path.join(blocker, "out"),
                                  list_fragments=False, fragment=None, raw=True,
                                  fast_check=False, password=None)
        entries = [{"offset": 0, "size": 10, "name": "zip"}]
        with mock.patch.object(carving, "binwalk_file_map", return_value=entries), \
                self.assertLogs(level="ERROR"):
            self.assertFalse(carving._carve_file(args))


class VersionFlagTest(unittest.TestCase):
    def test_version_prints_and_exits_zero(self):
        self.assertEqual(arguments.normalize_argv(["--version"]), ["--version"])
        with mock.patch("sys.stdout") as stdout, self.assertRaises(SystemExit) as raised:
            arguments.configure_parser().parse_args(["--version"])
        self.assertEqual(raised.exception.code, 0)
        self.assertTrue(stdout.write.called)


if __name__ == "__main__":
    unittest.main()
