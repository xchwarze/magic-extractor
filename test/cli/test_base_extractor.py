import argparse
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "cli"))
from formats.base_extractor import BaseExtractor, merge_move
from formats.format_kgb import FormatKgbHandler, KGB_MAGIC
from formats.format_pea import FormatPeaHandler


def make_handler(cls, file_path="archive.bin"):
    args = argparse.Namespace(file_path=file_path, output_dir=None, password=None)
    return cls(cli_args=args, bin_path="bin")


class FailureMarkersTest(unittest.TestCase):
    def test_exit_zero_with_marker_is_a_failure(self):
        # unace exits 0 on a non-ACE file and only says so on stdout.
        handler = make_handler(BaseExtractor)
        with mock.patch.object(handler, "run_command", return_value="Is no ACE-archive: x.exe\n"):
            self.assertFalse(handler.run_extraction(["unace"], failure_markers=("Is no ACE-archive",)))

    def test_exit_zero_without_marker_is_a_success(self):
        handler = make_handler(BaseExtractor)
        with mock.patch.object(handler, "run_command", return_value="Extracting a.txt OK\n"):
            self.assertTrue(handler.run_extraction(["unace"], failure_markers=("Is no ACE-archive",)))

    def test_listing_with_marker_returns_none(self):
        handler = make_handler(BaseExtractor)
        with mock.patch.object(handler, "run_command", return_value="Archive is broken!\n"):
            self.assertIsNone(handler.run_listing(["kgb"], failure_markers=("Archive is broken!",)))

    def test_listing_returns_the_output(self):
        handler = make_handler(BaseExtractor)
        with mock.patch.object(handler, "run_command", return_value="a.txt\n"):
            self.assertEqual(handler.run_listing(["unrar", "l"]), "a.txt\n")


class MergeMoveTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, rel, text="x"):
        path = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(text)
        return path

    def test_file_replaces_file_and_folders_merge(self):
        self._write("src/d/new.txt", "new")
        self._write("dst/d/old.txt", "old")
        self._write("src/same.txt", "new")
        self._write("dst/same.txt", "old")
        for name in ("d", "same.txt"):
            merge_move(os.path.join(self.tmp, "src", name), os.path.join(self.tmp, "dst", name))
        self.assertEqual(sorted(os.listdir(os.path.join(self.tmp, "dst", "d"))), ["new.txt", "old.txt"])
        with open(os.path.join(self.tmp, "dst", "same.txt")) as fh:
            self.assertEqual(fh.read(), "new")

    def test_file_never_replaces_a_folder(self):
        self._write("src/data", "file from the archive")
        self._write("dst/data/keep.txt", "user folder")
        final = merge_move(os.path.join(self.tmp, "src", "data"), os.path.join(self.tmp, "dst", "data"))
        self.assertEqual(os.path.basename(final), "data (1)")
        self.assertTrue(os.path.isfile(os.path.join(self.tmp, "dst", "data", "keep.txt")))


class PeaHeaderGuardTest(unittest.TestCase):
    def test_non_pea_file_never_reaches_pea_exe(self):
        # pea.exe would block on a modal "NOT_PEA_HEADER" dialog.
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "foreign.pea")
            with open(path, "wb") as fh:
                fh.write(b"not a pea archive")
            handler = make_handler(FormatPeaHandler, path)
            handler.extract_directory = tmp
            with mock.patch.object(handler, "run_extraction") as run_extraction:
                self.assertFalse(handler.extract())
            run_extraction.assert_not_called()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class KgbSfxPayloadTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _offset(self, content):
        path = os.path.join(self.tmp, "sample")
        with open(path, "wb") as fh:
            fh.write(content)
        return make_handler(FormatKgbHandler, path)._sfx_payload_offset()

    def test_plain_archive_has_no_payload_offset(self):
        self.assertIsNone(self._offset(KGB_MAGIC + b"\r\n..."))

    def test_sfx_payload_offset(self):
        self.assertEqual(self._offset(b"MZ" + b"\0" * 98 + KGB_MAGIC + b"\r\n"), 100)

    def test_magic_split_across_scan_chunks_is_found(self):
        import formats.format_kgb as format_kgb
        stub = b"MZ" + b"\0" * (format_kgb._SCAN_CHUNK - 5)
        self.assertEqual(self._offset(stub + KGB_MAGIC), len(stub))

    def test_pe_without_payload(self):
        self.assertEqual(self._offset(b"MZ" + b"\0" * 64), -1)


if __name__ == "__main__":
    unittest.main()
