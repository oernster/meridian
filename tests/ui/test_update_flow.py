"""The window's update wiring: prompt, fallback, skip and the manual entry.

Driven through the real `main.qml` against the stub controllers, the same way
the removal dialogs are tested: the stub emits what the Python bridge would;
what is asserted is which dialog opened and which call reached the stub.
`TestRealControllerInTheWindow` is the exception, joining the real
`UpdateController` to the real window.
"""

import time

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from meridian.application.dto.update_info import UpdateStatus
from meridian.ui.update_bridge import UpdateController
from tests.ui.window_stub import (
    StubController,
    StubUpdateController,
    load_main_window,
)

_ARRIVAL_TIMEOUT_SECONDS = 3.0


def _load(qapp):
    controller = StubController()
    update_stub = StubUpdateController()
    engine, component, window = load_main_window(controller, update_stub)
    return engine, component, window, update_stub


def _emit_update_available(update_stub, download_url, page_url):
    update_stub.updateAvailable.emit("v9.9.9", "0.0.0-test", download_url, page_url)


class TestUpdatePrompt:
    def test_update_available_opens_the_dialog_with_the_offer(self, qapp):
        _engine, _component, window, update_stub = _load(qapp)
        dialog = window.findChild(QObject, "updateDialog")
        _emit_update_available(update_stub, "https://x/setup.exe", "https://x/r")
        assert dialog.property("visible") is True
        assert dialog.property("latestVersion") == "v9.9.9"
        assert dialog.property("currentVersion") == "0.0.0-test"
        assert dialog.property("downloadUrl") == "https://x/setup.exe"
        assert dialog.property("pageUrl") == "https://x/r"

    def test_download_opens_the_asset_url(self, qapp):
        _engine, _component, window, update_stub = _load(qapp)
        dialog = window.findChild(QObject, "updateDialog")
        _emit_update_available(update_stub, "https://x/setup.exe", "https://x/r")
        dialog.metaObject().invokeMethod(dialog, "downloadRequested")
        assert update_stub.called("openDownload") == [
            ("openDownload", "https://x/setup.exe")
        ]

    def test_download_falls_back_to_the_release_page(self, qapp):
        _engine, _component, window, update_stub = _load(qapp)
        dialog = window.findChild(QObject, "updateDialog")
        _emit_update_available(update_stub, "", "https://x/r")
        dialog.metaObject().invokeMethod(dialog, "downloadRequested")
        assert update_stub.called("openDownload") == [("openDownload", "https://x/r")]

    def test_skip_persists_the_offered_tag(self, qapp):
        _engine, _component, window, update_stub = _load(qapp)
        dialog = window.findChild(QObject, "updateDialog")
        settings = window.findChild(QObject, "updateSettings")
        settings.setProperty("skippedVersion", "")
        _emit_update_available(update_stub, "https://x/setup.exe", "https://x/r")
        dialog.metaObject().invokeMethod(dialog, "skipRequested")
        assert settings.property("skippedVersion") == "v9.9.9"


class TestManualEntry:
    def test_help_menu_entry_triggers_the_manual_check(self, qapp):
        """Help, Down, Enter: the house Help > Check for Updates, by keys."""
        _engine, _component, window, update_stub = _load(qapp)
        QTest.qWaitForWindowExposed(window)
        button = window.findChild(QQuickItem, "helpBtn")
        button.forceActiveFocus(Qt.TabFocusReason)
        for key in (Qt.Key_Return, Qt.Key_Down, Qt.Key_Return):
            QTest.keyClick(window, key)
            QGuiApplication.processEvents()
        assert update_stub.called("checkManually") == [("checkManually",)]
        assert window.findChild(QObject, "helpMenu").property("visible") is False

    def test_about_no_longer_carries_the_check(self, qapp):
        _engine, _component, window, _update_stub = _load(qapp)
        assert window.findChild(QObject, "checkUpdatesBtn") is None


class _AnsweringService:
    def __init__(self, status):
        self._status = status

    def check(self, skipped_version=None):
        return self._status


def _ask_through_help(qapp, status):
    """The real UpdateController in the real window, asked by keys.

    Every other test here stands a stub in for the controller; this is the one
    place the real worker, its future and its polling timer drive the real
    dialogs.
    """
    real = UpdateController(_AnsweringService(status))
    engine, component, window = load_main_window(StubController(), real)
    QTest.qWaitForWindowExposed(window)
    window.findChild(QQuickItem, "helpBtn").forceActiveFocus(Qt.TabFocusReason)
    for key in (Qt.Key_Return, Qt.Key_Down, Qt.Key_Return):
        QTest.keyClick(window, key)
        QGuiApplication.processEvents()
    return engine, component, window


def _spin_until_visible(qapp, item):
    deadline = time.monotonic() + _ARRIVAL_TIMEOUT_SECONDS
    while item.property("visible") is not True and time.monotonic() < deadline:
        qapp.processEvents()
    return item.property("visible") is True


class TestRealControllerInTheWindow:
    def test_up_to_date_opens_the_info_dialog(self, qapp):
        status = UpdateStatus("2.9.0", "v2.9.0", False, None, "https://x/r")
        _engine, _component, window = _ask_through_help(qapp, status)
        info = window.findChild(QObject, "updateInfoDialog")
        assert _spin_until_visible(qapp, info)
        assert "latest version" in info.property("message")

    def test_newer_release_opens_the_prompt(self, qapp):
        status = UpdateStatus("2.9.0", "v3.0.0", True, "https://x/s.exe", "https://x/r")
        _engine, _component, window = _ask_through_help(qapp, status)
        prompt = window.findChild(QObject, "updateDialog")
        assert _spin_until_visible(qapp, prompt)
        assert prompt.property("latestVersion") == "v3.0.0"
        assert prompt.property("downloadUrl") == "https://x/s.exe"


class TestManualOutcomes:
    def test_up_to_date_reports(self, qapp):
        _engine, _component, window, update_stub = _load(qapp)
        info = window.findChild(QObject, "updateInfoDialog")
        update_stub.upToDate.emit()
        assert info.property("visible") is True
        assert "latest version" in info.property("message")

    def test_check_failed_reports(self, qapp):
        _engine, _component, window, update_stub = _load(qapp)
        info = window.findChild(QObject, "updateInfoDialog")
        update_stub.checkFailed.emit()
        assert info.property("visible") is True
        assert "could not reach GitHub" in info.property("message")
