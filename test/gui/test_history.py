import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from gui import history


class HistoryTest(unittest.TestCase):
    def test_parse_empty(self):
        self.assertEqual(history.parse(""), [])
        self.assertEqual(history.parse(None), [])

    def test_parse_drops_empties(self):
        self.assertEqual(history.parse("a||b|"), ["a", "b"])

    def test_join_roundtrip(self):
        self.assertEqual(history.join(["a", "b"]), "a|b")
        self.assertEqual(history.parse(history.join(["a", "b"])), ["a", "b"])

    def test_push_prepends_and_dedupes(self):
        items = ["b", "c"]
        self.assertEqual(history.push(items, "a", 10), ["a", "b", "c"])
        self.assertEqual(history.push(["a", "b"], "b", 10), ["b", "a"])  # moved to front

    def test_push_caps(self):
        self.assertEqual(history.push(["a", "b", "c"], "d", 2), ["d", "a"])

    def test_push_ignores_blank(self):
        self.assertEqual(history.push(["a"], "  ", 10), ["a"])


if __name__ == "__main__":
    unittest.main()
