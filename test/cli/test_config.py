import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "cli"))
import config


class ConfigTest(unittest.TestCase):
    def setUp(self):
        # Config is a singleton (Config._instance); reset it so each test gets a
        # fresh instance bound to its own temp .ini and cases stay independent.
        config.Config._instance = None
        fd, self.path = tempfile.mkstemp(suffix=".ini")
        os.close(fd)
        with open(self.path, "w") as ini:
            ini.write(
                "[settings]\n"
                "flag_on = True\n"
                "flag_off = no\n"
                "count = 42\n"
                "name = hello\n"
            )

    def tearDown(self):
        config.Config._instance = None
        if os.path.exists(self.path):
            os.remove(self.path)

    def _config(self):
        return config.Config(self.path)

    # --- singleton ------------------------------------------------------- #
    def test_is_singleton(self):
        first = self._config()
        second = config.Config("ignored-path-because-already-created.ini")
        self.assertIs(first, second)

    # --- get with type casting ------------------------------------------ #
    def test_get_bool_true(self):
        self.assertIs(self._config().get("settings", "flag_on", type=bool), True)

    def test_get_bool_false(self):
        self.assertIs(self._config().get("settings", "flag_off", type=bool), False)

    def test_get_int_casts(self):
        value = self._config().get("settings", "count", type=int)
        self.assertEqual(value, 42)
        self.assertIsInstance(value, int)

    def test_get_plain_string(self):
        self.assertEqual(self._config().get("settings", "name"), "hello")

    # --- get fallback ---------------------------------------------------- #
    def test_get_missing_key_returns_fallback(self):
        self.assertEqual(
            self._config().get("settings", "nope", fallback="dflt"), "dflt"
        )

    def test_get_missing_section_returns_fallback(self):
        self.assertEqual(
            self._config().get("no-section", "x", fallback="dflt"), "dflt"
        )

    def test_missing_key_without_fallback_returns_none(self):
        self.assertIsNone(self._config().get("settings", "nope"))

    # --- set / save round-trip ------------------------------------------ #
    def test_set_updates_in_memory(self):
        cfg = self._config()
        cfg.set("settings", "name", "world")
        self.assertEqual(cfg.get("settings", "name"), "world")

    def test_set_creates_new_section(self):
        # Regression: set() used to KeyError on a section absent at load time.
        cfg = self._config()
        cfg.set("brandnew", "k", "v")
        cfg.save()
        config.Config._instance = None
        self.assertEqual(config.Config(self.path).get("brandnew", "k"), "v")

    def test_save_round_trip_persists_to_disk(self):
        cfg = self._config()
        cfg.set("settings", "count", 99)
        cfg.set("settings", "name", "persisted")
        cfg.save()

        # Reload from disk via a fresh singleton to prove it was written out.
        config.Config._instance = None
        reloaded = config.Config(self.path)
        self.assertEqual(reloaded.get("settings", "count", type=int), 99)
        self.assertEqual(reloaded.get("settings", "name"), "persisted")


if __name__ == "__main__":
    unittest.main()
