"""The selection in the manager drawer survives scrolling a long list.

This has its own module because it needs a list long enough for the `ListView`
to recycle delegates; the drawer's other tests run against two feeds that
fit in one viewport. That difference is the whole reason the defect below
survived four mutation-checked keyboard suites: with two rows no delegate is
ever destroyed, so nothing could observe it.

The defect: `SubscriptionRow` carried `Component.onDestruction:
root._unregisterId(feedId)`; `_unregisterId` called
`toggleSelected(feedId, false)`. A `ListView` destroys delegates as they leave
the viewport, so scrolling deselected every row it passed. Selecting all of two
hundred feeds, scrolling to the end and confirming the removal deleted 113 of
them and the confirmation dialog counted 113 rather than 200. The register pair
existed only to maintain `_allIds`, which nothing read.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickWindow
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtTest import QTest

from tests.ui.window_stub import StubController, feed_dto

_QML_DIR = Path(__file__).resolve().parents[2] / "meridian" / "ui" / "qml"

# Enough rows that the content is many times the viewport, so delegates are
# genuinely destroyed rather than merely scrolled. The test asserts that below
# rather than assuming it.
_TOTAL = 200
_FEEDS = [feed_dto(i, f"Feed {i:03d}") for i in range(1, _TOTAL + 1)]

_VIEW_HEIGHT = 700
_SCROLL_STEPS = 12

_USE_SITE = """
import QtQuick

SubscriptionManager {
    width: 520
    height: 700
    theme: appTheme
}
"""

_THEME = {
    "base": "#1e1e2e",
    "mantle": "#181825",
    "surface0": "#313244",
    "surface1": "#45475a",
    "text": "#cdd6f4",
    "subtext": "#a6adc8",
    "overlay": "#6c7086",
    "blue": "#89b4fa",
    "red": "#f38ba8",
    "green": "#a6e3a1",
    "amber": "#f9e2af",
    "isDark": True,
}


@pytest.fixture
def long_manager(qapp):  # noqa: ANN001, ANN201
    controller = StubController(_FEEDS)

    engine = QQmlEngine()
    engine.rootContext().setContextProperty("controller", controller)
    engine.rootContext().setContextProperty("appTheme", _THEME)

    component = QQmlComponent(engine)
    component.setData(
        _USE_SITE.encode("utf-8"),
        QUrl.fromLocalFile(str(_QML_DIR / "use_site.qml")),
    )
    assert component.status() != QQmlComponent.Status.Error, component.errorString()
    item = component.create()
    assert item is not None, component.errorString()

    win = QQuickWindow()
    win.resize(520, _VIEW_HEIGHT)
    item.setParentItem(win.contentItem())
    win.show()
    QTest.qWaitForWindowExposed(win)
    QGuiApplication.processEvents()

    yield item, controller

    win.close()
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


def _scroll_to_end(sub_list) -> None:  # noqa: ANN001
    """Walk to the bottom in steps, so rows are passed rather than jumped over."""
    span = sub_list.property("contentHeight") - sub_list.property("height")
    for step in range(1, _SCROLL_STEPS + 1):
        sub_list.setProperty("contentY", span * step / _SCROLL_STEPS)
        QGuiApplication.processEvents()
        QTest.qWait(8)


def test_the_list_really_recycles_its_delegates(long_manager) -> None:  # noqa: ANN001
    """Without this the tests below could pass by never destroying anything."""
    item, _ = long_manager
    sub_list = _visual_find(item, "subList")

    assert sub_list is not None
    assert sub_list.property("contentHeight") > sub_list.property("height") * 10

    realised = len(sub_list.property("contentItem").childItems())
    assert realised < _TOTAL, (
        f"all {_TOTAL} delegates are realised at once, so nothing is ever "
        "destroyed and this module cannot observe the defect it exists for"
    )


def test_selecting_all_then_scrolling_keeps_every_row_selected(
    long_manager,
) -> None:  # noqa: ANN001
    item, _ = long_manager
    sub_list = _visual_find(item, "subList")

    item.metaObject().invokeMethod(item, "selectAll")
    QGuiApplication.processEvents()
    assert item.property("selectedCount") == _TOTAL

    _scroll_to_end(sub_list)

    assert (
        item.property("selectedCount") == _TOTAL
    ), "scrolling deselected rows as their delegates were destroyed"


def test_scrolling_back_up_keeps_the_selection(long_manager) -> None:  # noqa: ANN001
    """The return trip destroys the other end of the list, so it is its own case."""
    item, _ = long_manager
    sub_list = _visual_find(item, "subList")

    item.metaObject().invokeMethod(item, "selectAll")
    QGuiApplication.processEvents()
    _scroll_to_end(sub_list)
    sub_list.setProperty("contentY", 0.0)
    QGuiApplication.processEvents()
    QTest.qWait(8)

    assert item.property("selectedCount") == _TOTAL


def test_the_bulk_removal_deletes_everything_that_was_selected(
    long_manager,
) -> None:  # noqa: ANN001
    """The consequence that matters: a destructive action on the full selection.

    The count in the confirmation is asserted too. It reads `selectedCount`, so
    a selection that quietly shrank would have the dialog understate what it
    was about to do, which is worse than the deletion being wrong in silence.
    """
    item, controller = long_manager
    sub_list = _visual_find(item, "subList")

    item.metaObject().invokeMethod(item, "selectAll")
    QGuiApplication.processEvents()
    _scroll_to_end(sub_list)

    dialog = item.findChild(QObject, "bulkRemoveDialog")
    assert dialog is not None
    assert f"Remove {_TOTAL} feed(s)?" in dialog.property("message")

    dialog.metaObject().invokeMethod(dialog, "accept")
    QGuiApplication.processEvents()

    removed = [call for call in controller.calls if call[0] == "bulkUnsubscribe"]
    assert len(removed) == 1
    assert len(removed[0][1]) == _TOTAL
    assert set(removed[0][1]) == {feed.id for feed in _FEEDS}
