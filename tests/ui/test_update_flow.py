"""The window's update wiring: prompt, fallback, skip and the manual entry.

Driven through the real `main.qml` against the stub controllers, the same way
the removal dialogs are tested: the stub emits what the Python bridge would;
what is asserted is which dialog opened and which call reached the stub.
"""

from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from tests.ui.window_stub import (
    StubController,
    StubUpdateController,
    load_main_window,
)


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
