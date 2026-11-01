"""Closing the window while a run is going must never freeze it (B3).

The worker is a stand-in thread object: ``join`` must never be called from the UI
thread (it used to block for up to 10 s, which Windows reports as "Not responding"),
and the window is destroyed from an after() poll once the worker has stopped.
"""
import time
import unittest
from unittest import mock

import tkinter as tk

from test_app import AppTestCase, app_module


class FakeWorker:
    """is_alive() is True for the first ``alive_polls`` calls, then False."""

    def __init__(self, alive_polls):
        self.alive_polls = alive_polls
        self.polls = 0

    def is_alive(self):
        self.polls += 1
        return self.polls <= self.alive_polls

    def join(self, timeout=None):
        raise AssertionError("the UI thread must never join the worker")


class CloseWhileRunningTest(AppTestCase):
    def start_run(self, worker):
        self.app._set_running(True)
        self.app.worker = worker

    def destroyed(self):
        try:
            return not self.root.winfo_exists()
        except tk.TclError:
            return True

    def pump_until_destroyed(self, timeout=5):
        deadline = time.monotonic() + timeout
        while not self.destroyed() and time.monotonic() < deadline:
            try:
                self.root.update()
            except tk.TclError:
                break
            time.sleep(0.01)
        return self.destroyed()

    def test_close_returns_at_once_and_destroys_once_the_worker_stopped(self):
        self.start_run(FakeWorker(alive_polls=3))
        app_module.dialogs.confirm.return_value = True
        self.app._on_close()
        self.assertTrue(self.app.cancel_flag.is_set())
        self.assertFalse(self.destroyed(), "must wait for the worker, without blocking")
        self.assertTrue(self.pump_until_destroyed())

    def test_close_gives_up_on_a_worker_that_never_stops(self):
        self.start_run(FakeWorker(alive_polls=10 ** 9))
        app_module.dialogs.confirm.return_value = True
        with mock.patch.object(app_module.ExtractorApp, "CLOSE_TIMEOUT", 0.15):
            self.app._on_close()
            self.assertTrue(self.pump_until_destroyed(timeout=3))

    def test_a_second_close_request_while_closing_is_ignored(self):
        self.start_run(FakeWorker(alive_polls=5))
        app_module.dialogs.confirm.return_value = True
        self.app._on_close()
        self.app._on_close()
        self.assertEqual(app_module.dialogs.confirm.call_count, 1)
        self.assertTrue(self.pump_until_destroyed())

    def test_no_new_run_starts_while_closing(self):
        self.start_run(FakeWorker(alive_polls=5))
        app_module.dialogs.confirm.return_value = True
        self.app._on_close()
        self.app.source.set("a.zip")
        with mock.patch.object(self.app, "_run_jobs") as run_jobs:
            self.app._on_ok()
            self.app._on_batch()
        run_jobs.assert_not_called()
        self.assertTrue(self.pump_until_destroyed())

    def test_refusing_the_prompt_keeps_the_run_and_the_window(self):
        self.start_run(FakeWorker(alive_polls=1))
        app_module.dialogs.confirm.return_value = False
        self.app._on_close()
        self.assertFalse(self.app.cancel_flag.is_set())
        self.assertFalse(self.destroyed())
        self.app._set_running(False)

    def test_an_idle_window_closes_immediately_and_saves_the_settings(self):
        with mock.patch.object(self.app.settings, "save") as save:
            self.app._on_close()
        save.assert_called_once()
        self.assertTrue(self.destroyed())


if __name__ == "__main__":
    unittest.main()
