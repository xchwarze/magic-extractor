"""Partial extractions: a tool that fails after writing files (e.g. 7z exit 2 because
Windows refused to create a symlink from a Linux image) keeps what it extracted."""
import argparse
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src", "cli"))
import extraction  # noqa: E402
from formats.base_extractor import STAGING_PREFIX, BaseExtractor  # noqa: E402


def handler_class(name, files, result):
    """A BaseExtractor writing ``files`` ({name: text}) and returning ``result``."""
    def extract(self):
        for file_name, text in files.items():
            with open(os.path.join(self.extract_directory, file_name), "w") as fh:
                fh.write(text)
        return result
    return type(name, (BaseExtractor,), {"extract": extract})


class PartialExtractionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.archive = os.path.join(self.tmp, "image.sqsh")
        open(self.archive, "w").close()
        self.out = os.path.join(self.tmp, "image_extracted")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_with(self, *handlers, **extra):
        args = argparse.Namespace(file_path=self.archive, output_dir=None, password=None,
                                  fast_check=False, recursive=False, **extra)
        with mock.patch.object(extraction, "find_candidate_handlers", return_value=list(handlers)):
            return extraction.process_extraction(args)

    def files(self):
        return sorted(os.listdir(self.out)) if os.path.isdir(self.out) else None

    def test_a_partial_extraction_keeps_what_was_extracted(self):
        outcome = self.run_with(handler_class("Seven", {"real.txt": "hello"}, False))
        self.assertIs(outcome, extraction.Outcome.PARTIAL)
        self.assertFalse(outcome)  # never mistaken for a full success (e.g. by --delete-source)
        self.assertEqual(self.files(), ["real.txt"])

    def test_a_later_full_success_wins_over_a_partial(self):
        outcome = self.run_with(handler_class("Seven", {"half.txt": "x"}, False),
                                handler_class("Zs", {"full.txt": "x"}, True))
        self.assertIs(outcome, extraction.Outcome.OK)
        self.assertEqual(self.files(), ["full.txt"])

    def test_the_biggest_partial_is_kept(self):
        outcome = self.run_with(handler_class("Small", {"a.txt": "x"}, False),
                                handler_class("Big", {"a.txt": "x" * 100, "b.txt": "y" * 100}, False))
        self.assertIs(outcome, extraction.Outcome.PARTIAL)
        self.assertEqual(self.files(), ["a.txt", "b.txt"])

    def test_no_staging_folder_is_left_behind(self):
        self.run_with(handler_class("Seven", {"a.txt": "x"}, False),
                      handler_class("Zs", {"b.txt": "y"}, False))
        self.assertEqual([n for n in self.files() if n.startswith(STAGING_PREFIX)], [])

    def test_a_failure_with_nothing_written_is_still_a_failure(self):
        outcome = self.run_with(handler_class("Empty", {}, False))
        self.assertIs(outcome, extraction.Outcome.FAILED)
        self.assertIsNone(self.files())  # the folder it created is removed again

    def test_partial_never_deletes_the_source(self):
        args = argparse.Namespace(file_path=self.archive, delete_source=True, delete_to_recycle_bin=True)
        with mock.patch.object(extraction, "process_extraction", return_value=extraction.Outcome.PARTIAL), \
                mock.patch.object(extraction, "delete_source") as delete_source:
            outcome = extraction.run_extract(args)
        self.assertIs(outcome, extraction.Outcome.PARTIAL)
        delete_source.assert_not_called()

    def test_exit_codes(self):
        self.assertEqual(extraction.EXIT_CODES[extraction.Outcome.OK], 0)
        self.assertEqual(extraction.EXIT_CODES[extraction.Outcome.FAILED], 1)
        self.assertEqual(extraction.EXIT_CODES[extraction.Outcome.PARTIAL], 3)


if __name__ == "__main__":
    unittest.main()
