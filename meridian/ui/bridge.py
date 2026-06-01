"""QML bridge: exposes Application services as QML-callable QObject."""
from __future__ import annotations

import json
import logging
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

from meridian.application.dto.feed_dto import FeedDTO
from meridian.application.dto.item_dto import ItemDTO
from meridian.application.services.item_service import ItemService
from meridian.application.services.subscription_service import SubscriptionService


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


class AppController(QObject):
    feedsChanged = Signal()
    itemsChanged = Signal()
    errorOccurred = Signal(str)
    newItemsAvailable = Signal(int, int)

    def __init__(
        self,
        subscription_service: SubscriptionService,
        item_service: ItemService,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._sub_svc = subscription_service
        self._item_svc = item_service
        self._feed_model = FeedListModel(self)
        self._item_model = ItemListModel(self)
        self._selected_feed_id: int = 0
        self._feed_sort: str = "alpha_asc"
        self._item_sort: str = "newest"
        self.newItemsAvailable.connect(self._refresh_on_new_items)

    @Property(QObject, notify=feedsChanged)
    def feedModel(self) -> FeedListModel:
        return self._feed_model

    @Property(QObject, notify=itemsChanged)
    def itemModel(self) -> ItemListModel:
        return self._item_model

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

    @Slot('QVariantList')
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
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
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

    def _sort_feeds(self, feeds: list) -> list:
        match self._feed_sort:
            case "alpha_desc":
                return sorted(feeds, key=lambda f: (f.title or f.url).lower(), reverse=True)
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
        # Thread-safe: only emit signal; _refresh_on_new_items runs on Qt thread via auto-queued connection
        self.newItemsAvailable.emit(feed_id, count)

    @Slot(int, int)
    def _refresh_on_new_items(self, feed_id: int, count: int) -> None:
        self.loadFeeds()
        if self._selected_feed_id == feed_id:
            self.selectFeed(feed_id)
