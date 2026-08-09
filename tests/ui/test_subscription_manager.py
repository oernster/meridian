"""The manager drawer after its split: the ring, the rows and the dialogs.

Two joins now cross a component boundary. `AddSubscriptionBar` hands forward to
the list header through `focusForwardRequested`; the header hands back into
the bar through `focusLast()`, which has to ask whether Subscribe is a tab stop
at all: it only is while the field holds an `https://` URL.

The filter dialog is the other thing worth asserting. A filter is one string of
terms joined by AND. The dialog splits it into a row per term on the way in and
joins whatever is still active on the way out. That round trip is real logic
that moved file.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest

from tests.ui.window_stub import StubController, feed_dto

_QML_DIR = Path(__file__).resolve().parents[2] / "meridian" / "ui" / "qml"

_FEEDS = [
    feed_dto(
        1,
        "Alpha",
        description="First feed",
        filter_expr="type:video AND lang:en",
    ),
    feed_dto(2, "Beta"),
]

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
def manager(qapp):  # noqa: ANN001, ANN201
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
    win.resize(520, 700)
    item.setParentItem(win.contentItem())
    win.show()
    QTest.qWaitForWindowExposed(win)
    QGuiApplication.processEvents()

    yield item, win, controller

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


def _named(root, name: str):  # noqa: ANN001, ANN202
    found = root.findChild(QQuickItem, name) or _visual_find(root, name)
    assert found is not None, f"{name} was never created"
    return found


def _child(root, name: str):  # noqa: ANN001, ANN202
    found = root.findChild(QObject, name)
    assert found is not None, f"{name} was never created"
    return found


def _in_dialog(dialog, name: str):  # noqa: ANN001, ANN202
    """A dialog's contents render into the overlay, not under the manager.

    Searching from the item finds nothing, which reads like the content was
    never built rather than like it was reparented.
    """
    return _visual_find(dialog.property("contentItem"), name)


def _focused(win) -> str:  # noqa: ANN001
    item = win.activeFocusItem()
    while item is not None:
        if item.objectName():
            return item.objectName()
        item = item.parentItem()
    return "<nothing>"


def _type_url(item, url: str) -> None:  # noqa: ANN001
    _named(item, "urlField").setProperty("text", url)
    QGuiApplication.processEvents()


def test_focus_url_field_reaches_into_the_bar(manager) -> None:  # noqa: ANN001
    """The drawer opens onto the field, which is a call across the boundary."""
    item, win, _ = manager

    item.metaObject().invokeMethod(item, "focusUrlField")
    QGuiApplication.processEvents()

    assert _focused(win) == "urlField"


def test_tab_reaches_subscribe_once_the_url_is_ok(manager) -> None:  # noqa: ANN001
    item, win, _ = manager
    _type_url(item, "https://example.com/feed")

    item.metaObject().invokeMethod(item, "focusUrlField")
    QGuiApplication.processEvents()
    QTest.keyClick(win, Qt.Key_Tab)
    QGuiApplication.processEvents()

    assert _focused(win) == "subscribeButton"


def test_tab_skips_subscribe_while_the_url_is_not(manager) -> None:  # noqa: ANN001
    """It is not a tab stop until the field holds an https:// URL."""
    item, win, _ = manager
    _type_url(item, "not a url")

    item.metaObject().invokeMethod(item, "focusUrlField")
    QGuiApplication.processEvents()
    QTest.keyClick(win, Qt.Key_Tab)
    QGuiApplication.processEvents()

    assert _focused(win) == "selectAllCheckbox"


def test_right_from_the_field_crosses_to_the_header(manager) -> None:  # noqa: ANN001
    """The forward join, which is a signal rather than the Tab chain.

    Tab out of the field is natural traversal and would still work with the
    connection cut, so only the arrow exercises it.
    """
    item, win, _ = manager

    item.metaObject().invokeMethod(item, "focusUrlField")
    QGuiApplication.processEvents()
    QTest.keyClick(win, Qt.Key_Right)
    QGuiApplication.processEvents()

    assert _focused(win) == "selectAllCheckbox"


def test_the_list_header_hands_back_into_the_bar(manager) -> None:  # noqa: ANN001
    """focusLast() has to ask whether Subscribe is a stop; this is the join."""
    item, win, _ = manager
    _type_url(item, "https://example.com/feed")
    _named(item, "selectAllCheckbox").forceActiveFocus(Qt.TabFocusReason)
    QGuiApplication.processEvents()

    QTest.keyClick(win, Qt.Key_Backtab)
    QGuiApplication.processEvents()

    assert _focused(win) == "subscribeButton"


def test_it_hands_back_to_the_field_without_subscribe(manager) -> None:  # noqa: ANN001
    item, win, _ = manager
    _type_url(item, "")
    _named(item, "selectAllCheckbox").forceActiveFocus(Qt.TabFocusReason)
    QGuiApplication.processEvents()

    QTest.keyClick(win, Qt.Key_Backtab)
    QGuiApplication.processEvents()

    assert _focused(win) == "urlField"


def test_subscribing_reaches_the_controller_and_clears(manager) -> None:  # noqa: ANN001
    item, win, controller = manager
    _type_url(item, "  https://example.com/new  ")

    _named(item, "subscribeButton").forceActiveFocus(Qt.TabFocusReason)
    QTest.keyClick(win, Qt.Key_Return)
    QGuiApplication.processEvents()

    assert controller.called("subscribe") == [("subscribe", "https://example.com/new")]
    assert _named(item, "urlField").property("text") == ""


def test_a_row_binds_its_feed_from_the_model(manager) -> None:  # noqa: ANN001
    """Every required name has to match a role; a drift leaves the list empty."""
    item, _, _ = manager
    row = _named(item, "subList").property("currentItem") or _first_row(item)

    assert row.property("feedTitle") == "Alpha"
    assert row.property("feedFilter") == "type:video AND lang:en"
    assert row.property("feedDescription") == "First feed"


def _first_row(item):  # noqa: ANN001, ANN202
    sub_list = _named(item, "subList")
    sub_list.setProperty("currentIndex", 0)
    QGuiApplication.processEvents()
    current = sub_list.property("currentItem")
    assert current is not None, "no row was instantiated"
    return current


def test_removing_a_row_selects_it_and_asks_first(manager) -> None:  # noqa: ANN001
    """Destructive, so it confirms; and the confirmation counts one feed."""
    item, _, controller = manager
    row = _first_row(item)

    row.metaObject().invokeMethod(row, "removeRequested")
    QGuiApplication.processEvents()

    assert controller.called("bulkUnsubscribe") == [], "it removed without asking"
    assert item.property("selectedCount") == 1
    assert "1 feed(s)" in _child(item, "bulkRemoveDialog").property("message")


def test_the_dialog_splits_a_filter_into_terms(manager) -> None:  # noqa: ANN001
    item, _, _ = manager
    row = _first_row(item)
    dialog = _child(item, "filterDialog")

    row.metaObject().invokeMethod(row, "filterRequested")
    QGuiApplication.processEvents()

    assert dialog.property("visible") is True
    assert _in_dialog(dialog, "termRow0") is not None, "the filter was not split"
    assert _in_dialog(dialog, "termRow1") is not None


def test_accepting_rejoins_the_active_terms(manager) -> None:  # noqa: ANN001
    """Turning one term off has to drop it from what the controller is told."""
    item, win, controller = manager
    row = _first_row(item)
    dialog = _child(item, "filterDialog")

    row.metaObject().invokeMethod(row, "filterRequested")
    QGuiApplication.processEvents()

    second = _in_dialog(dialog, "termRow1")
    assert second is not None, "the filter was not split"
    second.forceActiveFocus(Qt.TabFocusReason)
    QTest.keyClick(win, Qt.Key_Space)
    QGuiApplication.processEvents()

    dialog.accept()
    QGuiApplication.processEvents()

    assert controller.called("setFilter") == [("setFilter", 1, "type:video")]


def test_editing_the_url_reaches_the_controller(manager) -> None:  # noqa: ANN001
    item, _, controller = manager
    row = _first_row(item)
    dialog = _child(item, "editUrlDialog")

    row.metaObject().invokeMethod(row, "editRequested")
    QGuiApplication.processEvents()
    assert _named(item, "editUrlField").property("text") == "https://example.com/feed/1"

    _named(item, "editUrlField").setProperty("text", "  https://example.com/moved  ")
    dialog.accept()
    QGuiApplication.processEvents()

    assert controller.called("updateFeedUrl") == [
        ("updateFeedUrl", 1, "https://example.com/moved")
    ]
