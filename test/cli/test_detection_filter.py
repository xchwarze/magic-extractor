import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "cli"))
import detection_filter

# Absolute path to cli/data (holds the real detection_blacklist.json).
DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "cli", "data",
)


class DetectionFilterTest(unittest.TestCase):
    def setUp(self):
        # init_blacklist mutates module-level globals; reload the real blacklist
        # before every test so the cases are independent of ordering.
        detection_filter.init_blacklist(DATA_PATH)

    # --- is_generic_mime / filter_mimes ---------------------------------- #
    def test_blacklisted_mime_is_generic(self):
        self.assertTrue(detection_filter.is_generic_mime("application/octet-stream"))

    def test_real_mime_is_not_generic(self):
        self.assertFalse(detection_filter.is_generic_mime("application/zip"))

    def test_mime_blacklist_is_case_insensitive(self):
        self.assertTrue(detection_filter.is_generic_mime("APPLICATION/OCTET-STREAM"))

    def test_filter_mimes_drops_blacklisted_keeps_real(self):
        result = detection_filter.filter_mimes(
            ["application/octet-stream", "application/zip", "text/plain"]
        )
        self.assertEqual(result, ["application/zip"])

    # --- is_generic_detection / filter_detections ------------------------ #
    def test_exact_blacklisted_detection_is_generic(self):
        self.assertTrue(detection_filter.is_generic_detection("unknown"))
        self.assertTrue(detection_filter.is_generic_detection("pe"))

    def test_real_detection_is_not_generic(self):
        self.assertFalse(detection_filter.is_generic_detection("pyinstaller"))
        self.assertFalse(detection_filter.is_generic_detection("7-zip"))

    def test_detection_exact_is_case_insensitive(self):
        self.assertTrue(detection_filter.is_generic_detection("UNKNOWN"))

    def test_substring_blacklist_matches_anywhere(self):
        # 'executable (generic)' is a blacklisted substring, so any string
        # containing it must be treated as generic noise.
        self.assertTrue(
            detection_filter.is_generic_detection("PE32 executable (generic)")
        )
        self.assertTrue(
            detection_filter.is_generic_detection("UPX compressed something")
        )

    def test_filter_detections_drops_generic_keeps_real(self):
        result = detection_filter.filter_detections(
            ["unknown", "pe", "pyinstaller", "7-zip", "PE32 executable (generic)"]
        )
        self.assertEqual(result, ["pyinstaller", "7-zip"])


if __name__ == "__main__":
    unittest.main()
