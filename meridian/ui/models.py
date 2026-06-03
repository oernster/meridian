"""QAbstractListModel subclasses for QML data binding."""

from __future__ import annotations

import dataclasses

from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Qt

from meridian.application.dto.feed_candidate_dto import FeedCandidateDTO
from meridian.application.dto.feed_dto import FeedDTO
from meridian.application.dto.item_dto import ItemDTO


class FeedListModel(QAbstractListModel):
    _ROLES = {
        Qt.UserRole + 0: b"feedId",
        Qt.UserRole + 1: b"feedUrl",
        Qt.UserRole + 2: b"feedTitle",
        Qt.UserRole + 3: b"feedIcon",
        Qt.UserRole + 4: b"feedSourceType",
        Qt.UserRole + 5: b"feedUnreadCount",
        Qt.UserRole + 6: b"feedDescription",
        Qt.UserRole + 7: b"feedFilter",
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
            case v if v == Qt.UserRole + 7:
                return feed.filter_expr or ""
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
