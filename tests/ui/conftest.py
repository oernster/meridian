"""A real QApplication for the UI tests.

Qt is never mocked here. One application instance is shared for the session
because a second one aborts the process.
"""

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    return QApplication.instance() or QApplication([])
