"""Work run off the UI thread, its result delivered back onto it.

The one shape for it, used by the update check and the feed import. The worker
thread is handed only the job and a `Future`: never a QObject, so letting go
of the owner while a job runs cannot leave the worker to destroy it on the
wrong thread. The owner's `BackgroundJobs` polls its pending futures with a
timer on the UI thread and emits `finished` there, with the future and the
context the job was started with. An earlier update check emitted from the
worker through a closure over its controller and crashed (measured, 1 run in
120 outside the tests); that history is why this shape exists.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from concurrent.futures import Future

from PySide6.QtCore import QObject, QTimer, Signal, Slot

__all__ = ["POLL_INTERVAL_MS", "BackgroundJobs"]

# How often the UI thread looks for finished work. Both users are a network
# call or a file the user picked, so a fraction of a second costs nothing.
POLL_INTERVAL_MS = 50


def _run(job: Callable[[], object], outcome: Future) -> None:
    """The worker's whole job; it holds the job and the future, no QObject."""
    try:
        result = job()
    except Exception as exc:  # noqa: BLE001 (the owner decides what it means)
        outcome.set_exception(exc)
        return
    outcome.set_result(result)


class BackgroundJobs(QObject):
    finished = Signal(object, object)

    def __init__(self, thread_name: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread_name = thread_name
        self._pending: list[tuple[Future, object]] = []
        self._poll = QTimer(self)
        self._poll.setInterval(POLL_INTERVAL_MS)
        self._poll.timeout.connect(self._collect)

    def start(self, job: Callable[[], object], context: object = None) -> None:
        """Run `job` on a worker; `finished(future, context)` follows on this thread."""
        outcome: Future = Future()
        threading.Thread(
            target=_run, args=(job, outcome), daemon=True, name=self._thread_name
        ).start()
        self._pending.append((outcome, context))
        self._poll.start()

    @Slot()
    def _collect(self) -> None:
        # One reading of each future: a job finishing between two readings
        # would otherwise land in neither list and be lost. The pending list is
        # settled before emitting, since a slot reacting to a result may start
        # another job, which must not be dropped from it.
        finished: list[tuple[Future, object]] = []
        waiting: list[tuple[Future, object]] = []
        for entry in self._pending:
            (finished if entry[0].done() else waiting).append(entry)
        self._pending = waiting
        if not self._pending:
            self._poll.stop()
        for outcome, context in finished:
            self.finished.emit(outcome, context)
