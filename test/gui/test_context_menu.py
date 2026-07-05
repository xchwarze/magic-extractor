import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gui import context_menu


class ContextMenuTest(unittest.TestCase):
    def test_command_string_single_part(self):
        self.assertEqual(
            context_menu.command_string(["C:/x/magic-extractor-gui.exe"]),
            '"C:/x/magic-extractor-gui.exe" "%1"',
        )

    def test_command_string_python_launcher(self):
        self.assertEqual(
            context_menu.command_string(["python.exe", "C:/app/gui/main.py"]),
            '"python.exe" "C:/app/gui/main.py" "%1"',
        )

    def test_is_supported_is_bool(self):
        self.assertIsInstance(context_menu.is_supported(), bool)


if __name__ == "__main__":
    unittest.main()
