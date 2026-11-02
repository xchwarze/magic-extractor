import argparse
import contextlib
import io
import os
import sys
import unittest
from unittest import mock


sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "src",
        "cli",
    ),
)

import carving
import detection
import extraction
import helpers


class DetectionWorkflowTest(unittest.TestCase):
    def test_find_candidates_stops_after_first_mapped_detector(self):
        first_handler = object()
        outputs = [
            ("first", [], ["known"]),
            ("second", [], ["also-known"]),
        ]

        def collect(output, candidates):
            candidates.append(first_handler)
            return True

        with mock.patch.object(detection, "detector_outputs", return_value=outputs), \
                mock.patch.object(detection, "collect_candidates", side_effect=collect) as collect_mock, \
                mock.patch.object(detection, "append_pe_installer_fallbacks"):
            candidates = detection.find_candidate_handlers("archive.bin", False)

        self.assertEqual(candidates, [first_handler])
        self.assertEqual(collect_mock.call_count, 1)

    def test_collect_candidates_adds_every_handler_of_a_shared_key(self):
        primary, fallback = type("Primary", (), {}), type("Fallback", (), {})
        candidates = []

        with mock.patch.object(detection, "get_handlers_from_mime", return_value=(primary, fallback)), \
                mock.patch.object(detection, "get_handlers_from_detection", return_value=(fallback,)), \
                mock.patch.object(detection, "filter_mimes", side_effect=lambda values: values), \
                mock.patch.object(detection, "filter_detections", side_effect=lambda values: values):
            added = detection.collect_candidates(("src", ["mime/x"], ["name"]), candidates)

        self.assertTrue(added)
        self.assertEqual(candidates, [primary, fallback])  # priority order, no duplicates

    def test_find_candidates_runs_every_detector_in_bruteforce_mode(self):
        outputs = [("first", [], []), ("second", [], [])]

        with mock.patch.object(detection, "detector_outputs", return_value=outputs), \
                mock.patch.object(detection, "collect_candidates", return_value=True) as collect_mock, \
                mock.patch.object(detection, "append_pe_installer_fallbacks"):
            detection.find_candidate_handlers("archive.bin", False, bruteforce=True)

        self.assertEqual(collect_mock.call_count, 2)


class RunPerFileTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _touch(self, *names):
        for name in names:
            open(os.path.join(self.tmp, name), "w").close()

    def test_single_file_is_processed_as_is(self):
        self._touch("a.zip")
        path = os.path.join(self.tmp, "a.zip")
        args = argparse.Namespace(file_path=path, output_dir=None)
        seen = []
        self.assertTrue(helpers.run_per_file(args, lambda a: seen.append(a.file_path) or True))
        self.assertEqual(seen, [path])

    def test_directory_runs_each_file_never_the_directory(self):
        self._touch("b.7z", "a.zip")
        os.mkdir(os.path.join(self.tmp, "sub"))
        args = argparse.Namespace(file_path=self.tmp, output_dir=None)
        seen = []
        helpers.run_per_file(args, lambda a: seen.append(a.file_path.name) or True)
        self.assertEqual(seen, ["a.zip", "b.7z"])  # sorted, files only

    def test_directory_with_output_dir_gives_each_file_its_own_folder(self):
        self._touch("a.zip", "b.7z")
        args = argparse.Namespace(file_path=self.tmp, output_dir="out")
        outputs = []
        helpers.run_per_file(
            args,
            lambda a: outputs.append(str(a.output_dir)) or True,
            output_name=extraction.batch_output_name,
        )
        self.assertEqual(outputs, [os.path.join("out", "a_extracted"), os.path.join("out", "b_extracted")])

    def test_directory_without_output_dir_uses_each_files_folder(self):
        self._touch("a.zip")
        args = argparse.Namespace(file_path=self.tmp, output_dir=None)
        outputs = []
        helpers.run_per_file(
            args,
            lambda a: outputs.append(str(a.output_dir)) or True,
            output_name=extraction.batch_output_name,
        )
        self.assertEqual(outputs, [os.path.join(self.tmp, "a_extracted")])

    def test_files_sharing_a_stem_get_distinct_folders(self):
        self._touch("a.zip", "a.7z", "b.gz")
        args = argparse.Namespace(file_path=self.tmp, output_dir="out")
        outputs = []
        helpers.run_per_file(
            args,
            lambda a: outputs.append(os.path.basename(str(a.output_dir))) or True,
            output_name=extraction.batch_output_name,
        )
        self.assertEqual(outputs, ["a.7z_extracted", "a.zip_extracted", "b_extracted"])

    def test_one_failure_fails_the_batch_but_keeps_going(self):
        self._touch("a.zip", "b.7z")
        args = argparse.Namespace(file_path=self.tmp, output_dir=None)
        seen = []
        result = helpers.run_per_file(args, lambda a: seen.append(a.file_path.name) or a.file_path.name != "a.zip")
        self.assertFalse(result)
        self.assertEqual(seen, ["a.zip", "b.7z"])


def make_handler_class(name, writes=(), result=True, events=None):
    """A BaseExtractor whose extract() writes `writes` into its folder and returns `result`."""
    from formats.base_extractor import BaseExtractor

    def extract(self):
        if events is not None:
            events.append((name, os.path.basename(self.extract_directory)))
        for file_name in writes:
            with open(os.path.join(self.extract_directory, file_name), "w") as fh:
                fh.write(name)
        return result

    return type(name, (BaseExtractor,), {"extract": extract})


class ExtractionWorkflowTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp()
        self.archive = os.path.join(self.tmp, "archive.bin")
        open(self.archive, "w").close()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _args(self, **extra):
        return argparse.Namespace(file_path=self.archive, output_dir=None, password=None,
                                  fast_check=False, recursive=False, **extra)

    def _extract(self, *handlers, **extra):
        with mock.patch.object(extraction, "find_candidate_handlers", return_value=list(handlers)):
            return extraction.process_extraction(self._args(**extra))

    def _tree(self, path):
        return sorted(os.path.relpath(os.path.join(root, name), path)
                      for root, dirs, files in os.walk(path) for name in dirs + files)

    def test_success_lands_in_the_output_folder_without_staging_leftovers(self):
        events = []
        self.assertTrue(self._extract(make_handler_class("Ok", writes=["a.txt"], events=events)))
        out = os.path.join(self.tmp, "archive_extracted")
        self.assertEqual(self._tree(out), ["a.txt"])
        # extract() ran inside a staging folder, not in the output folder itself
        self.assertTrue(events[0][1].startswith(".mx_staging_"))

    def test_failed_attempt_leaves_nothing_for_the_next_one(self):
        self.assertTrue(self._extract(
            make_handler_class("Broken", writes=["partial.bin"], result=False),
            make_handler_class("Good", writes=["good.txt"]),
        ))
        self.assertEqual(self._tree(os.path.join(self.tmp, "archive_extracted")), ["good.txt"])

    def test_success_that_extracted_nothing_is_a_failure(self):
        self.assertTrue(self._extract(
            make_handler_class("Liar", writes=(), result=True),
            make_handler_class("Good", writes=["good.txt"]),
        ))
        self.assertEqual(self._tree(os.path.join(self.tmp, "archive_extracted")), ["good.txt"])

    def test_total_failure_removes_the_folder_it_created(self):
        self.assertFalse(self._extract(make_handler_class("Broken", writes=(), result=False)))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "archive_extracted")))

    def test_existing_output_gets_a_dated_sibling(self):
        out = os.path.join(self.tmp, "archive_extracted")
        os.makedirs(out)
        open(os.path.join(out, "old.txt"), "w").close()

        self.assertTrue(self._extract(make_handler_class("Ok", writes=["new.txt"])))

        self.assertEqual(self._tree(out), ["old.txt"])  # untouched
        dated = [name for name in os.listdir(self.tmp) if name.startswith("archive_extracted_")]
        self.assertEqual(len(dated), 1)
        self.assertEqual(self._tree(os.path.join(self.tmp, dated[0])), ["new.txt"])

    def test_merge_output_extracts_into_the_existing_folder(self):
        out = os.path.join(self.tmp, "archive_extracted")
        os.makedirs(out)
        open(os.path.join(out, "old.txt"), "w").close()

        self.assertTrue(self._extract(make_handler_class("Ok", writes=["new.txt"]), merge_output=True))

        self.assertEqual(self._tree(out), ["new.txt", "old.txt"])
        self.assertEqual(os.listdir(self.tmp), ["archive.bin", "archive_extracted"])

    def test_given_output_dir_is_removed_when_nothing_was_extracted(self):
        out = os.path.join(self.tmp, "out")  # given, not created by argparse
        with mock.patch.object(extraction, "find_candidate_handlers",
                               return_value=[make_handler_class("Broken", writes=(), result=False)]):
            self.assertFalse(extraction.process_extraction(self._args_with(output_dir=out)))
        self.assertFalse(os.path.exists(out))

    def test_merge_output_post_processing_ignores_what_was_already_there(self):
        out = os.path.join(self.tmp, "shared")
        os.makedirs(out)
        with open(os.path.join(out, "NOTES"), "w") as fh:
            fh.write("plain text the user keeps here\n")
        open(os.path.join(out, "old.zip"), "w").close()
        nested = []

        def candidates(file_path, **_kwargs):
            if str(file_path) == self.archive:
                return [make_handler_class("Ok", writes=["new.bin"])]
            nested.append(os.path.basename(str(file_path)))
            return []

        args = self._args_with(output_dir=out, merge_output=True, fix_file_extensions=True,
                               recursive=True, max_depth=5)
        with mock.patch.object(extraction, "find_candidate_handlers", side_effect=candidates):
            self.assertTrue(extraction.process_extraction(args))

        self.assertIn("NOTES", os.listdir(out))  # not renamed to NOTES.txt
        self.assertEqual(nested, ["new.bin"])    # old.zip is not recursed into

    def _args_with(self, **values):
        args = self._args()
        for key, value in values.items():
            setattr(args, key, value)
        return args

    def test_process_extraction_returns_false_without_candidates(self):
        args = argparse.Namespace(file_path="unknown.bin", fast_check=False)
        with mock.patch.object(
            extraction, "find_candidate_handlers", return_value=[]
        ):
            self.assertFalse(extraction.process_extraction(args))


class ResolveOutputDirTest(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.mkdtemp()
        self.now = __import__("datetime").datetime(2026, 11, 1, 14, 5, 9)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _resolve(self, output_dir, **extra):
        args = argparse.Namespace(file_path=os.path.join(self.tmp, "a.zip"), output_dir=output_dir, **extra)
        return extraction.resolve_output_dir(args, now=self.now)

    def test_default_is_created_beside_the_file(self):
        path, created = self._resolve(None)
        self.assertEqual(path, os.path.join(self.tmp, "a_extracted"))
        self.assertTrue(created and os.path.isdir(path))

    def test_existing_empty_folder_is_reused(self):
        out = os.path.join(self.tmp, "out")
        os.makedirs(out)
        self.assertEqual(self._resolve(out), (out, False))

    def test_non_empty_folder_gets_a_dated_name_and_a_counter_on_collision(self):
        out = os.path.join(self.tmp, "out")
        os.makedirs(out)
        open(os.path.join(out, "x"), "w").close()
        os.makedirs(out + "_20261101-140509")
        path, created = self._resolve(out)
        self.assertEqual(path, out + "_20261101-140509-2")
        self.assertTrue(created)

    def test_merge_output_reuses_a_non_empty_folder(self):
        out = os.path.join(self.tmp, "out")
        os.makedirs(out)
        open(os.path.join(out, "x"), "w").close()
        self.assertEqual(self._resolve(out, merge_output=True), (out, False))


class CarvingWorkflowTest(unittest.TestCase):
    def test_process_carve_lists_fragments_without_writing(self):
        entries = [
            {
                "offset": 16,
                "size": 32,
                "name": "7-zip",
                "description": "7-Zip archive",
            }
        ]
        args = argparse.Namespace(
            file_path="archive.bin",
            list_fragments=True,
            fragment=None,
            raw=False,
            output_dir=None,
        )
        output = io.StringIO()
        with mock.patch.object(carving, "binwalk_file_map", return_value=entries), \
                contextlib.redirect_stdout(output):
            result = carving.process_carve(args)

        self.assertTrue(result)
        self.assertIn("7-zip", output.getvalue())
        self.assertIn("1 fragment(s)", output.getvalue())

    def test_process_carve_rejects_out_of_range_fragment(self):
        args = argparse.Namespace(
            file_path="archive.bin",
            list_fragments=False,
            fragment=2,
            raw=False,
            output_dir=None,
        )
        with mock.patch.object(
            carving,
            "binwalk_file_map",
            return_value=[{"offset": 0, "size": 1, "name": "raw"}],
        ):
            self.assertFalse(carving.process_carve(args))


if __name__ == "__main__":
    unittest.main()
