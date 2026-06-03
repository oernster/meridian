"""UI bridge tests using real QApplication (no Qt mocking)."""

import json
import tempfile
import threading
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from meridian.application.dto.feed_candidate_dto import FeedCandidateDTO
from meridian.application.dto.feed_dto import FeedDTO
from meridian.application.dto.item_dto import ItemDTO
from meridian.ui.bridge import (
    AppController,
    FeedCandidateModel,
    FeedListModel,
    ItemListModel,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _feed_dto(feed_id: int = 1, unread: int = 0) -> FeedDTO:
    return FeedDTO(
        id=feed_id,
        url=f"https://example.com/feed/{feed_id}",
        source_type="mfeed",
        title=f"Feed {feed_id}",
        description=None,
        icon=None,
        language=None,
        filter_expr=None,
        unread_count=unread,
    )


def _item_dto(item_id: int = 1) -> ItemDTO:
    return ItemDTO(
        id=item_id,
        feed_id=1,
        item_id=f"https://example.com/item/{item_id}",
        type="article",
        title=f"Item {item_id}",
        url=f"https://example.com/item/{item_id}",
        published_iso="2026-01-01T00:00:00+00:00",
        description="A test item",
        thumbnail_url=None,
        duration=None,
        is_read=False,
    )


class TestFeedListModel:
    def test_empty_model(self, qapp):
        model = FeedListModel()
        assert model.rowCount() == 0

    def test_refresh_sets_rows(self, qapp):
        model = FeedListModel()
        model.refresh([_feed_dto(1), _feed_dto(2)])
        assert model.rowCount() == 2

    def test_data_all_roles(self, qapp):
        from PySide6.QtCore import Qt

        model = FeedListModel()
        model.refresh([_feed_dto(1, unread=3)])
        idx = model.index(0, 0)
        assert model.data(idx, Qt.UserRole + 0) == 1  # feedId
        assert model.data(idx, Qt.UserRole + 1) is not None  # feedUrl
        assert model.data(idx, Qt.UserRole + 2) == "Feed 1"  # feedTitle
        assert model.data(idx, Qt.UserRole + 3) == ""  # feedIcon (None -> "")
        assert model.data(idx, Qt.UserRole + 4) == "mfeed"  # feedSourceType
        assert model.data(idx, Qt.UserRole + 5) == 3  # feedUnreadCount
        assert model.data(idx, Qt.UserRole + 6) == ""  # feedDescription (None -> "")
        assert model.data(idx, Qt.UserRole + 7) == ""  # feedFilterExpr (None -> "")
        assert model.data(idx, 9999) is None  # unknown role

    def test_data_feed_filter_expr_present(self, qapp):
        from PySide6.QtCore import Qt

        model = FeedListModel()
        dto = FeedDTO(
            id=1,
            url="https://example.com/feed/1",
            source_type="mfeed",
            title="Feed 1",
            description=None,
            icon=None,
            language=None,
            filter_expr="type:video",
            unread_count=0,
        )
        model.refresh([dto])
        idx = model.index(0, 0)
        assert model.data(idx, Qt.UserRole + 7) == "type:video"

    def test_data_feed_title_fallback_to_url(self, qapp):
        from PySide6.QtCore import Qt

        model = FeedListModel()
        dto = FeedDTO(
            id=1,
            url="https://example.com/feed",
            source_type="mfeed",
            title=None,
            description=None,
            icon=None,
            language=None,
            filter_expr=None,
            unread_count=0,
        )
        model.refresh([dto])
        idx = model.index(0, 0)
        assert model.data(idx, Qt.UserRole + 2) == "https://example.com/feed"

    def test_data_invalid_index(self, qapp):
        from PySide6.QtCore import Qt

        model = FeedListModel()
        idx = model.index(99, 0)
        assert model.data(idx, Qt.UserRole + 0) is None

    def test_role_names(self, qapp):
        model = FeedListModel()
        assert b"feedId" in model.roleNames().values()

    def test_remove_rows_by_ids(self, qapp):
        from PySide6.QtCore import Qt

        model = FeedListModel()
        model.refresh([_feed_dto(1), _feed_dto(2), _feed_dto(3)])
        model.remove_rows_by_ids({1, 3})
        assert model.rowCount() == 1
        assert model.data(model.index(0, 0), Qt.UserRole + 0) == 2

    def test_remove_rows_by_ids_unknown_ids_no_op(self, qapp):
        model = FeedListModel()
        model.refresh([_feed_dto(1), _feed_dto(2)])
        model.remove_rows_by_ids({99})
        assert model.rowCount() == 2


class TestItemListModel:
    def test_empty_model(self, qapp):
        model = ItemListModel()
        assert model.rowCount() == 0

    def test_refresh_sets_rows(self, qapp):
        model = ItemListModel()
        model.refresh([_item_dto(1), _item_dto(2)])
        assert model.rowCount() == 2

    def test_data_all_roles(self, qapp):
        from PySide6.QtCore import Qt
        from meridian.application.dto.item_dto import MediaDTO

        model = ItemListModel()
        dto = ItemDTO(
            id=1,
            feed_id=1,
            item_id="https://example.com/item/1",
            type="video",
            title="Item 1",
            url="https://example.com/item/1",
            published_iso="2026-01-01T00:00:00+00:00",
            description="A description",
            thumbnail_url="https://example.com/thumb.jpg",
            duration=600,
            is_read=False,
            language="en",
            live_status="live",
            media=(
                MediaDTO(
                    url="https://example.com/video.mp4",
                    mime_type="video/mp4",
                    role="primary",
                ),
            ),
        )
        model.refresh([dto])
        idx = model.index(0, 0)
        assert model.data(idx, Qt.UserRole + 0) == 1
        assert model.data(idx, Qt.UserRole + 1) == "Item 1"
        assert model.data(idx, Qt.UserRole + 2) == "video"
        assert model.data(idx, Qt.UserRole + 3) == "https://example.com/item/1"
        assert "2026" in model.data(idx, Qt.UserRole + 4)
        assert model.data(idx, Qt.UserRole + 5) == "https://example.com/thumb.jpg"
        assert model.data(idx, Qt.UserRole + 6) == 600
        assert model.data(idx, Qt.UserRole + 7) is False
        assert model.data(idx, Qt.UserRole + 8) == "A description"
        assert model.data(idx, Qt.UserRole + 9) == "live"
        assert model.data(idx, Qt.UserRole + 10) == "https://example.com/video.mp4"
        assert model.data(idx, 9999) is None

    def test_data_item_no_media_url(self, qapp):
        from PySide6.QtCore import Qt

        model = ItemListModel()
        model.refresh([_item_dto(1)])
        idx = model.index(0, 0)
        assert model.data(idx, Qt.UserRole + 10) == ""

    def test_data_invalid_index(self, qapp):
        from PySide6.QtCore import Qt

        model = ItemListModel()
        idx = model.index(0, 0)
        assert model.data(idx, Qt.UserRole + 0) is None

    def test_role_names(self, qapp):
        model = ItemListModel()
        assert b"itemTitle" in model.roleNames().values()


def _candidate_dto(
    url: str = "https://example.com/feed", subscribed: bool = False
) -> FeedCandidateDTO:
    return FeedCandidateDTO(
        url=url,
        title="Feed",
        description="A feed",
        favicon_url=None,
        source_type="rss",
        is_subscribed=subscribed,
    )


def _make_controller(qapp, sub_svc, item_svc, discovery_svc=None):
    if discovery_svc is None:
        discovery_svc = MagicMock()
        discovery_svc.search = AsyncMock(return_value=[])
    return AppController(sub_svc, item_svc, discovery_svc)


class TestFeedCandidateModel:
    def test_empty_model(self, qapp):
        model = FeedCandidateModel()
        assert model.rowCount() == 0

    def test_refresh_sets_rows(self, qapp):
        model = FeedCandidateModel()
        model.refresh([_candidate_dto(), _candidate_dto("https://b.com/feed")])
        assert model.rowCount() == 2

    def test_data_all_roles(self, qapp):
        from PySide6.QtCore import Qt

        model = FeedCandidateModel()
        model.refresh([_candidate_dto()])
        idx = model.index(0, 0)
        assert model.data(idx, Qt.UserRole + 0) == "https://example.com/feed"
        assert model.data(idx, Qt.UserRole + 1) == "Feed"
        assert model.data(idx, Qt.UserRole + 2) == "A feed"
        assert model.data(idx, Qt.UserRole + 3) == ""
        assert model.data(idx, Qt.UserRole + 4) == "rss"
        assert model.data(idx, Qt.UserRole + 5) is False
        assert model.data(idx, 9999) is None

    def test_data_title_fallback_to_url(self, qapp):
        from PySide6.QtCore import Qt

        model = FeedCandidateModel()
        dto = FeedCandidateDTO(
            url="https://example.com/feed",
            title=None,
            description=None,
            favicon_url=None,
            source_type="rss",
        )
        model.refresh([dto])
        idx = model.index(0, 0)
        assert model.data(idx, Qt.UserRole + 1) == "https://example.com/feed"

    def test_data_invalid_index(self, qapp):
        from PySide6.QtCore import Qt

        model = FeedCandidateModel()
        assert model.data(model.index(99, 0), Qt.UserRole + 0) is None

    def test_role_names(self, qapp):
        model = FeedCandidateModel()
        assert b"candidateUrl" in model.roleNames().values()

    def test_mark_subscribed(self, qapp):
        from PySide6.QtCore import Qt

        model = FeedCandidateModel()
        model.refresh(
            [_candidate_dto("https://a.com"), _candidate_dto("https://b.com")]
        )
        model.mark_subscribed("https://a.com")
        assert model.data(model.index(0, 0), Qt.UserRole + 5) is True
        assert model.data(model.index(1, 0), Qt.UserRole + 5) is False

    def test_mark_subscribed_unknown_url_no_op(self, qapp):
        model = FeedCandidateModel()
        model.refresh([_candidate_dto()])
        model.mark_subscribed("https://nonexistent.com/feed")
        assert model.rowCount() == 1


class TestAppController:
    def setup_method(self):
        self.sub_svc = MagicMock()
        self.item_svc = MagicMock()
        self.discovery_svc = MagicMock()
        self.discovery_svc.search = AsyncMock(return_value=[])

    def test_load_feeds(self, qapp):
        self.sub_svc.list_feeds.return_value = [_feed_dto(1), _feed_dto(2)]
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.loadFeeds()
        assert controller.feedModel.rowCount() == 2

    def test_select_feed(self, qapp):
        self.item_svc.get_items.return_value = [_item_dto(1)]
        self.sub_svc.list_feeds.return_value = []
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.selectFeed(1)
        assert controller.itemModel.rowCount() == 1
        assert controller.selectedFeedId == 1

    def test_subscribe_success(self, qapp):
        self.sub_svc.subscribe.return_value = _feed_dto(5)
        self.sub_svc.list_feeds.return_value = [_feed_dto(5)]
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.subscribe("https://example.com/feed/5")
        self.sub_svc.subscribe.assert_called_once_with("https://example.com/feed/5")

    def test_subscribe_error_emits_signal(self, qapp):
        self.sub_svc.subscribe.side_effect = ValueError("bad URL")
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        errors = []
        controller.errorOccurred.connect(errors.append)
        controller.subscribe("http://insecure.com/feed")
        assert len(errors) == 1
        assert "bad URL" in errors[0]

    def test_unsubscribe_clears_items_if_selected(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        self.item_svc.get_items.return_value = [_item_dto(1)]
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.selectFeed(1)
        controller.unsubscribe(1)
        assert controller.selectedFeedId == 0
        assert controller.itemModel.rowCount() == 0

    def test_unsubscribe_other_feed_no_clear(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        self.item_svc.get_items.return_value = [_item_dto(1)]
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.selectFeed(1)
        controller.unsubscribe(99)
        assert controller.selectedFeedId == 1

    def test_set_filter(self, qapp):
        self.item_svc.get_items.return_value = []
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller._selected_feed_id = 1
        controller.setFilter(1, "type:video")
        self.sub_svc.set_filter.assert_called_once_with(1, "type:video")

    def test_set_filter_other_feed_no_reload(self, qapp):
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller._selected_feed_id = 1
        controller.setFilter(99, "type:video")
        self.item_svc.get_items.assert_not_called()

    def test_set_filter_empty_clears(self, qapp):
        self.item_svc.get_items.return_value = []
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller._selected_feed_id = 1
        controller.setFilter(1, "   ")
        self.sub_svc.set_filter.assert_called_once_with(1, None)

    def test_mark_read(self, qapp):
        self.item_svc.get_items.return_value = []
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller._selected_feed_id = 1
        controller.markRead(5)
        self.item_svc.mark_read.assert_called_once_with(5)

    def test_mark_read_no_feed_selected(self, qapp):
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.markRead(5)
        self.item_svc.mark_read.assert_called_once_with(5)
        self.item_svc.get_items.assert_not_called()

    def test_mark_all_read(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        self.item_svc.get_items.return_value = []
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.markAllRead(1)
        self.item_svc.mark_all_read.assert_called_once_with(1)

    def test_notify_new_items(self, qapp):
        self.sub_svc.list_feeds.return_value = [_feed_dto(1, unread=3)]
        self.item_svc.get_items.return_value = []
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        signals = []
        controller.newItemsAvailable.connect(lambda fid, n: signals.append((fid, n)))
        controller.notify_new_items(1, 3)
        assert (1, 3) in signals

    def test_notify_new_items_reloads_selected(self, qapp):
        self.sub_svc.list_feeds.return_value = [_feed_dto(1, unread=3)]
        self.item_svc.get_items.return_value = [_item_dto(1)]
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller._selected_feed_id = 1
        controller.notify_new_items(1, 2)
        self.item_svc.get_items.assert_called_with(1)

    def test_set_feed_sort_alpha_asc(self, qapp):
        self.sub_svc.list_feeds.return_value = [_feed_dto(1), _feed_dto(2)]
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.setFeedSort("alpha_asc")
        assert controller._feed_sort == "alpha_asc"
        assert controller.feedModel.rowCount() == 2

    def test_set_feed_sort_alpha_desc(self, qapp):
        feeds = [
            FeedDTO(
                id=1,
                url="https://example.com/feed/1",
                source_type="mfeed",
                title="Zebra",
                description=None,
                icon=None,
                language=None,
                filter_expr=None,
                unread_count=0,
            ),
            FeedDTO(
                id=2,
                url="https://example.com/feed/2",
                source_type="mfeed",
                title="Apple",
                description=None,
                icon=None,
                language=None,
                filter_expr=None,
                unread_count=0,
            ),
        ]
        self.sub_svc.list_feeds.return_value = feeds
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.setFeedSort("alpha_desc")
        from PySide6.QtCore import Qt

        first = controller.feedModel.data(
            controller.feedModel.index(0, 0), Qt.UserRole + 2
        )
        assert first == "Zebra"

    def test_set_feed_sort_unread(self, qapp):
        feeds = [_feed_dto(1, unread=5), _feed_dto(2, unread=20)]
        self.sub_svc.list_feeds.return_value = feeds
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.setFeedSort("unread")
        from PySide6.QtCore import Qt

        first_unread = controller.feedModel.data(
            controller.feedModel.index(0, 0), Qt.UserRole + 5
        )
        assert first_unread == 20

    def test_set_item_sort_newest(self, qapp):
        items = [
            _item_dto(1),
            ItemDTO(
                id=2,
                feed_id=1,
                item_id="https://example.com/item/2",
                type="article",
                title="Item 2",
                url="https://example.com/item/2",
                published_iso="2025-01-01T00:00:00+00:00",
                description=None,
                thumbnail_url=None,
                duration=None,
                is_read=False,
            ),
        ]
        self.item_svc.get_items.return_value = items
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller._selected_feed_id = 1
        controller.setItemSort("newest")
        from PySide6.QtCore import Qt

        first_pub = controller.itemModel.data(
            controller.itemModel.index(0, 0), Qt.UserRole + 4
        )
        assert "2026" in first_pub

    def test_set_item_sort_oldest(self, qapp):
        items = [
            _item_dto(1),
            ItemDTO(
                id=2,
                feed_id=1,
                item_id="https://example.com/item/2",
                type="article",
                title="Item 2",
                url="https://example.com/item/2",
                published_iso="2025-01-01T00:00:00+00:00",
                description=None,
                thumbnail_url=None,
                duration=None,
                is_read=False,
            ),
        ]
        self.item_svc.get_items.return_value = items
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller._selected_feed_id = 1
        controller.setItemSort("oldest")
        from PySide6.QtCore import Qt

        first_pub = controller.itemModel.data(
            controller.itemModel.index(0, 0), Qt.UserRole + 4
        )
        assert "2025" in first_pub

    def test_set_item_sort_alpha(self, qapp):
        items = [
            ItemDTO(
                id=1,
                feed_id=1,
                item_id="https://example.com/item/1",
                type="article",
                title="Zebra Article",
                url="https://example.com/item/1",
                published_iso="2026-01-01T00:00:00+00:00",
                description=None,
                thumbnail_url=None,
                duration=None,
                is_read=False,
            ),
            ItemDTO(
                id=2,
                feed_id=1,
                item_id="https://example.com/item/2",
                type="article",
                title="Apple Article",
                url="https://example.com/item/2",
                published_iso="2026-01-02T00:00:00+00:00",
                description=None,
                thumbnail_url=None,
                duration=None,
                is_read=False,
            ),
        ]
        self.item_svc.get_items.return_value = items
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller._selected_feed_id = 1
        controller.setItemSort("alpha")
        from PySide6.QtCore import Qt

        first_title = controller.itemModel.data(
            controller.itemModel.index(0, 0), Qt.UserRole + 1
        )
        assert first_title == "Apple Article"

    def test_set_item_sort_no_feed_selected_no_op(self, qapp):
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.setItemSort("newest")
        self.item_svc.get_items.assert_not_called()

    def test_bulk_unsubscribe_clears_selected(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        self.item_svc.get_items.return_value = [_item_dto(1)]
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.selectFeed(1)
        controller.bulkUnsubscribe([1, 2])
        assert controller.selectedFeedId == 0
        assert controller.itemModel.rowCount() == 0
        assert self.sub_svc.unsubscribe.call_count == 2

    def test_bulk_unsubscribe_non_selected_feed(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        self.item_svc.get_items.return_value = [_item_dto(1)]
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.selectFeed(1)
        controller.bulkUnsubscribe([99])
        assert controller.selectedFeedId == 1

    def test_export_feeds(self, qapp):
        feeds = [_feed_dto(1), _feed_dto(2)]
        self.sub_svc.list_feeds.return_value = feeds
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        controller.exportFeeds(tmp.as_uri())
        data = json.loads(tmp.read_text())
        assert data["version"] == 1
        assert len(data["feeds"]) == 2
        tmp.unlink()

    def test_export_feeds_write_error_emits_signal(self, qapp):
        self.sub_svc.list_feeds.return_value = [_feed_dto(1)]
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        errors = []
        controller.errorOccurred.connect(errors.append)
        controller.exportFeeds("file:///nonexistent_dir/out.json")
        assert len(errors) == 1

    def test_import_feeds(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        data = {
            "version": 1,
            "feeds": [
                {
                    "url": "https://example.com/feed/1",
                    "source_type": "rss",
                    "title": "Feed One",
                },
                {
                    "url": "https://example.com/feed/2",
                    "source_type": "atom",
                    "title": None,
                },
            ],
        }
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(data, f)
            tmp = Path(f.name)
        controller.importFeeds(tmp.as_uri())
        assert self.sub_svc.subscribe.call_count == 2
        tmp.unlink()

    def test_import_feeds_skips_bad_url(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        self.sub_svc.subscribe.side_effect = ValueError("bad url")
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        data = {
            "version": 1,
            "feeds": [{"url": "https://example.com/feed", "source_type": "rss"}],
        }
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(data, f)
            tmp = Path(f.name)
        controller.importFeeds(tmp.as_uri())
        tmp.unlink()

    def test_import_feeds_skips_empty_url(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        data = {
            "version": 1,
            "feeds": [{"url": "", "source_type": "rss"}, {"url": "   "}],
        }
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(data, f)
            tmp = Path(f.name)
        controller.importFeeds(tmp.as_uri())
        self.sub_svc.subscribe.assert_not_called()
        tmp.unlink()

    def test_import_feeds_bad_file_emits_error(self, qapp):
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        errors = []
        controller.errorOccurred.connect(errors.append)
        controller.importFeeds("file:///nonexistent/path.json")
        assert len(errors) == 1

    def test_subscribe_from_discovery_success(self, qapp):
        self.sub_svc.subscribe.return_value = _feed_dto(1)
        self.sub_svc.list_feeds.return_value = [_feed_dto(1)]
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller._candidate_model.refresh(
            [_candidate_dto("https://example.com/feed")]
        )
        controller.subscribeFromDiscovery("https://example.com/feed")
        self.sub_svc.subscribe.assert_called_once_with("https://example.com/feed")

    def test_subscribe_from_discovery_marks_subscribed_in_model(self, qapp):
        from PySide6.QtCore import Qt

        self.sub_svc.subscribe.return_value = _feed_dto(1)
        self.sub_svc.list_feeds.return_value = []
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller._candidate_model.refresh(
            [_candidate_dto("https://example.com/feed")]
        )
        controller.subscribeFromDiscovery("https://example.com/feed")
        idx = controller.candidateModel.index(0, 0)
        assert controller.candidateModel.data(idx, Qt.UserRole + 5) is True

    def test_subscribe_from_discovery_error_emits_signal(self, qapp):
        self.sub_svc.subscribe.side_effect = ValueError("bad url")
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        errors = []
        controller.errorOccurred.connect(errors.append)
        controller.subscribeFromDiscovery("https://example.com/feed")
        assert len(errors) == 1

    def test_bulk_subscribe_from_discovery(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller._candidate_model.refresh(
            [
                _candidate_dto("https://a.com/feed"),
                _candidate_dto("https://b.com/feed"),
            ]
        )
        controller.bulkSubscribeFromDiscovery(
            ["https://a.com/feed", "https://b.com/feed"]
        )
        assert self.sub_svc.subscribe.call_count == 2

    def test_bulk_subscribe_skips_failures(self, qapp):
        self.sub_svc.list_feeds.return_value = []

        def _side(url, **kw):
            if "a.com" in url:
                raise ValueError("bad")

        self.sub_svc.subscribe.side_effect = _side
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller._candidate_model.refresh([_candidate_dto("https://b.com/feed")])
        controller.bulkSubscribeFromDiscovery(
            ["https://a.com/feed", "https://b.com/feed"]
        )
        assert self.sub_svc.subscribe.call_count == 2

    def test_set_result_cap(self, qapp):
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.setResultCap(50)
        assert controller._result_cap == 50

    def test_set_result_cap_retriggers_search_if_query_set(self, qapp):
        started = []
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.searchStarted.connect(lambda: started.append(1))
        controller._last_query = "python"
        controller.setResultCap(100)
        assert len(started) == 1

    def test_cancel_search_emits_cancelled_when_no_future(self, qapp):
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        cancelled = []
        controller.searchCancelled.connect(lambda: cancelled.append(1))
        controller.cancelSearch()
        assert cancelled == []

    def test_search_feeds_empty_query_no_op(self, qapp):
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        started = []
        controller.searchStarted.connect(lambda: started.append(1))
        controller.searchFeeds("   ")
        assert started == []

    def test_search_feeds_emits_started(self, qapp):
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        started = []
        controller.searchStarted.connect(lambda: started.append(1))
        controller.searchFeeds("python")
        assert len(started) == 1
        controller.shutdown()

    def test_candidate_model_property(self, qapp):
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        assert controller.candidateModel is not None
        assert isinstance(controller.candidateModel, FeedCandidateModel)

    def test_search_emits_error_signal_on_failure(self, qapp):
        import time

        from PySide6.QtWidgets import QApplication as _QApp
        from meridian.application.interfaces.discovery_fetcher import DiscoveryError

        async def _failing(*args, **kwargs):
            raise DiscoveryError("network error")

        self.discovery_svc.search = _failing
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        errors = []
        controller.searchError.connect(errors.append)
        controller.searchFeeds("python")
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and not errors:
            _QApp.processEvents()
            time.sleep(0.01)
        assert len(errors) == 1
        assert "network error" in errors[0]
        controller.shutdown()

    def test_search_populates_candidate_model_on_success(self, qapp):
        import time

        from PySide6.QtWidgets import QApplication as _QApp

        candidates = [_candidate_dto("https://python.org/feed")]

        async def _fast_search(*args, **kwargs):
            return candidates

        self.discovery_svc.search = _fast_search
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        finished = []
        controller.searchFinished.connect(lambda: finished.append(1))
        controller.searchFeeds("python")
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and not finished:
            _QApp.processEvents()
            time.sleep(0.01)
        assert len(finished) == 1
        assert controller.candidateModel.rowCount() == 1
        controller.shutdown()

    def test_cancel_active_search_emits_cancelled(self, qapp):
        started_event = threading.Event()

        async def _slow_with_signal(*args, **kwargs):
            import asyncio as _asyncio

            started_event.set()
            await _asyncio.sleep(30)
            return []

        self.discovery_svc.search = _slow_with_signal
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        cancelled = []
        controller.searchCancelled.connect(lambda: cancelled.append(1))
        controller.searchFeeds("python")
        started_event.wait(timeout=2.0)
        controller.cancelSearch()
        assert len(cancelled) == 1
        controller.shutdown()

    def test_search_feeds_cancels_prior_future(self, qapp):
        started_event = threading.Event()

        async def _slow(*args, **kwargs):
            import asyncio as _asyncio

            started_event.set()
            await _asyncio.sleep(30)
            return []

        self.discovery_svc.search = _slow
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.searchFeeds("python")
        started_event.wait(timeout=2.0)
        started2 = []
        controller.searchStarted.connect(lambda: started2.append(1))
        controller.searchFeeds("java")
        assert len(started2) == 1
        controller.shutdown()

    def test_shutdown_with_no_active_future(self, qapp):
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.shutdown()

    def test_shutdown_while_search_in_progress_drains_tasks(self, qapp):
        started_event = threading.Event()

        async def _blocking(*args, **kwargs):
            import asyncio as _asyncio

            started_event.set()
            await _asyncio.sleep(30)
            return []

        self.discovery_svc.search = _blocking
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.searchFeeds("python")
        started_event.wait(timeout=2.0)
        controller.shutdown()

    def test_shutdown_when_loop_already_closed(self, qapp):
        import time

        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.shutdown()
        deadline = time.monotonic() + 2.0
        while (
            time.monotonic() < deadline and not controller._discovery_loop.is_closed()
        ):
            time.sleep(0.01)
        controller.shutdown()

    def test_discovery_loop_drains_pending_tasks_on_direct_stop(self, qapp):
        import time

        started_event = threading.Event()

        async def _blocking(*args, **kwargs):
            import asyncio as _asyncio

            started_event.set()
            await _asyncio.sleep(30)
            return []

        self.discovery_svc.search = _blocking
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.searchFeeds("python")
        started_event.wait(timeout=2.0)
        controller._discovery_loop.call_soon_threadsafe(controller._discovery_loop.stop)
        deadline = time.monotonic() + 3.0
        while (
            time.monotonic() < deadline and not controller._discovery_loop.is_closed()
        ):
            time.sleep(0.01)
        assert controller._discovery_loop.is_closed()

    def test_update_feed_url_success(self, qapp):
        self.sub_svc.list_feeds.return_value = [_feed_dto(1)]
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.updateFeedUrl(1, "https://new.example.com/feed")
        self.sub_svc.update_url.assert_called_once_with(
            1, "https://new.example.com/feed"
        )

    def test_update_feed_url_error_emits_signal(self, qapp):
        self.sub_svc.update_url.side_effect = ValueError("invalid url")
        controller = _make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        errors = []
        controller.errorOccurred.connect(errors.append)
        controller.updateFeedUrl(1, "not-a-url")
        assert len(errors) == 1
        assert "invalid url" in errors[0]
