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
from meridian.ui.models import FeedCandidateModel, FeedListModel, ItemListModel

QML_DIR = Path(__file__).resolve().parents[2] / "meridian" / "ui" / "qml"


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


class StubController(QObject):
    errorOccurred = Signal(str)
    newItemsAvailable = Signal(int, int)
    itemsChanged = Signal()
    searchStarted = Signal()
    searchFinished = Signal()
    searchError = Signal(str)
    searchCancelled = Signal()

    def __init__(self, feeds: list[FeedDTO] | None = None) -> None:
        super().__init__()
        self._feeds = FeedListModel()
        self._items = ItemListModel()
        self._candidates = FeedCandidateModel()
        if feeds:
            self._feeds.refresh(feeds)
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

    @Property(int, constant=True)
    def selectedFeedId(self) -> int:
        return 0

    @Slot()
    def loadFeeds(self) -> None:
        self._record("loadFeeds")

    @Slot(int)
    def selectFeed(self, feed_id: int) -> None:
        self._record("selectFeed", feed_id)

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

    @Slot()
    def markAllRead(self) -> None:
        self._record("markAllRead")

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


def load_main_window(
    controller: StubController,
) -> tuple[QQmlEngine, QQmlComponent, QObject]:
    """Load the real `main.qml` against the stub, with the context it expects.

    The component is handed back with the window. Letting it fall out of scope
    takes the window with it, reported as a deleted C++ object rather than as
    anything that reads like an ownership problem.
    """
    engine = QQmlEngine()
    context = engine.rootContext()
    context.setContextProperty("controller", controller)
    context.setContextProperty("appVersion", "0.0.0-test")
    context.setContextProperty("appIconUrl", "")
    context.setContextProperty("uiLicenceText", "UI licence text")
    context.setContextProperty("modelLicenceText", "Model licence text")

    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / "main.qml")))
    assert component.status() != QQmlComponent.Status.Error, component.errorString()
    window = component.create()
    assert window is not None, component.errorString()
    return engine, component, window
