"""QML bridge for the update check.

A separate QObject rather than another surface on AppController: the check
owns a worker thread and three user-facing outcomes; `bridge.py` has no room
for them under the module-size cap.

Threading shape: the worker never touches the controller. It runs a module
function holding only the service and a `Future`, fills the future and exits.
The controller polls its pending futures with a timer it owns on the UI
thread, emitting `_resultReady` there. An earlier shape emitted from the
worker through a closure over the controller, which made the worker an owner:
a caller letting go mid-check left the worker to drop the last reference and
destroy the controller on the worker thread while the UI thread delivered to
it, which crashed the process (measured, 1 run in 120 outside the tests).
Now dropping the controller mid-check simply orphans the future.

The skip persistence and the launch/periodic timers live QML-side (the
application's settings already persist through `Qt.labs.settings`), so this
object is stateless between checks: the automatic check is handed the skipped
tag, the manual check ignores it by construction.
"""

from __future__ import annotations

import threading
from concurrent.futures import Future

from PySide6.QtCore import QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from meridian.application.services.update_service import UpdateService

__all__ = ["UpdateController"]

# How often the UI thread looks for a finished check. A check is a daily
# network call, so a fraction of a second of delivery latency costs nothing.
_POLL_INTERVAL_MS = 50


def _run_check(
    service: UpdateService, skipped_version: str | None, outcome: Future
) -> None:
    """The worker's whole job; it holds the service and the future, no QObject."""
    try:
        status = service.check(skipped_version)
    except Exception:  # noqa: BLE001 (any error reads as unreachable)
        status = None
    outcome.set_result(status)


class UpdateController(QObject):
    updateAvailable = Signal(str, str, str, str)
    upToDate = Signal()
    checkFailed = Signal()

    _resultReady = Signal(object, bool)

    def __init__(self, service: UpdateService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._pending: list[tuple[Future, bool]] = []
        self._poll = QTimer(self)
        self._poll.setInterval(_POLL_INTERVAL_MS)
        self._poll.timeout.connect(self._collect)
        self._resultReady.connect(self._apply_result)

    @Slot(str)
    def checkAutomatically(self, skipped_version: str) -> None:
        self._start_check(skipped_version or None, manual=False)

    @Slot()
    def checkManually(self) -> None:
        self._start_check(None, manual=True)

    @Slot(str)
    def openDownload(self, url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))

    def _start_check(self, skipped_version: str | None, manual: bool) -> None:
        outcome: Future = Future()
        threading.Thread(
            target=_run_check,
            args=(self._service, skipped_version, outcome),
            daemon=True,
            name="meridian-update-check",
        ).start()
        self._pending.append((outcome, manual))
        self._poll.start()

    @Slot()
    def _collect(self) -> None:
        # One reading of each future: a check finishing between two readings
        # would otherwise land in neither list and be lost. The pending list is
        # settled before emitting, since a slot reacting to a result may start
        # another check, which must not be dropped from it.
        finished: list[tuple[Future, bool]] = []
        waiting: list[tuple[Future, bool]] = []
        for entry in self._pending:
            (finished if entry[0].done() else waiting).append(entry)
        self._pending = waiting
        if not self._pending:
            self._poll.stop()
        for outcome, manual in finished:
            self._resultReady.emit(outcome.result(), manual)

    @Slot(object, bool)
    def _apply_result(self, status: object, manual: bool) -> None:
        if status is None:
            if manual:
                self.checkFailed.emit()
            return
        if status.update_available:
            self.updateAvailable.emit(
                status.latest,
                status.current,
                status.download_url or "",
                status.page_url or "",
            )
            return
        if manual:
            self.upToDate.emit()
