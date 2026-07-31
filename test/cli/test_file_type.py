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


if __name__ == "__main__":
    unittest.main()
