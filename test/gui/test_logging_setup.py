import logging
import os
import shutil
import sys
import tempfile
import threading
import unittest
from logging.handlers import RotatingFileHandler
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "src"))
from gui import logging_setup  # noqa: E402


class LoggingSetupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.root_logger = logging.getLogger()
        self.before = (list(self.root_logger.handlers), self.root_logger.level,
                       sys.excepthook, threading.excepthook, logging_setup._path)
        self.addCleanup(self.restore)

    def restore(self):
        for handler in list(self.root_logger.handlers):
            if handler not in self.before[0]:
                self.root_logger.removeHandler(handler)
                handler.close()
        self.root_logger.setLevel(self.before[1])
        sys.excepthook, threading.excepthook, logging_setup._path = self.before[2:]
        shutil.rmtree(self.tmp, ignore_errors=True)

    def file_handlers(self):
        return [h for h in self.root_logger.handlers if isinstance(h, RotatingFileHandler)]

    def test_a_source_run_keeps_logging_to_the_console(self):
        self.assertIsNone(logging_setup.configure(self.tmp, frozen=False))
        self.assertEqual(self.file_handlers(), [])
        self.assertEqual(os.listdir(self.tmp), [])

    def test_the_frozen_exe_writes_errors_to_gui_log(self):
        path = logging_setup.configure(self.tmp, frozen=True)
        self.assertEqual(path, os.path.join(self.tmp, "gui.log"))
        self.assertEqual(logging_setup.log_path(), path)
        logging.error("something broke: %s", "архив")
        for handler in self.file_handlers():
            handler.flush()
        with open(path, encoding="utf-8") as handle:
            content = handle.read()
        self.assertIn("ERROR", content)
        self.assertIn("something broke: архив", content)

    def test_configuring_twice_adds_one_handler(self):
        logging_setup.configure(self.tmp, frozen=True)
        logging_setup.configure(self.tmp, frozen=True)
        self.assertEqual(len(self.file_handlers()), 1)

    def test_a_folder_that_cannot_be_written_is_not_fatal(self):
        blocker = os.path.join(self.tmp, "file-not-folder")
        with open(blocker, "w", encoding="utf-8"):
            pass
        with mock.patch.dict(os.environ, {"LOCALAPPDATA": ""}):
            self.assertIsNone(logging_setup.configure(blocker, frozen=True))
        self.assertEqual(self.file_handlers(), [])

    def test_a_read_only_install_folder_falls_back_to_local_app_data(self):
        blocker = os.path.join(self.tmp, "file-not-folder")
        with open(blocker, "w", encoding="utf-8"):
            pass
        local = os.path.join(self.tmp, "local")
        with mock.patch.dict(os.environ, {"LOCALAPPDATA": local}):
            path = logging_setup.configure(blocker, frozen=True)
        self.assertEqual(path, os.path.join(local, "magic-extractor", "gui.log"))

    def test_uncaught_exceptions_are_logged_in_the_main_thread_and_in_workers(self):
        path = logging_setup.configure(self.tmp, frozen=True)
        try:
            raise ValueError("main boom")
        except ValueError:
            sys.excepthook(*sys.exc_info())

        def worker():
            raise RuntimeError("worker boom")

        thread = threading.Thread(target=worker, name="job-worker")
        thread.start()
        thread.join()
        for handler in self.file_handlers():
            handler.flush()
        with open(path, encoding="utf-8") as handle:
            content = handle.read()
        self.assertIn("main boom", content)
        self.assertIn("Traceback", content)
        self.assertIn("worker boom", content)
        self.assertIn("job-worker", content)

    def test_a_fatal_error_is_shown_in_a_message_box_only_in_the_frozen_exe(self):
        with mock.patch.object(logging_setup, "_message_box") as box, self.assertLogs(level="CRITICAL"):
            with mock.patch.object(sys, "frozen", True, create=True):
                logging_setup.report_fatal("Magic Extractor", "could not start")
        box.assert_called_once()
        self.assertIn("could not start", box.call_args.args[1])
        with mock.patch.object(logging_setup, "_message_box") as box, self.assertLogs(level="CRITICAL"):
            logging_setup.report_fatal("Magic Extractor", "could not start")
        box.assert_not_called()


if __name__ == "__main__":
    unittest.main()
