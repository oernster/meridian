"""The window's focus ring still closes now that it spans four files.

The ring runs from the header's Import button along the header, into the
sidebar's select-all, past the sort chips and into the feed list. It used to be
wired by id inside `main.qml`. Header and sidebar are separate components now
and neither names the other: each hands over through a signal the window
connects, so the joins between them exist only in `main.qml`.

That is exactly the kind of wiring that compiles whatever happens. A dropped
connection leaves both components correct on their own and simply strands the
user at the join. Nothing short of a delivered key press shows it, because
the handlers are `Keys.onTabPressed` on whichever item holds focus.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import QObject, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from tests.ui.window_stub import StubController, feed_dto, load_main_window

_FEEDS = [
    feed_dto(1, "Alpha", unread=3),
    feed_dto(2, "Beta"),
]

# The order the user walks with Tab, from the first stop to the last before the
# reader takes over. The active sort chip is not a stop, so A→Z is absent.
_RING = [
    "importBtn",
    "exportBtn",
    "discoverBtn",
    "manageBtn",
    "uiLicenceBtn",
    "modelLicenceBtn",
    "aboutBtn",
    "themeToggleBtn",
    "checkAll",
    "sortChip_alpha_desc",
    "sortChip_unread",
    "feedList",
]


@pytest.fixture
def window(qapp):  # noqa: ANN001, ANN201
    controller = StubController(_FEEDS)
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


def _child(root, name: str):  # noqa: ANN001, ANN202
    """A named QObject that is not an Item, such as a Dialog."""
    found = root.findChild(QObject, name)
    assert found is not None, f"{name} was never created"
    return found


def _named(win, name: str):  # noqa: ANN001, ANN202
    """Search the QObject tree, then the visual one.

    A Repeater's delegates are owned by its QQmlDelegateModel rather than by
    the item they are laid out in, so `findChild` cannot see the sort chips at
    all. They are visual children of the row, which is where the second pass
    looks.
    """
    found = win.findChild(QQuickItem, name) or _visual_find(win.contentItem(), name)
    assert found is not None, f"{name} was never created"
    return found


def _focused(win) -> str:  # noqa: ANN001
    """The nearest named ancestor of whatever holds focus.

    A focused ListView passes active focus to its current delegate, so the
    deepest focus item is a FeedRow rather than the list itself.
    """
    item = win.activeFocusItem()
    while item is not None:
        if item.objectName():
            return item.objectName()
        item = item.parentItem()
    return "<nothing>"


def _tab(win, back: bool = False) -> None:  # noqa: ANN001
    QTest.keyClick(win, Qt.Key_Backtab if back else Qt.Key_Tab)
    QGuiApplication.processEvents()


def test_nothing_visible_is_focused_on_startup(window) -> None:  # noqa: ANN001
    """The neutral start: focus rests on the 0x0 absorber, not on a control.

    Focusing the header on startup is what makes a button wear an orange
    border before the user has touched anything.
    """
    win, _ = window

    assert _focused(win) == "initialFocusItem"


def test_tab_walks_the_whole_ring_in_order(window) -> None:  # noqa: ANN001
    """Two of these steps are joins between separate components."""
    win, _ = window

    for expected in _RING:
        _tab(win)
        assert _focused(win) == expected, f"the ring broke before {expected}"


def test_shift_tab_goes_from_the_sidebar_to_the_header(window) -> None:  # noqa: ANN001
    """The join in the other direction, which is a separate connection."""
    win, _ = window
    _named(win, "checkAll").forceActiveFocus(Qt.TabFocusReason)
    QGuiApplication.processEvents()
    assert _focused(win) == "checkAll"

    _tab(win, back=True)

    assert _focused(win) == "themeToggleBtn"


def test_the_header_reports_the_theme_toggle(window) -> None:  # noqa: ANN001
    """The bar emits; the window owns the palette and the stored setting."""
    win, _ = window
    theme_before = _named(win, "themeToggleBtn")

    _named(win, "themeToggleBtn").forceActiveFocus(Qt.TabFocusReason)
    QTest.keyClick(win, Qt.Key_Return)
    QGuiApplication.processEvents()

    assert theme_before.property("label") == "🌙", "the palette did not flip to light"


def test_a_sort_chip_reaches_the_controller(window) -> None:  # noqa: ANN001
    win, controller = window

    _named(win, "sortChip_unread").forceActiveFocus(Qt.TabFocusReason)
    QTest.keyClick(win, Qt.Key_Return)
    QGuiApplication.processEvents()

    assert controller.called("setFeedSort") == [("setFeedSort", "unread")]


def test_the_active_sort_chip_is_inert(window) -> None:  # noqa: ANN001
    """It is not a tab stop; pressing it changes nothing."""
    win, controller = window
    chip = _named(win, "sortChip_alpha_asc")

    assert chip.property("activeFocusOnTab") is False

    chip.forceActiveFocus(Qt.TabFocusReason)
    QTest.keyClick(win, Qt.Key_Return)
    QGuiApplication.processEvents()

    assert controller.called("setFeedSort") == []


def test_selecting_every_feed_shows_the_remove_button(window) -> None:  # noqa: ANN001
    """It is a conditional stop, so the ring has to grow by one when it shows."""
    win, _ = window
    assert _named(win, "removeBtn").property("visible") is False

    _named(win, "checkAll").forceActiveFocus(Qt.TabFocusReason)
    QTest.keyClick(win, Qt.Key_Return)
    QGuiApplication.processEvents()

    assert _named(win, "removeBtn").property("visible") is True
    assert win.property("_selectedFeedCount") == len(_FEEDS)

    _tab(win)
    assert _focused(win) == "removeBtn"


def test_removing_the_selection_asks_first(window) -> None:  # noqa: ANN001
    """Destructive, so it must confirm rather than act."""
    win, controller = window
    _named(win, "checkAll").forceActiveFocus(Qt.TabFocusReason)
    QTest.keyClick(win, Qt.Key_Return)
    QGuiApplication.processEvents()

    _named(win, "removeBtn").forceActiveFocus(Qt.TabFocusReason)
    QTest.keyClick(win, Qt.Key_Return)
    QGuiApplication.processEvents()

    dialog = _child(win, "bulkRemoveDialog")
    assert controller.called("bulkUnsubscribe") == [], "it removed without asking"
    assert dialog.property("visible") is True
    assert "2 feed(s)" in dialog.property("message")


def test_confirming_the_removal_reaches_the_controller(window) -> None:  # noqa: ANN001
    win, controller = window
    _named(win, "checkAll").forceActiveFocus(Qt.TabFocusReason)
    QTest.keyClick(win, Qt.Key_Return)
    QGuiApplication.processEvents()
    _named(win, "removeBtn").forceActiveFocus(Qt.TabFocusReason)
    QTest.keyClick(win, Qt.Key_Return)
    QGuiApplication.processEvents()

    _child(win, "bulkRemoveDialog").accept()
    QGuiApplication.processEvents()

    assert controller.called("bulkUnsubscribe") == [("bulkUnsubscribe", (1, 2))]
    assert win.property("_selectedFeedCount") == 0
