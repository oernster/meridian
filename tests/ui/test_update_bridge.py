"""UpdateController: cross-thread delivery and the three outcomes.

The worker thread emits an internal signal connected to a bound method of the
controller, so delivery is queued onto the UI thread. Each test therefore
spins the event loop until the outcome lands; that spin is the offscreen probe
proving the delivery, not just the logic.
"""

import time

from PySide6.QtCore import QObject, QUrl, Slot

from meridian.application.dto.update_info import UpdateStatus
from meridian.ui.update_bridge import UpdateController

_PROBE_TIMEOUT_SECONDS = 3.0


def _status(available=True, download_url="https://x/setup.exe", page_url="https://x/r"):
    return UpdateStatus(
        current="2.5.1",
        latest="v2.6.0",
        update_available=available,
        download_url=download_url,
        page_url=page_url,
    )


class FakeUpdateService:
    def __init__(self, status=None, exc=None):
        self._status = status
        self._exc = exc
        self.calls = []

    def check(self, skipped_version=None):
        self.calls.append(skipped_version)
        if self._exc is not None:
            raise self._exc
        return self._status


class Recorder:
    def __init__(self, controller):
        self.available = []
        self.up_to_date = 0
        self.failed = 0
        controller.updateAvailable.connect(lambda *args: self.available.append(args))
        controller.upToDate.connect(self._on_up_to_date)
        controller.checkFailed.connect(self._on_failed)

    def _on_up_to_date(self):
        self.up_to_date += 1

    def _on_failed(self):
        self.failed += 1

    def outcomes(self):
        return len(self.available) + self.up_to_date + self.failed


class DeliveryProbe(QObject):
    """Proves the queued delivery landed even when the outcome is silence.

    Connected to `_resultReady` after `_apply_result`, so its own queued event
    is posted (and therefore processed) after the controller's: once this has
    recorded, the silent path has definitely run.
    """

    def __init__(self):
        super().__init__()
        self.delivered = []

    @Slot(object, bool)
    def record(self, status, manual):
        self.delivered.append((status, manual))


def _spin_until(qapp, condition):
    deadline = time.monotonic() + _PROBE_TIMEOUT_SECONDS
    while not condition() and time.monotonic() < deadline:
        qapp.processEvents()
    assert condition(), "outcome never arrived on the UI thread"


class TestAutomaticCheck:
    def test_update_available_prompts(self, qapp):
        service = FakeUpdateService(_status())
        controller = UpdateController(service)
        recorder = Recorder(controller)
        controller.checkAutomatically("")
        _spin_until(qapp, lambda: recorder.outcomes() > 0)
        assert recorder.available == [
            ("v2.6.0", "2.5.1", "https://x/setup.exe", "https://x/r")
        ]
        assert service.calls == [None]

    def test_skipped_tag_is_passed_through(self, qapp):
        service = FakeUpdateService(_status(available=False))
        controller = UpdateController(service)
        controller.checkAutomatically("v2.6.0")
        _spin_until(qapp, lambda: bool(service.calls))
        assert service.calls == ["v2.6.0"]

    def test_up_to_date_is_silent(self, qapp):
        service = FakeUpdateService(_status(available=False))
        controller = UpdateController(service)
        recorder = Recorder(controller)
        probe = DeliveryProbe()
        controller._resultReady.connect(probe.record)
        controller.checkAutomatically("")
        _spin_until(qapp, lambda: bool(probe.delivered))
        assert recorder.outcomes() == 0

    def test_unreachable_is_silent(self, qapp):
        service = FakeUpdateService(None)
        controller = UpdateController(service)
        recorder = Recorder(controller)
        probe = DeliveryProbe()
        controller._resultReady.connect(probe.record)
        controller.checkAutomatically("")
        _spin_until(qapp, lambda: bool(probe.delivered))
        assert recorder.outcomes() == 0

    def test_missing_urls_become_empty_strings(self, qapp):
        service = FakeUpdateService(_status(download_url=None, page_url=None))
        controller = UpdateController(service)
        recorder = Recorder(controller)
        controller.checkAutomatically("")
        _spin_until(qapp, lambda: recorder.outcomes() > 0)
        assert recorder.available == [("v2.6.0", "2.5.1", "", "")]


class TestManualCheck:
    def test_update_available_prompts(self, qapp):
        service = FakeUpdateService(_status())
        controller = UpdateController(service)
        recorder = Recorder(controller)
        controller.checkManually()
        _spin_until(qapp, lambda: recorder.outcomes() > 0)
        assert len(recorder.available) == 1

    def test_manual_ignores_the_skip_by_construction(self, qapp):
        service = FakeUpdateService(_status())
        controller = UpdateController(service)
        controller.checkManually()
        _spin_until(qapp, lambda: bool(service.calls))
        assert service.calls == [None]

    def test_up_to_date_is_reported(self, qapp):
        service = FakeUpdateService(_status(available=False))
        controller = UpdateController(service)
        recorder = Recorder(controller)
        controller.checkManually()
        _spin_until(qapp, lambda: recorder.outcomes() > 0)
        assert recorder.up_to_date == 1

    def test_unreachable_is_reported(self, qapp):
        service = FakeUpdateService(None)
        controller = UpdateController(service)
        recorder = Recorder(controller)
        controller.checkManually()
        _spin_until(qapp, lambda: recorder.outcomes() > 0)
        assert recorder.failed == 1

    def test_service_exception_reads_as_unreachable(self, qapp):
        service = FakeUpdateService(exc=RuntimeError("boom"))
        controller = UpdateController(service)
        recorder = Recorder(controller)
        controller.checkManually()
        _spin_until(qapp, lambda: recorder.outcomes() > 0)
        assert recorder.failed == 1


class TestOpenDownload:
    def test_opens_the_url(self, qapp, monkeypatch):
        opened = []
        monkeypatch.setattr(
            "meridian.ui.update_bridge.QDesktopServices.openUrl",
            lambda url: opened.append(url) or True,
        )
        controller = UpdateController(FakeUpdateService())
        controller.openDownload("https://x/setup.exe")
        assert opened == [QUrl("https://x/setup.exe")]
