"""QML bridge for the update check.

A separate QObject rather than another surface on AppController: the check
owns a worker thread and three user-facing outcomes, and `bridge.py` has no
room for them under the module-size cap.

Threading shape: the worker thread emits `_resultReady`, which is connected to
a bound method of this controller. The controller lives on the UI thread, so
delivery is a queued connection and the slot runs on the UI thread; a signal
connected to a bare callable would run in the worker's thread instead.

The skip persistence and the launch/periodic timers live QML-side (the
application's settings already persist through `Qt.labs.settings`), so this
object is stateless between calls: the automatic check is handed the skipped
tag, the manual check ignores it by construction.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices

from meridian.application.services.update_service import UpdateService

__all__ = ["UpdateController"]


class UpdateController(QObject):
    updateAvailable = Signal(str, str, str, str)
    upToDate = Signal()
    checkFailed = Signal()

    _resultReady = Signal(object, bool)

    def __init__(self, service: UpdateService, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = service
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
        def _run() -> None:
            try:
                status = self._service.check(skipped_version)
            except Exception:  # noqa: BLE001 (any error reads as unreachable)
                status = None
            self._resultReady.emit(status, manual)

        threading.Thread(target=_run, daemon=True, name="meridian-update-check").start()

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
