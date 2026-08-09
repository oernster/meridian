"""Clicking a row with the mouse, which no test in this suite ever did.

A delegate that declares `required` properties stops receiving the model's
context properties, so `index` is not defined inside it. Reading it throws a
ReferenceError, the handler dies on that line and every statement after it is
skipped, which is how selecting a feed silently stopped working while the whole
suite stayed green: both rows set `currentIndex = index` before reporting
outwards, so both reports came after the throw.

Nothing about this shows up in a keyboard test. The list's own
`onCurrentIndexChanged` reports the row without going near the delegate, so the
rings kept passing while the mouse did nothing at all.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from tests.ui.window_stub import StubController, feed_dto, item_dto, load_main_window

_FEEDS = [feed_dto(1, "Alpha", unread=3), feed_dto(2, "Beta")]

_ITEMS = [
    item_dto(11, "First item"),
    item_dto(12, "Second item"),
]


@pytest.fixture
def window(qapp):  # noqa: ANN001, ANN201
    controller = StubController(_FEEDS, _ITEMS)
    engine, component, win = load_main_window(controller)
    QTest.qWaitForWindowExposed(win)
    QGuiApplication.processEvents()

    yield win, controller

    win.setProperty("visible", False)
    QGuiApplication.processEvents()
    del component
    del engine


def _visual_find(item, name: str):  # noqa: ANN001, ANN202
    for child in item.childItems():
        if child.objectName() == name:
            return child
        hit = _visual_find(child, name)
        if hit is not None:
            return hit
    return None


def _named(win, name: str):  # noqa: ANN001, ANN202
    found = win.findChild(QQuickItem, name) or _visual_find(win.contentItem(), name)
    assert found is not None, f"{name} was never created"
    return found


def _row(win, list_name: str, index: int):  # noqa: ANN001, ANN202
    """The delegate at a row, taken from the view rather than the model."""
    view = _named(win, list_name)
    view.setProperty("currentIndex", index)
    QGuiApplication.processEvents()
    row = view.property("currentItem")
    assert row is not None, f"{list_name} never instantiated row {index}"
    return row


def _click(win, item) -> None:  # noqa: ANN001
    centre = item.mapToScene(
        QPointF(item.property("width") / 2, item.property("height") / 2)
    ).toPoint()
    QTest.mousePress(win, Qt.LeftButton, Qt.NoModifier, centre)
    QTest.mouseRelease(win, Qt.LeftButton, Qt.NoModifier, centre)
    QGuiApplication.processEvents()


def test_clicking_a_feed_row_selects_that_feed(window) -> None:  # noqa: ANN001
    """The whole point of the sidebar; it reached nothing."""
    win, controller = window
    controller.calls.clear()

    _click(win, _row(win, "feedList", 1))

    assert controller.called("selectFeed") == [("selectFeed", 2)]


def test_clicking_a_feed_row_makes_it_current(window) -> None:  # noqa: ANN001
    """The delegate sets this from its own index before it reports."""
    win, _ = window
    feed_list = _named(win, "feedList")
    row = _row(win, "feedList", 1)
    feed_list.setProperty("currentIndex", -1)
    QGuiApplication.processEvents()

    _click(win, row)

    assert feed_list.property("currentIndex") == 1


def test_clicking_an_item_row_opens_and_marks_it_read(window) -> None:  # noqa: ANN001
    """The same shape in the reader: the row reports, the composition acts."""
    win, controller = window
    controller.calls.clear()

    _click(win, _row(win, "itemList", 1))

    assert controller.called("markRead") == [("markRead", 12)]
    assert _named(win, "detailTitle").property("text") == "Second item"


def test_clicking_an_item_row_makes_it_current(window) -> None:  # noqa: ANN001
    win, _ = window
    item_list = _named(win, "itemList")
    row = _row(win, "itemList", 1)
    item_list.setProperty("currentIndex", -1)
    QGuiApplication.processEvents()

    _click(win, row)

    assert item_list.property("currentIndex") == 1
