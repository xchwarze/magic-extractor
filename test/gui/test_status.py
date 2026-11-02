import os
import sys
import tkinter as tk
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))
from gui import theme  # noqa: E402
from gui.status import StatusLine, fit, job_status, run_summary  # noqa: E402
from gui.surfaces import surface  # noqa: E402


def results(*codes, mode="extract"):
    return [(mode, f"C:\\in\\file{index}.zip", code) for index, code in enumerate(codes, 1)]


class JobStatusTest(unittest.TestCase):
    def test_a_single_job_names_its_file(self):
        self.assertEqual(job_status(1, 1, "extract", "C:\\in\\foo.zip"), "Extracting foo.zip")
        self.assertEqual(job_status(1, 1, "scan", "C:\\in\\foo.zip"), "Scanning foo.zip")
        self.assertEqual(job_status(1, 1, "carve", "/in/foo.bin"), "Carving foo.bin")

    def test_a_batch_shows_the_position_and_the_file(self):
        self.assertIn("2 of 5: foo.zip", job_status(2, 5, "extract", "C:\\in\\foo.zip"))

    def test_a_trailing_separator_does_not_empty_the_name(self):
        self.assertEqual(job_status(1, 1, "extract", "C:\\in\\folder\\"), "Extracting folder")


class RunSummaryTest(unittest.TestCase):
    def test_counts_of_a_finished_batch(self):
        self.assertEqual(run_summary(results(0, 0, 1, 0, 0), 5), ("4 extracted, 1 failed", "warning"))

    def test_a_clean_batch_is_info(self):
        self.assertEqual(run_summary(results(0, 0, 0), 3), ("3 extracted", "info"))

    def test_a_batch_where_everything_failed_is_an_error(self):
        self.assertEqual(run_summary(results(1, 2), 2), ("2 failed", "error"))

    def test_one_job_says_which_file(self):
        self.assertEqual(run_summary(results(0), 1), ("Extracted: file1.zip", "info"))
        self.assertEqual(run_summary(results(2), 1), ("Failed: file1.zip (exit code 2)", "error"))

    def test_a_job_that_could_not_start_has_no_exit_code_to_show(self):
        self.assertEqual(run_summary(results(-1), 1), ("Failed: file1.zip", "error"))

    def test_scan_and_carve_use_their_own_words(self):
        self.assertEqual(run_summary(results(0, 1, mode="scan"), 2), ("1 identified, 1 not identified", "warning"))
        self.assertEqual(run_summary(results(1, mode="scan"), 1), ("Not identified: file1.zip (exit code 1)", "warning"))
        self.assertEqual(run_summary(results(0, 0, mode="carve"), 2), ("2 carved", "info"))

    def test_a_mixed_batch_uses_neutral_words(self):
        mixed = [("extract", "a.zip", 0), ("scan", "b.zip", 1)]
        self.assertEqual(run_summary(mixed, 2), ("1 succeeded, 1 failed", "warning"))

    def test_cancelling_counts_the_interrupted_job_as_not_run_not_failed(self):
        self.assertEqual(run_summary(results(0, -1), 3, cancelled=True), ("Cancelled: 1 extracted, 2 not run", "info"))

    def test_cancelling_a_single_job(self):
        self.assertEqual(run_summary(results(-1), 1, cancelled=True), ("Cancelled", "info"))

    def test_a_job_that_failed_before_the_cancel_is_still_a_failure(self):
        self.assertEqual(run_summary(results(1, -1), 3, cancelled=True),
                         ("Cancelled: 1 failed, 2 not run", "info"))

    def test_nothing_ran(self):
        self.assertEqual(run_summary([], 0), ("Nothing to do", "info"))


class FitTest(unittest.TestCase):
    def measure(self, text):
        return len(text) * 10

    def test_short_text_is_untouched(self):
        self.assertEqual(fit("abc", 100, self.measure), "abc")

    def test_long_text_ends_in_an_ellipsis_that_still_fits(self):
        shown = fit("abcdefghijklmnopqrstuvwxyz", 100, self.measure)
        self.assertTrue(shown.endswith("\u2026"))
        self.assertLessEqual(self.measure(shown), 100)
        self.assertGreater(len(shown), 5)

    def test_no_room_gives_just_the_ellipsis(self):
        self.assertEqual(fit("abcdef", 5, self.measure), "\u2026")


class StatusLineTest(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"no display for Tk: {exc}")
        self.addCleanup(self.root.destroy)
        self.root.geometry("300x80+0+0")
        self.root.withdraw()
        theme.apply(self.root, "dark")  # theme.current() reads the applied sv-ttk theme
        self.line = StatusLine(self.root)
        self.line.label.pack(fill="x")

    def test_text_is_one_line(self):
        self.line.set("first\nsecond   third")
        self.assertEqual(self.line.full, "first second third")

    def test_a_long_message_is_cut_and_its_full_text_is_the_tooltip(self):
        message = "x" * 400
        self.line.label.update_idletasks()
        self.line.label.configure(width=1)
        # an unmapped label reports width 1, so give it a real one the way a mapped one has it
        self.line.label.winfo_width = lambda: 120
        self.line.set(message)
        shown = str(self.line.label.cget("text"))
        self.assertTrue(shown.endswith("\u2026"))
        self.assertLess(len(shown), len(message))
        self.assertEqual(self.line._tip.text, message)

    def test_a_message_that_fits_has_no_tooltip(self):
        self.line.label.winfo_width = lambda: 5000
        self.line.set("Ready")
        self.assertEqual(str(self.line.label.cget("text")), "Ready")
        self.assertEqual(self.line._tip.text, "")

    def test_the_label_does_not_widen_the_window(self):
        self.assertEqual(int(self.line.label.cget("width")), 1)

    def test_warning_and_error_have_their_own_colours_and_info_resets_to_the_style(self):
        mode = theme.current(self.line.label)
        self.line.set("careful", "warning")
        self.assertEqual(str(self.line.label.cget("foreground")), theme.alert_colors(mode)["fg"])
        self.line.set("broken", "error")
        self.assertEqual(str(self.line.label.cget("foreground")), surface(mode)["error"])
        self.line.set("fine", "info")
        self.assertEqual(str(self.line.label.cget("foreground")), "")


def luminance(color):
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    channels = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]


def contrast(foreground, background):
    high, low = sorted((luminance(foreground), luminance(background)), reverse=True)
    return (high + 0.05) / (low + 0.05)


class ContrastTest(unittest.TestCase):
    # sv-ttk's window backgrounds, which the status line sits on
    SV_BG = {"dark": "#1c1c1c", "light": "#fafafa"}

    def test_status_colours_are_readable_in_both_themes(self):
        for mode in ("dark", "light"):
            for name, color in (("warning", theme.alert_colors(mode)["fg"]), ("error", surface(mode)["error"])):
                for where, background in (("sv-ttk", self.SV_BG[mode]), ("log", theme.palette(mode)["bg"])):
                    self.assertGreaterEqual(contrast(color, background), 4.5, (mode, name, where))

    def test_popup_text_colours_are_readable_on_the_popup_surface(self):
        for mode in ("dark", "light"):
            background = theme.palette(mode)["bg"]
            self.assertGreaterEqual(contrast(surface(mode)["disabled"], background), 4.5, mode)
            self.assertGreaterEqual(contrast(theme.palette(mode)["fg"], surface(mode)["hover"]), 4.5, mode)
            for where in (background, surface(mode)["hover"]):  # shortcut hints, also on a hovered row
                self.assertGreaterEqual(contrast(surface(mode)["muted"], where), 4.5, (mode, where))


if __name__ == "__main__":
    unittest.main()
