"""QML bridge for the update check.

A separate QObject rather than another surface on AppController: the check
owns a worker thread and three user-facing outcomes; `bridge.py` has no room
for them under the module-size cap.

Threading shape: the check runs through `BackgroundJobs`, whose worker holds
only the service call and a `Future`, never the controller; the result is
delivered on the UI thread as `_resultReady`. `background.py` records why:
an earlier shape emitted from the worker through a closure over the
controller and crashed when a caller let go mid-check. Now dropping the
controller mid-check simply orphans the future.

The skip persistence and the launch/periodic timers live QML-side (the
application's settings already persist through `Qt.labs.settings`), so this
object is stateless between checks: the automatic check is handed the skipped
tag, the manual check ignores it by construction.
"""

from __future__ import annotations

from concurrent.futures import Future
from functools import partial

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from meridian.application.services.update_service import UpdateService
from meridian.ui.background import BackgroundJobs

__all__ = ["UpdateController"]


class UpdateController(QObject):
    updateAvailable = Signal(str, str, str, str)
    upToDate = Signal()
    checkFailed = Signal()

    _resultReady = Signal(object, bool)

    def __init__(self, service: UpdateService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = service
        self._jobs = BackgroundJobs("meridian-update-check", self)
        self._jobs.finished.connect(self._on_finished)
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
        self._jobs.start(partial(self._service.check, skipped_version), manual)

    @Slot(object, object)
    def _on_finished(self, outcome: Future, manual: object) -> None:
        # Any error in the check reads as unreachable.
        status = None if outcome.exception() else outcome.result()
        self._resultReady.emit(status, bool(manual))

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
