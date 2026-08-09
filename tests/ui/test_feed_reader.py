"""The reader after its split: the ring across five files and the joins.

`FeedReader.qml` is composition only now. The list panel reports the row it
selected rather than loading the pane; the pane asks the media panel whether
its transport is a focus stop at all, because a YouTube embed brings its own
and is therefore not one. Every one of those joins is a signal; a signal that
is never connected leaves both components correct on their own.

The list panel is entered here rather than reached from the window, so the use
site stands in for what `main.qml` provides: a header button to hand focus
forward to, plus the palette.
"""

from __future__ import annotations

import pytest
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest

from tests.ui.window_stub import QML_DIR, THEME, StubController, feed_dto, item_dto

# Nothing is fetched: the player is asked for a file that is not there, which
# fails the same way as any unreachable source and never touches the network.
_CLIP_URL = "file:///clip-that-is-not-there.mp4"
_YOUTUBE_WATCH = "https://www.youtube.com/watch?v=aBcDeFgHiJk"

_FEED_ID = 1

_ARTICLE = 11
_CLIP = 12
_EMBED = 13

_ITEMS = [
    item_dto(_ARTICLE, "Plain article", description="Body text"),
    item_dto(_CLIP, "Local clip", item_type="video", media_url=_CLIP_URL, duration=95),
    item_dto(_EMBED, "Embedded talk", item_type="video", url=_YOUTUBE_WATCH),
]

# Newest is the active chip, so it is not a stop. The list is entered last,
# which is what loads the first item into the pane.
_PANEL_RING = ["sortChip_oldest", "sortChip_alpha", "markAllReadBtn", "itemList"]

# Back out of the pane, through the panel and off the front of the reader.
_REVERSE_RING = [
    "itemList",
    "markAllReadBtn",
    "sortChip_alpha",
    "sortChip_oldest",
    "firstHeaderBtn",
]

_USE_SITE = """
import QtQuick
import QtQuick.Controls

Item {
    width: 1200
    height: 720

    Button {
        id: headerStub
        objectName: "firstHeaderBtn"
        width: 120
        height: 32
        text: "Header"
        activeFocusOnTab: true
    }

    FeedReader {
        objectName: "reader"
        anchors.top: headerStub.bottom
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        theme: appTheme
        firstHeaderBtn: headerStub
    }
}
"""


@pytest.fixture
def reader(qapp):  # noqa: ANN001, ANN201
    controller = StubController([feed_dto(_FEED_ID, "Alpha")], _ITEMS)

    engine = QQmlEngine()
    engine.rootContext().setContextProperty("controller", controller)
    engine.rootContext().setContextProperty("appTheme", THEME)

    component = QQmlComponent(engine)
    component.setData(
        _USE_SITE.encode("utf-8"),
        QUrl.fromLocalFile(str(QML_DIR / "use_site.qml")),
    )
    assert component.status() != QQmlComponent.Status.Error, component.errorString()
    item = component.create()
    assert item is not None, component.errorString()

    win = QQuickWindow()
    win.resize(1200, 720)
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
    """A Repeater's chips are not QObject children of the row they sit in."""
    found = root.findChild(QQuickItem, name) or _visual_find(root, name)
    assert found is not None, f"{name} was never created"
    return found


def _focused(win) -> str:  # noqa: ANN001
    item = win.activeFocusItem()
    while item is not None:
        if item.objectName():
            return item.objectName()
        item = item.parentItem()
    return "<nothing>"


def _tab(win, back: bool = False) -> None:  # noqa: ANN001
    QTest.keyClick(win, Qt.Key_Backtab if back else Qt.Key_Tab)
    QGuiApplication.processEvents()


def _focus(item, name: str) -> None:  # noqa: ANN001
    _named(item, name).forceActiveFocus(Qt.TabFocusReason)
    QGuiApplication.processEvents()


def _select(item, row: int) -> None:  # noqa: ANN001
    """Enter the list, then walk to the wanted row.

    Entering it is what selects a row at all: the list takes focus, takes the
    first row as current, then reports it outwards.
    """
    _focus(item, "itemList")
    _named(item, "itemList").setProperty("currentIndex", row)
    QGuiApplication.processEvents()


def test_tab_walks_the_panel_ring_into_the_pane(reader) -> None:  # noqa: ANN001
    """The chips skip the active one; the list hands across the divider."""
    item, win, _ = reader
    _focus(item, _PANEL_RING[0])

    for expected in _PANEL_RING[1:]:
        _tab(win)
        assert _focused(win) == expected, f"the ring broke before {expected}"

    _tab(win)
    assert _focused(win) == "openButton", "the list never reached the pane"


def test_shift_tab_walks_the_ring_back_out_of_reader(reader) -> None:  # noqa: ANN001
    """The same ring in reverse, which is a separate set of connections.

    The last step is the reader's own: stepping off the front of the chips
    leaves the reader entirely; only the composition knows what is there.
    """
    item, win, _ = reader
    _select(item, 0)
    _focus(item, "openButton")

    for expected in _REVERSE_RING:
        _tab(win, back=True)
        assert _focused(win) == expected, f"the ring broke before {expected}"


def test_tab_off_the_open_button_reaches_the_header(reader) -> None:  # noqa: ANN001
    """The wrap the window relies on, which only the reader can make."""
    item, win, _ = reader
    _select(item, 0)
    _focus(item, "openButton")

    _tab(win)

    assert _focused(win) == "firstHeaderBtn"


def test_a_clip_puts_the_transport_first_in_the_pane(reader) -> None:  # noqa: ANN001
    item, win, _ = reader
    _select(item, 1)
    assert _named(item, "mediaPanel").property("hasTransport") is True

    _focus(item, "itemList")
    _tab(win)

    assert _focused(win) == "playPauseBtn"


def test_the_transport_runs_through_to_the_open_button(reader) -> None:  # noqa: ANN001
    item, win, _ = reader
    _select(item, 1)
    _focus(item, "playPauseBtn")

    for expected in ["seekSlider", "volumeSlider", "openButton"]:
        _tab(win)
        assert _focused(win) == expected, f"the transport broke before {expected}"


def test_open_button_shift_tab_re_enters_transport(reader) -> None:  # noqa: ANN001
    """The pane has to ask the media panel; the answer decides the stop."""
    item, win, _ = reader
    _select(item, 1)
    _focus(item, "openButton")

    _tab(win, back=True)

    assert _focused(win) == "volumeSlider"


def test_transport_shift_tab_crosses_back_to_list(reader) -> None:  # noqa: ANN001
    """Three components deep: the panel asks the pane, which asks the reader."""
    item, win, _ = reader
    _select(item, 1)
    _focus(item, "playPauseBtn")

    _tab(win, back=True)

    assert _focused(win) == "itemList"


def test_a_youtube_page_brings_its_own_transport(reader) -> None:  # noqa: ANN001
    """The embed is showing, so the panel is visible and still not a stop."""
    item, win, _ = reader
    _select(item, 2)
    media = _named(item, "mediaPanel")
    assert media.property("visible") is True
    assert media.property("hasTransport") is False

    _focus(item, "itemList")
    _tab(win)

    assert _focused(win) == "openButton"


def test_selecting_a_row_loads_the_pane_and_marks_read(reader) -> None:  # noqa: ANN001
    """The composition owns both halves of this; neither panel knows the other."""
    item, _, controller = reader

    _select(item, 0)

    assert controller.called("markRead") == [("markRead", _ARTICLE)]
    assert _named(item, "detailTitle").property("text") == "Plain article"
    assert _named(item, "detailMeta").property("text") == "2026-08-01  09:30"


def test_a_row_binds_every_required_role(reader) -> None:  # noqa: ANN001
    """A name that drifts from its role leaves the list empty and compiles."""
    item, _, _ = reader
    _select(item, 1)
    row = _named(item, "itemList").property("currentItem")
    assert row is not None, "no row was instantiated"

    assert row.property("itemId") == _CLIP
    assert row.property("itemTitle") == "Local clip"
    assert row.property("itemType") == "video"
    assert row.property("itemUrl") == f"https://example.com/item/{_CLIP}"
    assert row.property("itemPublished").startswith("2026-08-01")
    assert row.property("itemThumbnail") == ""
    assert row.property("itemDuration") == 95
    assert row.property("itemIsRead") is False
    assert row.property("durationText") == "01:35"


def test_mark_all_read_waits_for_a_selected_feed(reader) -> None:  # noqa: ANN001
    """The guard lives in the composition, so the panel just reports."""
    item, win, controller = reader
    _focus(item, "markAllReadBtn")

    QTest.keyClick(win, Qt.Key_Space)
    QGuiApplication.processEvents()
    assert controller.called("markAllRead") == [], "it marked a feed that is not open"

    controller.selectFeed(_FEED_ID)
    QTest.keyClick(win, Qt.Key_Space)
    QGuiApplication.processEvents()

    assert controller.called("markAllRead") == [("markAllRead", _FEED_ID)]


def test_emptying_the_feed_clears_the_pane(reader) -> None:  # noqa: ANN001
    """The reader listens for this; the pane cannot see the model."""
    item, _, controller = reader
    _select(item, 0)
    assert _named(item, "detailTitle").property("text") == "Plain article"

    controller.itemModel.refresh([])
    controller.itemsChanged.emit()
    QGuiApplication.processEvents()

    assert _named(item, "detailTitle").property("text") == ""
    assert _named(item, "mediaPanel").property("visible") is False
