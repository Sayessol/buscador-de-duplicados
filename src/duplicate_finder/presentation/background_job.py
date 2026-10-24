"""Runs a long task in a thread and hands its progress and result to the main thread.

This is the pattern the app uses for every long task (scan, analyze, move, gather).
Tkinter is not thread-safe: only the main thread can touch widgets. So:

* the heavy work runs in a separate thread,
* that thread does NOT touch the interface: it only puts messages in a queue,
* the interface polls the queue every 100 ms from the main thread, takes the messages out and
  updates the widgets.

This way the window does not freeze and the task can be cancelled halfway.
"""

import logging
import queue
import threading
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)

_POLL_MS = 100


class BackgroundJob:
    def __init__(
        self,
        schedule: Callable[[int, Callable[[], None]], object],
        on_progress: Callable[[Any], None],
        on_done: Callable[[Any], None],
        on_error: Callable[[Exception], None],
        on_cancelled: Callable[[], None] | None = None,
        cancelled_exceptions: tuple[type[BaseException], ...] = (),
    ) -> None:
        """`schedule(ms, callback)` is the `after` of a widget: it runs `callback` in the main
        thread. The `on_*` callbacks always run in the main thread. A task that raises one of
        `cancelled_exceptions` ends with `on_cancelled`; any other exception is logged with
        its traceback and ends with `on_error`."""
        self._schedule = schedule
        self._on_progress = on_progress
        self._on_done = on_done
        self._on_error = on_error
        self._on_cancelled = on_cancelled
        self._cancelled_exceptions = cancelled_exceptions
        self._thread: threading.Thread | None = None
        self._messages: queue.Queue[tuple[str, Any]] = queue.Queue()

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self, work: Callable[[Callable[[Any], None]], Any], what: str) -> None:
        """Runs `work(report)` in a thread. `report(value)` sends progress to `on_progress`;
        what `work` returns goes to `on_done`. `what` names the task in the log if it fails."""
        messages: queue.Queue[tuple[str, Any]] = queue.Queue()
        self._messages = messages

        def run() -> None:
            try:
                result = work(lambda value: messages.put(("progress", value)))
                messages.put(("done", result))
            except self._cancelled_exceptions:
                messages.put(("cancelled", None))
            except Exception as e:  # any failure is logged and shown
                log.exception("%s failed", what)
                messages.put(("error", e))

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
        self._schedule(_POLL_MS, self._poll)

    def _poll(self) -> None:
        """Main thread: empties the queue and acts on each message. It reschedules itself until
        "done", "cancelled" or "error" arrives."""
        try:
            while True:
                kind, datum = self._messages.get_nowait()
                if kind == "progress":
                    self._on_progress(datum)
                elif kind == "done":
                    self._on_done(datum)
                    return
                elif kind == "cancelled":
                    if self._on_cancelled is not None:
                        self._on_cancelled()
                    return
                else:
                    self._on_error(datum)
                    return
        except queue.Empty:
            pass
        self._schedule(_POLL_MS, self._poll)
