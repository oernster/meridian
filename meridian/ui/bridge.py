"""QML bridge: exposes Application services as QML-callable QObject."""

from __future__ import annotations

import asyncio
import concurrent.futures
import dataclasses
import json
import logging
import threading
from pathlib import Path

from PySide6.QtCore import (
    Property,
    QAbstractListModel,
    QModelIndex,
    QObject,
    Qt,
    QUrl,
    Signal,
    Slot,
)

_LOG = logging.getLogger(__name__)

from meridian.application.dto.feed_candidate_dto import FeedCandidateDTO  # noqa: E402
from meridian.application.dto.feed_dto import FeedDTO  # noqa: E402
from meridian.application.dto.item_dto import ItemDTO  # noqa: E402
from meridian.application.interfaces.discovery_fetcher import (  # noqa: E402
    DEFAULT_RESULT_CAP,
)
from meridian.application.services.discovery_service import (  # noqa: E402
    DiscoveryService,
)
from meridian.application.services.item_service import ItemService  # noqa: E402
from meridian.application.services.subscription_service import (  # noqa: E402
    SubscriptionService,
)


class FeedListModel(QAbstractListModel):
    _ROLES = {
        Qt.UserRole + 0: b"feedId",
        Qt.UserRole + 1: b"feedUrl",
        Qt.UserRole + 2: b"feedTitle",
        Qt.UserRole + 3: b"feedIcon",
        Qt.UserRole + 4: b"feedSourceType",
        Qt.UserRole + 5: b"feedUnreadCount",
        Qt.UserRole + 6: b"feedDescription",
    }

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._feeds: list[FeedDTO] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._feeds)

    def roleNames(self) -> dict[int, bytes]:
        return self._ROLES

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._feeds):
            return None
        feed = self._feeds[index.row()]
        match role:
            case v if v == Qt.UserRole + 0:
                return feed.id
            case v if v == Qt.UserRole + 1:
                return feed.url
            case v if v == Qt.UserRole + 2:
                return feed.title or feed.url
            case v if v == Qt.UserRole + 3:
                return feed.icon or ""
            case v if v == Qt.UserRole + 4:
                return feed.source_type
            case v if v == Qt.UserRole + 5:
                return feed.unread_count
            case v if v == Qt.UserRole + 6:
                return feed.description or ""
        return None

    def refresh(self, feeds: list[FeedDTO]) -> None:
        self.beginResetModel()
        self._feeds = feeds
        self.endResetModel()

    def remove_rows_by_ids(self, feed_ids: set[int]) -> None:
        indices = sorted(
            (i for i, f in enumerate(self._feeds) if f.id in feed_ids),
            reverse=True,
        )
        for idx in indices:
            self.beginRemoveRows(QModelIndex(), idx, idx)
            self._feeds.pop(idx)
            self.endRemoveRows()


class ItemListModel(QAbstractListModel):
    _ROLES = {
        Qt.UserRole + 0: b"itemId",
        Qt.UserRole + 1: b"itemTitle",
        Qt.UserRole + 2: b"itemType",
        Qt.UserRole + 3: b"itemUrl",
        Qt.UserRole + 4: b"itemPublished",
        Qt.UserRole + 5: b"itemThumbnail",
        Qt.UserRole + 6: b"itemDuration",
        Qt.UserRole + 7: b"itemIsRead",
        Qt.UserRole + 8: b"itemDescription",
        Qt.UserRole + 9: b"itemLiveStatus",
        Qt.UserRole + 10: b"itemMediaUrl",
    }

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._items: list[ItemDTO] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._items)

    def roleNames(self) -> dict[int, bytes]:
        return self._ROLES

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        primary_media = next((m.url for m in item.media if m.role == "primary"), "")
        match role:
            case v if v == Qt.UserRole + 0:
                return item.id
            case v if v == Qt.UserRole + 1:
                return item.title
            case v if v == Qt.UserRole + 2:
                return item.type
            case v if v == Qt.UserRole + 3:
                return item.url
            case v if v == Qt.UserRole + 4:
                return item.published_iso
            case v if v == Qt.UserRole + 5:
                return item.thumbnail_url or ""
            case v if v == Qt.UserRole + 6:
                return item.duration or 0
            case v if v == Qt.UserRole + 7:
                return item.is_read
            case v if v == Qt.UserRole + 8:
                return item.description or ""
            case v if v == Qt.UserRole + 9:
                return item.live_status or ""
            case v if v == Qt.UserRole + 10:
                return primary_media
        return None

    def refresh(self, items: list[ItemDTO]) -> None:
        self.beginResetModel()
        self._items = items
        self.endResetModel()


class FeedCandidateModel(QAbstractListModel):
    _ROLES = {
        Qt.UserRole + 0: b"candidateUrl",
        Qt.UserRole + 1: b"candidateTitle",
        Qt.UserRole + 2: b"candidateDescription",
        Qt.UserRole + 3: b"candidateFaviconUrl",
        Qt.UserRole + 4: b"candidateSourceType",
        Qt.UserRole + 5: b"candidateIsSubscribed",
    }

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._candidates: list[FeedCandidateDTO] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._candidates)

    def roleNames(self) -> dict[int, bytes]:
        return self._ROLES

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._candidates):
            return None
        c = self._candidates[index.row()]
        match role:
            case v if v == Qt.UserRole + 0:
                return c.url
            case v if v == Qt.UserRole + 1:
                return c.title or c.url
            case v if v == Qt.UserRole + 2:
                return c.description or ""
            case v if v == Qt.UserRole + 3:
                return c.favicon_url or ""
            case v if v == Qt.UserRole + 4:
                return c.source_type
            case v if v == Qt.UserRole + 5:
                return c.is_subscribed
        return None

    def refresh(self, candidates: list[FeedCandidateDTO]) -> None:
        self.beginResetModel()
        self._candidates = list(candidates)
        self.endResetModel()

    def mark_subscribed(self, url: str) -> None:
        for i, c in enumerate(self._candidates):
            if c.url == url:
                self._candidates[i] = dataclasses.replace(c, is_subscribed=True)
                idx = self.index(i, 0)
                self.dataChanged.emit(idx, idx, [Qt.UserRole + 5])
                break


class AppController(QObject):
    feedsChanged = Signal()
    itemsChanged = Signal()
    errorOccurred = Signal(str)
    newItemsAvailable = Signal(int, int)

    searchStarted = Signal()
    searchFinished = Signal()
    searchError = Signal(str)
    searchCancelled = Signal()
    candidatesChanged = Signal()

    _searchResultReady = Signal(object)

    def __init__(
        self,
        subscription_service: SubscriptionService,
        item_service: ItemService,
        discovery_service: DiscoveryService,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._sub_svc = subscription_service
        self._item_svc = item_service
        self._discovery_svc = discovery_service
        self._feed_model = FeedListModel(self)
        self._item_model = ItemListModel(self)
        self._candidate_model = FeedCandidateModel(self)
        self._selected_feed_id: int = 0
        self._feed_sort: str = "alpha_asc"
        self._item_sort: str = "newest"
        self._result_cap: int = DEFAULT_RESULT_CAP
        self._last_query: str = ""
        self._search_generation: int = 0
        self._current_search_future: concurrent.futures.Future | None = None

        self._discovery_loop = asyncio.new_event_loop()

        def _run_discovery_loop() -> None:
            asyncio.set_event_loop(self._discovery_loop)
            try:
                self._discovery_loop.run_forever()
            finally:
                pending = asyncio.all_tasks(self._discovery_loop)
                for task in pending:
                    task.cancel()
                if pending:
                    self._discovery_loop.run_until_complete(
                        asyncio.gather(*pending, return_exceptions=True)
                    )
                self._discovery_loop.close()

        threading.Thread(
            target=_run_discovery_loop,
            daemon=True,
            name="meridian-discovery",
        ).start()

        self.newItemsAvailable.connect(self._refresh_on_new_items)
        self._searchResultReady.connect(self._apply_search_result)

    @Property(QObject, notify=feedsChanged)
    def feedModel(self) -> FeedListModel:
        return self._feed_model

    @Property(QObject, notify=itemsChanged)
    def itemModel(self) -> ItemListModel:
        return self._item_model

    @Property(QObject, notify=candidatesChanged)
    def candidateModel(self) -> FeedCandidateModel:
        return self._candidate_model

    @Property(int, notify=feedsChanged)
    def selectedFeedId(self) -> int:
        return self._selected_feed_id

    @Slot()
    def loadFeeds(self) -> None:
        feeds = self._sub_svc.list_feeds()
        feeds = self._sort_feeds(feeds)
        self._feed_model.refresh(feeds)
        self.feedsChanged.emit()

    @Slot(int)
    def selectFeed(self, feed_id: int) -> None:
        self._selected_feed_id = feed_id
        items = self._item_svc.get_items(feed_id)
        items = self._sort_items(items)
        self._item_model.refresh(items)
        self.itemsChanged.emit()

    @Slot(str)
    def setFeedSort(self, key: str) -> None:
        self._feed_sort = key
        self.loadFeeds()

    @Slot(str)
    def setItemSort(self, key: str) -> None:
        self._item_sort = key
        if self._selected_feed_id:
            items = self._item_svc.get_items(self._selected_feed_id)
            items = self._sort_items(items)
            self._item_model.refresh(items)
            self.itemsChanged.emit()

    @Slot(str)
    def subscribe(self, url: str) -> None:
        try:
            self._sub_svc.subscribe(url)
            self.loadFeeds()
        except Exception as exc:
            self.errorOccurred.emit(str(exc))

    @Slot("QVariantList")
    def bulkUnsubscribe(self, feed_ids: list) -> None:
        ids = {int(fid) for fid in feed_ids}
        for fid in ids:
            self._sub_svc.unsubscribe(fid)
            if self._selected_feed_id == fid:
                self._selected_feed_id = 0
                self._item_model.refresh([])
                self.itemsChanged.emit()
        self._feed_model.remove_rows_by_ids(ids)
        self.feedsChanged.emit()

    @Slot(int)
    def unsubscribe(self, feed_id: int) -> None:
        self._sub_svc.unsubscribe(feed_id)
        if self._selected_feed_id == feed_id:
            self._selected_feed_id = 0
            self._item_model.refresh([])
            self.itemsChanged.emit()
        self.loadFeeds()

    @Slot(int, str)
    def setFilter(self, feed_id: int, filter_expr: str) -> None:
        self._sub_svc.set_filter(feed_id, filter_expr.strip() or None)
        if self._selected_feed_id == feed_id:
            self.selectFeed(feed_id)

    @Slot(int)
    def markRead(self, item_id: int) -> None:
        self._item_svc.mark_read(item_id)
        if self._selected_feed_id:
            self.selectFeed(self._selected_feed_id)

    @Slot(int)
    def markAllRead(self, feed_id: int) -> None:
        self._item_svc.mark_all_read(feed_id)
        self.selectFeed(feed_id)
        self.loadFeeds()

    @Slot(str)
    def exportFeeds(self, file_url: str) -> None:
        path = Path(QUrl(file_url).toLocalFile())
        feeds = self._sub_svc.list_feeds()
        data = {
            "version": 1,
            "feeds": [
                {"url": f.url, "source_type": f.source_type, "title": f.title}
                for f in feeds
            ],
        }
        try:
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
            )
        except Exception as exc:
            _LOG.error("Export failed: %s", exc)
            self.errorOccurred.emit(f"Export failed: {exc}")

    @Slot(str)
    def importFeeds(self, file_url: str) -> None:
        path = Path(QUrl(file_url).toLocalFile())
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            _LOG.error("Import read failed: %s", exc)
            self.errorOccurred.emit(f"Import failed: {exc}")
            return
        imported = 0
        for entry in data.get("feeds", []):
            url = (entry.get("url") or "").strip()
            if not url:
                continue
            source_type = entry.get("source_type")
            title = (entry.get("title") or "").strip() or None
            try:
                self._sub_svc.subscribe(url, source_type=source_type, title=title)
                imported += 1
            except Exception as exc:
                _LOG.warning("Skipping %s: %s", url, exc)
        self.loadFeeds()
        _LOG.info("Imported %d feeds from %s", imported, path)

    @Slot(str)
    def searchFeeds(self, query: str) -> None:
        query = query.strip()
        if not query:
            return
        self._last_query = query
        if self._current_search_future and not self._current_search_future.done():
            self._current_search_future.cancel()
        self._search_generation += 1
        generation = self._search_generation
        self.searchStarted.emit()

        async def _run() -> list[FeedCandidateDTO]:
            return await self._discovery_svc.search(
                query, limit=self._result_cap, page=0
            )

        future = asyncio.run_coroutine_threadsafe(_run(), self._discovery_loop)
        self._current_search_future = future

        def _on_done(f: concurrent.futures.Future) -> None:
            if f.cancelled():
                return
            if generation != self._search_generation:  # pragma: no cover
                return
            exc = f.exception()
            if exc is not None:
                self.searchError.emit(str(exc))
                return
            self._searchResultReady.emit(f.result())

        future.add_done_callback(_on_done)

    @Slot()
    def cancelSearch(self) -> None:
        if self._current_search_future and not self._current_search_future.done():
            self._search_generation += 1
            self._current_search_future.cancel()
            self.searchCancelled.emit()

    @Slot(int)
    def setResultCap(self, cap: int) -> None:
        self._result_cap = cap
        if self._last_query:
            self.searchFeeds(self._last_query)

    @Slot(str)
    def subscribeFromDiscovery(self, url: str) -> None:
        try:
            self._sub_svc.subscribe(url)
            self._candidate_model.mark_subscribed(url)
            self.loadFeeds()
        except Exception as exc:
            _LOG.warning("Discovery subscribe failed for %s: %s", url, exc)
            self.errorOccurred.emit(str(exc))

    @Slot("QVariantList")
    def bulkSubscribeFromDiscovery(self, urls: list) -> None:
        for url in urls:
            try:
                self._sub_svc.subscribe(str(url))
                self._candidate_model.mark_subscribed(str(url))
            except Exception as exc:
                _LOG.warning("Skip discovery subscribe %s: %s", url, exc)
        self.loadFeeds()

    @Slot(object)
    def _apply_search_result(self, candidates: object) -> None:
        self._candidate_model.refresh(candidates)  # type: ignore[arg-type]
        self.candidatesChanged.emit()
        self.searchFinished.emit()

    def _sort_feeds(self, feeds: list) -> list:
        match self._feed_sort:
            case "alpha_desc":
                return sorted(
                    feeds, key=lambda f: (f.title or f.url).lower(), reverse=True
                )
            case "unread":
                return sorted(feeds, key=lambda f: f.unread_count, reverse=True)
            case _:  # alpha_asc
                return sorted(feeds, key=lambda f: (f.title or f.url).lower())

    def _sort_items(self, items: list) -> list:
        match self._item_sort:
            case "oldest":
                return sorted(items, key=lambda i: i.published_iso)
            case "alpha":
                return sorted(items, key=lambda i: i.title.lower())
            case _:  # newest
                return sorted(items, key=lambda i: i.published_iso, reverse=True)

    def notify_new_items(self, feed_id: int, count: int) -> None:
        # Thread-safe: only emit signal; _refresh_on_new_items runs on Qt thread via auto-queued connection  # noqa: E501
        self.newItemsAvailable.emit(feed_id, count)

    def shutdown(self) -> None:
        if self._current_search_future and not self._current_search_future.done():
            self._current_search_future.cancel()
        if not self._discovery_loop.is_closed():
            self._discovery_loop.call_soon_threadsafe(self._discovery_loop.stop)

    @Slot(int, int)
    def _refresh_on_new_items(self, feed_id: int, count: int) -> None:
        self.loadFeeds()
        if self._selected_feed_id == feed_id:
            self.selectFeed(feed_id)
