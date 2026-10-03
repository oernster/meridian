"""The window's import report: every import ends in a dialog that says what it did.

Driven through the real `main.qml` against the stub controller: the stub emits
what the bridge would; what is asserted is the dialog that opened, its title
and its message.
"""

from PySide6.QtCore import QObject

from tests.ui.window_stub import StubController, load_main_window


def _report_dialog(qapp, message, complete):
    controller = StubController()
    engine, component, window = load_main_window(controller)
    dialog = window.findChild(QObject, "importReportDialog")
    assert dialog.property("visible") is False
    controller.importReported.emit(message, complete)
    qapp.processEvents()
    return engine, component, dialog


class TestImportReport:
    def test_a_whole_import_reports_under_its_own_title(self, qapp):
        _engine, _component, dialog = _report_dialog(qapp, "Imported 2 feeds.", True)
        assert dialog.property("visible") is True
        assert dialog.property("title") == "Import Feeds"
        assert dialog.property("message") == "Imported 2 feeds."

    def test_a_partial_import_says_it_is_incomplete(self, qapp):
        message = "Imported 1 feed.\n1 feed could not be imported:\nhttps://x: bad"
        _engine, _component, dialog = _report_dialog(qapp, message, False)
        assert dialog.property("visible") is True
        assert dialog.property("title") == "Import Incomplete"
        assert dialog.property("message") == message
