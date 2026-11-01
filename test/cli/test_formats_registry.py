import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src", "cli"))
import formats
from formats.format_7z import Format7zHandler
from formats.format_7z_ext import Format7zExtHandler
from formats.format_7z_zs import Format7zZsHandler
from formats.format_lzip import FormatLzipHandler
from formats.format_rar import FormatRarHandler

# Absolute path to cli/data (holds the real handlers.json).
DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "src", "cli", "data",
)


class FormatsRegistryTest(unittest.TestCase):
    def setUp(self):
        # init_handlers mutates module-level MIME_HANDLERS / DETECTION_HANDLERS;
        # load the real handlers.json before every test for independence.
        formats.init_handlers(DATA_PATH)

    # --- static registry ------------------------------------------------- #
    def test_registry_has_twenty_one_handlers(self):
        self.assertEqual(len(formats.HANDLER_REGISTRY), 21)

    def test_registry_keyed_by_class_name(self):
        self.assertIs(
            formats.HANDLER_REGISTRY["Format7zHandler"],
            Format7zHandler,
        )

    # --- init_handlers populated the runtime maps ------------------------ #
    def test_init_handlers_populates_maps(self):
        self.assertTrue(formats.MIME_HANDLERS)
        self.assertTrue(formats.DETECTION_HANDLERS)

    # --- get_handlers_from_detection ------------------------------------- #
    def test_detection_routes_to_expected_handler(self):
        # pyinstaller needs a 7z plugin, so it routes to the extended handler.
        self.assertEqual(
            formats.get_handlers_from_detection("pyinstaller"),
            (Format7zExtHandler,),
        )

    def test_detection_lookup_is_case_insensitive(self):
        self.assertEqual(
            formats.get_handlers_from_detection("PyInstaller"),
            (Format7zExtHandler,),
        )

    def test_unknown_detection_returns_empty(self):
        self.assertEqual(formats.get_handlers_from_detection("no-such-detection"), ())

    # --- get_handlers_from_mime ------------------------------------------ #
    def test_mime_routes_to_expected_handler(self):
        self.assertEqual(
            formats.get_handlers_from_mime("application/vnd.rar"),
            (FormatRarHandler,),
        )

    def test_mime_lookup_is_case_insensitive(self):
        self.assertEqual(
            formats.get_handlers_from_mime("APPLICATION/VND.RAR"),
            (FormatRarHandler,),
        )

    def test_unknown_mime_returns_empty(self):
        self.assertEqual(formats.get_handlers_from_mime("application/x-no-such-mime"), ())

    # --- shared keys: several handlers, in registry (priority) order ------ #
    def test_shared_mime_lists_fallback_after_primary(self):
        self.assertEqual(
            formats.get_handlers_from_mime("application/x-7z-compressed"),
            (Format7zHandler, Format7zZsHandler),
        )

    def test_shared_detection_follows_registry_order(self):
        # Format7zZsHandler is registered before FormatLzipHandler.
        self.assertEqual(
            formats.get_handlers_from_detection("lzip compressed archive"),
            (Format7zZsHandler, FormatLzipHandler),
        )
        self.assertEqual(
            formats.get_handlers_from_detection("nullsoft scriptable install system"),
            (Format7zHandler, Format7zZsHandler),
        )

    def test_init_handlers_accepts_string_or_list(self):
        data_dir = tempfile.mkdtemp()
        try:
            with open(os.path.join(data_dir, "handlers.json"), "w", encoding="utf-8") as fh:
                json.dump({
                    "mime_handlers": {"application/x-foo": "FormatRarHandler"},
                    "detection_handlers": {"foo": ["Format7zHandler", "NoSuchHandler", "Format7zExtHandler"]},
                }, fh)
            formats.init_handlers(data_dir)
            self.assertEqual(formats.get_handlers_from_mime("application/x-foo"), (FormatRarHandler,))
            # unknown class names are skipped, the rest keep their order
            self.assertEqual(formats.get_handlers_from_detection("foo"), (Format7zHandler, Format7zExtHandler))
        finally:
            shutil.rmtree(data_dir)


if __name__ == "__main__":
    unittest.main()
