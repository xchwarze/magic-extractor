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
        "cli",
    ),
)

import carving
import detection
import extraction


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

    def test_find_candidates_runs_every_detector_in_bruteforce_mode(self):
        outputs = [("first", [], []), ("second", [], [])]

        with mock.patch.object(detection, "detector_outputs", return_value=outputs), \
                mock.patch.object(detection, "collect_candidates", return_value=True) as collect_mock, \
                mock.patch.object(detection, "append_pe_installer_fallbacks"):
            detection.find_candidate_handlers("archive.bin", False, bruteforce=True)

        self.assertEqual(collect_mock.call_count, 2)


class ExtractionWorkflowTest(unittest.TestCase):
    def test_process_extraction_runs_handler_lifecycle(self):
        events = []

        class SuccessfulHandler:
            def __init__(self, cli_args, bin_path):
                self.extract_directory = "output"
                events.append(("init", cli_args.file_path, bin_path))

            def pre_extract_actions(self):
                events.append("pre")

            def extract(self):
                events.append("extract")
                return True

            def post_extract_actions(self):
                events.append("post")

        args = argparse.Namespace(
            file_path="archive.bin", fast_check=False, recursive=False
        )
        with mock.patch.object(
            extraction, "find_candidate_handlers", return_value=[SuccessfulHandler]
        ):
            result = extraction.process_extraction(args)

        self.assertTrue(result)
        self.assertEqual([event for event in events if isinstance(event, str)], [
            "pre", "extract", "post"
        ])

    def test_process_extraction_returns_false_without_candidates(self):
        args = argparse.Namespace(file_path="unknown.bin", fast_check=False)
        with mock.patch.object(
            extraction, "find_candidate_handlers", return_value=[]
        ):
            self.assertFalse(extraction.process_extraction(args))


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
