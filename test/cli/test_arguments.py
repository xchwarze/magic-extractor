import argparse
import os
import sys
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "cli"))
import arguments


class NormalizeArgvTest(unittest.TestCase):
    def test_defaults_to_extract(self):
        self.assertEqual(arguments.normalize_argv(["a.zip"]), ["extract", "a.zip"])

    def test_options_before_the_file_still_default_to_extract(self):
        self.assertEqual(
            arguments.normalize_argv(["--debug", "a.zip", "out"]),
            ["extract", "--debug", "a.zip", "out"],
        )

    def test_option_value_is_not_taken_as_the_subcommand(self):
        self.assertEqual(
            arguments.normalize_argv(["--password", "x", "a.zip"]),
            ["extract", "--password", "x", "a.zip"],
        )

    def test_subcommand_moves_in_front_of_leading_options(self):
        self.assertEqual(
            arguments.normalize_argv(["--debug", "list", "a.zip"]),
            ["list", "--debug", "a.zip"],
        )

    def test_explicit_subcommand_is_untouched(self):
        self.assertEqual(arguments.normalize_argv(["carve", "a.bin"]), ["carve", "a.bin"])

    def test_a_file_named_like_a_subcommand_after_the_file_is_kept(self):
        self.assertEqual(
            arguments.normalize_argv(["a.zip", "list"]),
            ["extract", "a.zip", "list"],
        )

    def test_option_values_are_skipped_when_looking_for_the_subcommand(self):
        self.assertEqual(
            arguments.normalize_argv(["--password", "pw", "list", "x.rar"]),
            ["list", "--password", "pw", "x.rar"],
        )

    def test_value_options_match_the_parser(self):
        parser = arguments.configure_parser()
        subparsers = next(action for action in parser._actions
                          if isinstance(action, argparse._SubParsersAction))
        taking_values = {
            option
            for subparser in subparsers.choices.values()
            for action in subparser._actions
            if action.option_strings and action.nargs != 0
            for option in action.option_strings if option.startswith("--")
        }
        self.assertEqual(taking_values, set(arguments.VALUE_OPTIONS))

    def test_output_dir_check_does_not_create_the_folder(self):
        import tempfile
        tmp = tempfile.mkdtemp()
        try:
            missing = os.path.join(tmp, "not-yet")
            arguments.dir_path_type_check(missing)
            self.assertFalse(os.path.exists(missing))
        finally:
            os.rmdir(tmp)

    def test_help_and_empty_are_untouched(self):
        self.assertEqual(arguments.normalize_argv(["-h"]), ["-h"])
        self.assertEqual(arguments.normalize_argv([]), [])

    def test_normalized_argv_parses(self):
        with mock.patch.object(arguments, "file_path_type_check", side_effect=lambda value: value):
            parser = arguments.configure_parser()
            args = parser.parse_args(arguments.normalize_argv(["--debug", "a.zip"]))
        self.assertEqual(args.command, "extract")
        self.assertTrue(args.debug)


class ConfigureSettingsTest(unittest.TestCase):
    def test_fills_only_the_options_a_subcommand_has(self):
        config = mock.Mock()
        config.get.return_value = True
        args = argparse.Namespace(fast_check=None)  # like `identify`: no update_defaults

        arguments.configure_settings(args, config)

        self.assertTrue(args.fast_check)
        config.get.assert_called_once_with("settings", "fast_check", type=bool)
        self.assertFalse(hasattr(args, "open_output_folder"))


if __name__ == "__main__":
    unittest.main()
