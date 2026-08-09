"""Background operation runner for the installer UI."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Callable, Optional

from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt

from installer.ops.errors import AppRunningError, InstallerOperationError

import logging

ProgressCb = Callable[[str], None]


@dataclass(frozen=True, slots=True)
class OperationResult:
    ok: bool
    message: str = ""


class OperationWorker(QObject):
    progress = Signal(object)
    finished = Signal(object)
    appRunning = Signal(str)

    def __init__(
        self,
        fn: Callable[..., None],
        *,
        kwargs: dict,
        cancel_event: threading.Event,
    ) -> None:
        super().__init__()
        self._fn = fn
        self._kwargs = dict(kwargs)
        self._cancel_event = cancel_event

    def run(self) -> None:
        logger = logging.getLogger("installer.worker")

        # COM is needed on this thread only so `create_shortcut` can run here.
        # If it will not initialise, the operation still proceeds and the
        # shortcut step raises its own specific error, which is a far better
        # message than one about COM apartments. `pythoncom` is reset to None
        # so the matching CoUninitialize below is skipped.
        pythoncom = None
        try:
            import pythoncom as _pythoncom  # type: ignore

            pythoncom = _pythoncom
            pythoncom.CoInitialize()
        except Exception:
            pythoncom = None

        try:
            logger.info(
                "Operation start: %s", getattr(self._fn, "__name__", str(self._fn))
            )
            self._kwargs.setdefault("cancel_event", self._cancel_event)
            self._kwargs.setdefault("progress", self._emit_progress)
            self._fn(**self._kwargs)
            logger.info("Operation finished OK")
            self.finished.emit(OperationResult(ok=True))
        except AppRunningError as exc:
            logger.warning("Operation blocked: app running: %s", exc)
            self.appRunning.emit(str(exc) or "Application is running")
            self.finished.emit(OperationResult(ok=False, message="app_running"))
        except InstallerOperationError as exc:
            logger.exception("Operation failed (expected): %s", exc)
            self.finished.emit(OperationResult(ok=False, message=str(exc)))
        except Exception as exc:
            # The backstop for this thread. Nothing is being hidden: the
            # traceback is logged and the failure is reported to the interface
            # as a result. It exists because an exception escaping here would
            # end the thread without ever emitting `finished`, leaving the
            # window stuck on "Working..." with no error and no way forward.
            logger.exception("Operation failed (unexpected): %s", exc)
            self.finished.emit(OperationResult(ok=False, message=repr(exc)))
        finally:
            self._emit_progress("")
            # Balancing CoInitialize as the thread ends. A failure here would
            # leak one apartment from a process that is about to exit, and
            # must not displace the result already emitted above.
            try:
                if pythoncom is not None:
                    pythoncom.CoUninitialize()
            except Exception:
                pass

    def _emit_progress(self, payload) -> None:  # noqa: ANN001
        self.progress.emit(payload)


class _GuiRelay(QObject):
    def __init__(
        self,
        *,
        on_progress: Callable[[str], None],
        on_finished: Callable[[OperationResult], None],
        on_app_running: Callable[[str], None],
    ) -> None:
        super().__init__()
        self._on_progress = on_progress
        self._on_finished = on_finished
        self._on_app_running = on_app_running
        self._result: OperationResult | None = None

    @Slot(object)
    def handle_progress(self, payload) -> None:  # noqa: ANN001
        self._on_progress(payload)

    @Slot(str)
    def handle_app_running(self, msg: str) -> None:
        self._on_app_running(msg)

    @Slot(object)
    def store_result(self, result) -> None:  # noqa: ANN001
        # Plain attribute assignment, which cannot raise. This carried a
        # try/except whose fallback was unreachable; the real "no result"
        # case is a `finished` that never arrives, and `notify_finished`
        # below already covers it by checking for None.
        self._result = result

    @Slot()
    def notify_finished(self) -> None:
        result = self._result
        if result is None:
            result = OperationResult(
                ok=False, message="Operation did not return a result"
            )
        self._on_finished(result)
        self.deleteLater()


class OperationController:
    def __init__(self) -> None:
        self._thread: Optional[QThread] = None
        self._worker: Optional[OperationWorker] = None
        self._relay: Optional[_GuiRelay] = None
        self._cancel_event = threading.Event()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.isRunning()

    def wait(self, timeout_ms: int) -> bool:
        if self._thread is None:
            return True
        return bool(self._thread.wait(timeout_ms))

    def force_stop(self, timeout_ms: int = 2000) -> None:
        self.cancel()
        if self._thread is None:
            return
        self._thread.quit()
        if not self._thread.wait(timeout_ms):
            # Last resort on a thread that ignored `quit`. Terminating one is
            # allowed to fail, and if it does there is nothing further to try:
            # the process is closing, and blocking the close to report an
            # unkillable background thread helps nobody. Both waits are
            # bounded so this can never become the shutdown that hangs.
            try:
                self._thread.terminate()
                self._thread.wait(500)
            except Exception:
                return

    def cancel(self) -> None:
        self._cancel_event.set()

    def start(
        self,
        fn: Callable[..., None],
        *,
        kwargs: dict,
        on_progress: Callable[[str], None],
        on_finished: Callable[[OperationResult], None],
        on_app_running: Callable[[str], None],
    ) -> None:
        if self.is_running:
            return

        self._cancel_event = threading.Event()

        thread = QThread()
        worker = OperationWorker(fn, kwargs=kwargs, cancel_event=self._cancel_event)
        worker.moveToThread(thread)

        relay = _GuiRelay(
            on_progress=on_progress,
            on_finished=on_finished,
            on_app_running=on_app_running,
        )
        self._relay = relay

        worker.progress.connect(relay.handle_progress, Qt.QueuedConnection)
        worker.appRunning.connect(relay.handle_app_running, Qt.QueuedConnection)

        thread.started.connect(worker.run, Qt.QueuedConnection)

        worker.finished.connect(relay.store_result, Qt.QueuedConnection)
        worker.finished.connect(thread.quit, Qt.QueuedConnection)
        worker.finished.connect(worker.deleteLater)

        def _on_thread_finished() -> None:
            try:
                relay.notify_finished()
            finally:
                self._thread = None
                self._worker = None
                self._relay = None
                # The controller's references are already cleared in the
                # `finally` above, so the thread is collectable either way.
                # Scheduling the C++ side for deletion can fail if it has
                # already gone, which is the outcome being asked for.
                try:
                    thread.deleteLater()
                except Exception:
                    pass

        thread.finished.connect(_on_thread_finished, Qt.QueuedConnection)

        self._thread = thread
        self._worker = worker
        thread.start()
