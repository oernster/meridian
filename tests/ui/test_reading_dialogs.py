"""The dialogs of words to read open on Close; their page is never a pane.

The licences and the Guide share ReadingDialog. The page is words, not a
control, so three things hold for every one of them, each asserted here with a
real key press or mouse press through the real window:

- it opens with Close focused, never the page, so nothing is ringed before the
  reader has done anything (the licences used to open on their text);
- a click on the page never takes focus from where it was;
- the page is a Tab stop only while it overflows. The test window's licences
  are one line long and fit, so Tab stays on Close; the Guide always overflows,
  so Tab, Right, Shift+Tab and Left step between Close and the page.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QGuiApplication

# Imported for its converters: without QtQuick loaded, the window comes back as
# a bare QWindow and every QQuickItem it hands over is refused.
from PySide6.QtQuick import QQuickItem  # noqa: F401
from PySide6.QtTest import QTest

from tests.ui.window_stub import StubController, feed_dto, load_main_window

# Each reading dialog in the window, against the prefix its parts are named by.
_DIALOGS = [
    ("uiLicenceDialog", "licence"),
    ("modelLicenceDialog", "licence"),
    ("guideDialog", "guide"),
]


@pytest.fixture
def window(qapp):
    controller = StubController([feed_dto(1, "Alpha", unread=3)])
    engine, component, win = load_main_window(controller)
    QTest.qWaitForWindowExposed(win)
    QGuiApplication.processEvents()

    yield win

    win.setProperty("visible", False)
    QGuiApplication.processEvents()
    del component
    del engine


def _focused(win) -> str:
    item = win.activeFocusItem()
    while item is not None:
        if item.objectName():
            return item.objectName()
        item = item.parentItem()
    return "<nothing>"


def _open(win, name: str):
    dialog = win.findChild(QObject, name)
    assert dialog is not None, f"{name} was never created"
    dialog.setProperty("visible", True)
    QGuiApplication.processEvents()
    return dialog


def _key(win, key) -> None:
    QTest.keyClick(win, key)
    QGuiApplication.processEvents()


@pytest.mark.parametrize(("name", "prefix"), _DIALOGS)
def test_it_opens_on_close(window, name: str, prefix: str) -> None:
    _open(window, name)

    assert _focused(window) == f"{prefix}CloseBtn"


@pytest.mark.parametrize(("name", "prefix"), _DIALOGS)
def test_a_click_on_the_page_never_takes_focus(window, name: str, prefix: str) -> None:
    dialog = _open(window, name)
    page = dialog.property("contentItem")
    centre = page.mapToScene(page.boundingRect().center()).toPoint()

    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, centre)
    QGuiApplication.processEvents()

    assert _focused(window) == f"{prefix}CloseBtn"


@pytest.mark.parametrize("name", ["uiLicenceDialog", "modelLicenceDialog"])
@pytest.mark.parametrize("key", [Qt.Key_Tab, Qt.Key_Right, Qt.Key_Backtab])
def test_a_page_that_fits_is_not_a_stop(window, name: str, key) -> None:
    _open(window, name)

    _key(window, key)

    assert _focused(window) == "licenceCloseBtn"


@pytest.mark.parametrize(
    ("forward", "back"),
    [(Qt.Key_Tab, Qt.Key_Backtab), (Qt.Key_Right, Qt.Key_Left)],
)
def test_an_overflowing_page_is_the_other_stop(window, forward, back) -> None:
    _open(window, "guideDialog")

    _key(window, forward)
    assert _focused(window) == "guideText"
    _key(window, forward)
    assert _focused(window) == "guideCloseBtn"
    _key(window, back)
    assert _focused(window) == "guideText"
    _key(window, back)
    assert _focused(window) == "guideCloseBtn"
