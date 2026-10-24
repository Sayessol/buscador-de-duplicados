"""The thread + queue + polling helper the interface uses for every long task.

It needs no window: the "after" of a widget is replaced by a scheduler the test drives by hand.
"""

import logging
import time

import pytest

from duplicate_finder.presentation.background_job import BackgroundJob


class Scheduler:
    """Stands in for `widget.after`: keeps the callbacks until the test runs them."""

    def __init__(self):
        self.pending = []

    def __call__(self, _ms, callback):
        self.pending.append(callback)

    def run_until_idle(self, timeout=5.0):
        end = time.time() + timeout
        while self.pending and time.time() < end:
            callbacks, self.pending = self.pending, []
            for callback in callbacks:
                callback()
            time.sleep(0.005)
        assert not self.pending, "the job did not finish"


class Cancelled(Exception):
    pass


@pytest.fixture
def events():
    return []


@pytest.fixture
def scheduler():
    return Scheduler()


def _job(scheduler, events):
    return BackgroundJob(
        scheduler,
        on_progress=lambda value: events.append(("progress", value)),
        on_done=lambda result: events.append(("done", result)),
        on_error=lambda error: events.append(("error", type(error).__name__)),
        on_cancelled=lambda: events.append(("cancelled", None)),
        cancelled_exceptions=(Cancelled,))


def test_progress_arrives_in_order_and_then_the_result(scheduler, events):
    job = _job(scheduler, events)

    def work(report):
        for i in (1, 2, 3):
            report(i)
        return "result"

    job.start(work, what="Counting")
    scheduler.run_until_idle()

    assert events == [("progress", 1), ("progress", 2), ("progress", 3), ("done", "result")]
    assert not job.running


def test_a_cancelled_task_ends_with_the_cancelled_callback(scheduler, events):
    job = _job(scheduler, events)

    def work(_report):
        raise Cancelled()

    job.start(work, what="Counting")
    scheduler.run_until_idle()

    assert events == [("cancelled", None)]


def test_a_failing_task_is_logged_with_its_name_and_reported(scheduler, events, caplog):
    job = _job(scheduler, events)

    def work(_report):
        raise KeyError("boom")

    with caplog.at_level(logging.ERROR):
        job.start(work, what="Scan of C:\\photos")
        scheduler.run_until_idle()

    assert events == [("error", "KeyError")]
    assert "Scan of C:\\photos failed" in caplog.text and "KeyError" in caplog.text


def test_the_same_job_can_run_again(scheduler, events):
    job = _job(scheduler, events)

    job.start(lambda _report: 1, what="First")
    scheduler.run_until_idle()
    job.start(lambda _report: 2, what="Second")
    scheduler.run_until_idle()

    assert events == [("done", 1), ("done", 2)]
