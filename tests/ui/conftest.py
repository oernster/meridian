"""A real QApplication for the UI tests.

Qt is never mocked here. One application instance is shared for the session
because a second one aborts the process.

Settings go to a folder of each test's own. The window persists its palette
through Qt.labs.settings, so a test that presses the toggle would otherwise
write it into the user's real preferences; every later window, in this run or
the next, would then start in whatever palette that test left behind.
"""

import pytest
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path):
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(
        QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path)
    )


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])
