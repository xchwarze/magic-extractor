import os
import tempfile
import unittest
from unittest import mock

from cli import file_type


class FastMagicCheckTest(unittest.TestCase):
    def test_fast_check_reads_only_first_64_kib(self):
        with tempfile.NamedTemporaryFile(delete=False) as sample:
            sample.write(b"x" * (file_type._FAST_MAGIC_READ_LEN + 1024))
            sample_path = sample.name
        try:
            with mock.patch.object(file_type.puremagic, "magic_string", return_value=[]) as magic_string:
                self.assertIsNone(file_type.determine_file_type_with_magic(sample_path, fast_check=True))
            inspected_data = magic_string.call_args.args[0]
            self.assertEqual(len(inspected_data), 64 * 1024)
        finally:
            os.remove(sample_path)


class RunJsonDetectorTest(unittest.TestCase):
    def _run(self, stdout):
        completed = mock.Mock(stdout=stdout)
        with mock.patch.object(file_type.subprocess, "run", return_value=completed) as run:
            result = file_type.run_json_detector(["tool"], "DIE", "sample.bin")
        return result, run

    def test_ignores_script_errors_after_the_json(self):
        # Real DIE output for an .ar archive: valid JSON, then a script error.
        stdout = (
            '{\n    "detects": [{"values": [{"type": "Archive", "name": "AR"}]}]\n}\n\n'
            "audio.1.sg: Binary/audio.1.sg: 149: ReferenceError: Can't find variable: X\n"
        )
        result, _run = self._run(stdout)
        self.assertEqual(result, {"detects": [{"values": [{"type": "Archive", "name": "AR"}]}]})

    def test_parses_a_json_list(self):
        result, _run = self._run('[{"Analysis": {"file_map": []}}]')
        self.assertEqual(result, [{"Analysis": {"file_map": []}}])

    def test_no_json_returns_none(self):
        result, _run = self._run("nothing useful")
        self.assertIsNone(result)

    def test_decodes_as_utf8_with_replacement(self):
        _result, run = self._run("{}")
        self.assertEqual(run.call_args.kwargs["encoding"], "utf-8")
        self.assertEqual(run.call_args.kwargs["errors"], "replace")


if __name__ == "__main__":
    unittest.main()
