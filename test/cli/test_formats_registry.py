import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "cli"))
import formats
from formats.format_7z import Format7zHandler
from formats.format_rar import FormatRarHandler

# Absolute path to cli/data (holds the real handlers.json).
DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "cli", "data",
)


class FormatsRegistryTest(unittest.TestCase):
    def setUp(self):
        # init_handlers mutates module-level MIME_HANDLERS / DETECTION_HANDLERS;
        # load the real handlers.json before every test for independence.
        formats.init_handlers(DATA_PATH)

    # --- static registry ------------------------------------------------- #
    def test_registry_has_nineteen_handlers(self):
        self.assertEqual(len(formats.HANDLER_REGISTRY), 19)

    def test_registry_keyed_by_class_name(self):
        self.assertIs(
            formats.HANDLER_REGISTRY["Format7zHandler"],
            Format7zHandler,
        )

    # --- init_handlers populated the runtime maps ------------------------ #
    def test_init_handlers_populates_maps(self):
        self.assertTrue(formats.MIME_HANDLERS)
        self.assertTrue(formats.DETECTION_HANDLERS)

    # --- get_handler_from_detection -------------------------------------- #
    def test_detection_routes_to_expected_handler(self):
        # pyinstaller is now handled by the 7z handler (dedicated handler removed).
        self.assertIs(
            formats.get_handler_from_detection("pyinstaller"),
            Format7zHandler,
        )

    def test_detection_lookup_is_case_insensitive(self):
        self.assertIs(
            formats.get_handler_from_detection("PyInstaller"),
            Format7zHandler,
        )

    def test_unknown_detection_returns_none(self):
        self.assertIsNone(formats.get_handler_from_detection("no-such-detection"))

    # --- get_handler_from_mime ------------------------------------------- #
    def test_mime_routes_to_expected_handler(self):
        self.assertIs(
            formats.get_handler_from_mime("application/x-7z-compressed"),
            Format7zHandler,
        )

    def test_mime_lookup_is_case_insensitive(self):
        self.assertIs(
            formats.get_handler_from_mime("APPLICATION/VND.RAR"),
            FormatRarHandler,
        )

    def test_unknown_mime_returns_none(self):
        self.assertIsNone(formats.get_handler_from_mime("application/x-no-such-mime"))


if __name__ == "__main__":
    unittest.main()
