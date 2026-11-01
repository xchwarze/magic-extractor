import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))
from gui import option_warnings
from gui.app import CONFIG_KEYS, GUI_LABELS

# Options rendered in the Run options dialog (not in CONFIG_KEYS / GUI_LABELS).
RUN_OPTION_KEYS = {"recursive", "bruteforce", "fast_check", "delete_source"}


class OptionWarningsTest(unittest.TestCase):
    def test_shown_only_in_the_risky_state(self):
        self.assertIsNotNone(option_warnings.warning_for("fix_file_extensions", True))
        self.assertIsNone(option_warnings.warning_for("fix_file_extensions", False))

    def test_inverted_options_warn_when_off(self):
        self.assertIsNotNone(option_warnings.warning_for("delete_to_recycle_bin", False))
        self.assertIsNone(option_warnings.warning_for("delete_to_recycle_bin", True))
        self.assertIsNotNone(option_warnings.warning_for("keep_open", False))

    def test_delete_source_warns_for_delete_and_ask(self):
        self.assertIsNotNone(option_warnings.warning_for("delete_source", "delete"))
        self.assertIsNotNone(option_warnings.warning_for("delete_source", "ask"))
        self.assertIsNone(option_warnings.warning_for("delete_source", "keep"))

    def test_options_without_caveats_have_no_warning(self):
        self.assertIsNone(option_warnings.warning_for("always_on_top", True))

    def test_every_warning_belongs_to_an_option_the_dialogs_render(self):
        known = set(CONFIG_KEYS) | set(GUI_LABELS) | RUN_OPTION_KEYS
        self.assertEqual(set(option_warnings.OPTION_WARNINGS) - known, set())


if __name__ == "__main__":
    unittest.main()
