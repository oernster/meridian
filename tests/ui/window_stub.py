"""A stand-in controller with exactly the surface `main.qml` reaches for.

Hand written rather than mocked. The QML binds to properties and connects to
signals by name, so what matters is that the shape is right; a mock that
answers to anything would let a renamed property pass unnoticed.

Every call is recorded so a test can assert that a keystroke or a click reached
the controller, which is the only thing the window is responsible for once the
panels report what happened.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Property, QObject, QUrl, Signal, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine

from meridian.application.dto.feed_dto import FeedDTO
from meridian.application.dto.item_dto import ItemDTO, MediaDTO
from meridian.ui.models import FeedCandidateModel, FeedListModel, ItemListModel

QML_DIR = Path(__file__).resolve().parents[2] / "meridian" / "ui" / "qml"

# The palette the window builds at runtime, as a plain dict. A component under
# test takes it as its `theme`, so every colour it reads has to be present.
THEME = {
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


def feed_dto(
    feed_id: int,
    title: str,
    unread: int = 0,
    description: str | None = None,
    filter_expr: str | None = None,
) -> FeedDTO:
    return FeedDTO(
        id=feed_id,
        url=f"https://example.com/feed/{feed_id}",
        source_type="mfeed",
        title=title,
        description=description,
        icon=None,
        language=None,
        filter_expr=filter_expr,
        unread_count=unread,
    )


def item_dto(
    item_id: int,
    title: str,
    *,
    feed_id: int = 1,
    item_type: str = "article",
    url: str | None = None,
    published: str = "2026-08-01T09:30:00Z",
    description: str = "",
    thumbnail: str | None = None,
    duration: int | None = None,
    is_read: bool = False,
    media_url: str = "",
) -> ItemDTO:
    return ItemDTO(
        id=item_id,
        feed_id=feed_id,
        item_id=f"item-{item_id}",
        type=item_type,
        title=title,
        url=url or f"https://example.com/item/{item_id}",
        published_iso=published,
        description=description,
        thumbnail_url=thumbnail,
        duration=duration,
        is_read=is_read,
        media=(MediaDTO(url=media_url, mime_type="video/mp4"),) if media_url else (),
    )


class StubController(QObject):
    feedsChanged = Signal()
    errorOccurred = Signal(str)
    newItemsAvailable = Signal(int, int)
    itemsChanged = Signal()
    searchStarted = Signal()
    searchFinished = Signal()
    searchError = Signal(str)
    searchCancelled = Signal()

    def __init__(
        self,
        feeds: list[FeedDTO] | None = None,
        items: list[ItemDTO] | None = None,
    ) -> None:
        super().__init__()
        self._feeds = FeedListModel()
        self._items = ItemListModel()
        self._candidates = FeedCandidateModel()
        self._selected_feed_id = 0
        if feeds:
            self._feeds.refresh(feeds)
        if items:
            self._items.refresh(items)
        self.calls: list[tuple] = []

    def _record(self, name: str, *args) -> None:
        self.calls.append((name, *args))

    def called(self, name: str) -> list[tuple]:
        return [c for c in self.calls if c[0] == name]

    @Property(QObject, constant=True)
    def feedModel(self) -> QObject:
        return self._feeds

    @Property(QObject, constant=True)
    def itemModel(self) -> QObject:
        return self._items

    @Property(QObject, constant=True)
    def candidateModel(self) -> QObject:
        return self._candidates

    @Property(int, notify=feedsChanged)
    def selectedFeedId(self) -> int:
        return self._selected_feed_id

    @Slot()
    def loadFeeds(self) -> None:
        self._record("loadFeeds")

    @Slot(int)
    def selectFeed(self, feed_id: int) -> None:
        self._record("selectFeed", feed_id)
        self._selected_feed_id = feed_id
        self.feedsChanged.emit()

    @Slot(int)
    def unsubscribe(self, feed_id: int) -> None:
        self._record("unsubscribe", feed_id)

    @Slot(list)
    def bulkUnsubscribe(self, feed_ids: list) -> None:
        self._record("bulkUnsubscribe", tuple(feed_ids))

    @Slot(str)
    def setFeedSort(self, key: str) -> None:
        self._record("setFeedSort", key)

    @Slot(str)
    def setItemSort(self, key: str) -> None:
        self._record("setItemSort", key)

    @Slot(int)
    def markRead(self, item_id: int) -> None:
        self._record("markRead", item_id)

    @Slot(int)
    def markAllRead(self, feed_id: int) -> None:
        self._record("markAllRead", feed_id)

    @Slot(str)
    def subscribe(self, url: str) -> None:
        self._record("subscribe", url)

    @Slot(int, str)
    def setFilter(self, feed_id: int, expr: str) -> None:
        self._record("setFilter", feed_id, expr)

    @Slot(int, str)
    def updateFeedUrl(self, feed_id: int, url: str) -> None:
        self._record("updateFeedUrl", feed_id, url)

    @Slot(str)
    def exportFeeds(self, path: str) -> None:
        self._record("exportFeeds", path)

    @Slot(str)
    def importFeeds(self, path: str) -> None:
        self._record("importFeeds", path)

    @Slot(str)
    def searchFeeds(self, query: str) -> None:
        self._record("searchFeeds", query)

    @Slot()
    def cancelSearch(self) -> None:
        self._record("cancelSearch")

    @Slot(int)
    def setResultCap(self, cap: int) -> None:
        self._record("setResultCap", cap)

    @Slot(str)
    def subscribeFromDiscovery(self, url: str) -> None:
        self._record("subscribeFromDiscovery", url)

    @Slot(list)
    def bulkSubscribeFromDiscovery(self, urls: list) -> None:
        self._record("bulkSubscribeFromDiscovery", tuple(urls))


class StubUpdateController(QObject):
    """The update surface `main.qml` reaches for, recorded like the stub above."""

    updateAvailable = Signal(str, str, str, str)
    upToDate = Signal()
    checkFailed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[tuple] = []

    def _record(self, name: str, *args) -> None:
        self.calls.append((name, *args))

    def called(self, name: str) -> list[tuple]:
        return [c for c in self.calls if c[0] == name]

    @Slot(str)
    def checkAutomatically(self, skipped_version: str) -> None:
        self._record("checkAutomatically", skipped_version)

    @Slot()
    def checkManually(self) -> None:
        self._record("checkManually")

    @Slot(str)
    def openDownload(self, url: str) -> None:
        self._record("openDownload", url)


def load_main_window(
    controller: StubController,
    update_controller: StubUpdateController | None = None,
) -> tuple[QQmlEngine, QQmlComponent, QObject]:
    """Load the real `main.qml` against the stub, with the context it expects.

    The component is handed back with the window. Letting it fall out of scope
    takes the window with it, reported as a deleted C++ object rather than as
    anything that reads like an ownership problem.
    """
    engine = QQmlEngine()
    context = engine.rootContext()
    context.setContextProperty("controller", controller)
    # Kept referenced via the engine: setContextProperty does not take
    # ownership, and a garbage-collected default stub would leave QML calling
    # a deleted object.
    update_stub = update_controller or StubUpdateController()
    engine._update_controller = update_stub
    context.setContextProperty("updateController", update_stub)
    context.setContextProperty("appVersion", "0.0.0-test")
    context.setContextProperty("appIconUrl", "")
    context.setContextProperty("uiLicenceText", "UI licence text")
    context.setContextProperty("modelLicenceText", "Model licence text")

    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / "main.qml")))
    assert component.status() != QQmlComponent.Status.Error, component.errorString()
    window = component.create()
    assert window is not None, component.errorString()
    return engine, component, window
