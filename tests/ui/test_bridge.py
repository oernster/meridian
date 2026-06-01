"""UI bridge tests using real QApplication (no Qt mocking)."""
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtWidgets import QApplication

from meridian.application.dto.feed_dto import FeedDTO
from meridian.application.dto.item_dto import ItemDTO
from meridian.ui.bridge import AppController, FeedListModel, ItemListModel


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
        assert model.data(idx, Qt.UserRole + 0) == 1       # feedId
        assert model.data(idx, Qt.UserRole + 1) is not None # feedUrl
        assert model.data(idx, Qt.UserRole + 2) == "Feed 1" # feedTitle
        assert model.data(idx, Qt.UserRole + 3) == ""       # feedIcon (None -> "")
        assert model.data(idx, Qt.UserRole + 4) == "mfeed"  # feedSourceType
        assert model.data(idx, Qt.UserRole + 5) == 3        # feedUnreadCount
        assert model.data(idx, Qt.UserRole + 6) == ""       # feedDescription (None -> "")
        assert model.data(idx, 9999) is None                # unknown role

    def test_data_feed_title_fallback_to_url(self, qapp):
        from PySide6.QtCore import Qt
        model = FeedListModel()
        dto = FeedDTO(
            id=1, url="https://example.com/feed", source_type="mfeed",
            title=None, description=None, icon=None, language=None,
            filter_expr=None, unread_count=0,
        )
        model.refresh([dto])
        idx = model.index(0, 0)
        assert model.data(idx, Qt.UserRole + 2) == "https://example.com/feed"

    def test_data_invalid_index(self, qapp):
        from PySide6.QtCore import Qt, QModelIndex
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
            id=1, feed_id=1, item_id="https://example.com/item/1",
            type="video", title="Item 1",
            url="https://example.com/item/1",
            published_iso="2026-01-01T00:00:00+00:00",
            description="A description",
            thumbnail_url="https://example.com/thumb.jpg",
            duration=600,
            is_read=False,
            language="en",
            live_status="live",
            media=(MediaDTO(url="https://example.com/video.mp4", mime_type="video/mp4", role="primary"),),
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


class TestAppController:
    def setup_method(self):
        self.sub_svc = MagicMock()
        self.item_svc = MagicMock()

    def test_load_feeds(self, qapp):
        self.sub_svc.list_feeds.return_value = [_feed_dto(1), _feed_dto(2)]
        controller = AppController(self.sub_svc, self.item_svc)
        controller.loadFeeds()
        assert controller.feedModel.rowCount() == 2

    def test_select_feed(self, qapp):
        self.item_svc.get_items.return_value = [_item_dto(1)]
        self.sub_svc.list_feeds.return_value = []
        controller = AppController(self.sub_svc, self.item_svc)
        controller.selectFeed(1)
        assert controller.itemModel.rowCount() == 1
        assert controller.selectedFeedId == 1

    def test_subscribe_success(self, qapp):
        self.sub_svc.subscribe.return_value = _feed_dto(5)
        self.sub_svc.list_feeds.return_value = [_feed_dto(5)]
        controller = AppController(self.sub_svc, self.item_svc)
        controller.subscribe("https://example.com/feed/5")
        self.sub_svc.subscribe.assert_called_once_with("https://example.com/feed/5")

    def test_subscribe_error_emits_signal(self, qapp):
        self.sub_svc.subscribe.side_effect = ValueError("bad URL")
        controller = AppController(self.sub_svc, self.item_svc)
        errors = []
        controller.errorOccurred.connect(errors.append)
        controller.subscribe("http://insecure.com/feed")
        assert len(errors) == 1
        assert "bad URL" in errors[0]

    def test_unsubscribe_clears_items_if_selected(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        self.item_svc.get_items.return_value = [_item_dto(1)]
        controller = AppController(self.sub_svc, self.item_svc)
        controller.selectFeed(1)
        controller.unsubscribe(1)
        assert controller.selectedFeedId == 0
        assert controller.itemModel.rowCount() == 0

    def test_unsubscribe_other_feed_no_clear(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        self.item_svc.get_items.return_value = [_item_dto(1)]
        controller = AppController(self.sub_svc, self.item_svc)
        controller.selectFeed(1)
        controller.unsubscribe(99)
        assert controller.selectedFeedId == 1

    def test_set_filter(self, qapp):
        self.item_svc.get_items.return_value = []
        controller = AppController(self.sub_svc, self.item_svc)
        controller._selected_feed_id = 1
        controller.setFilter(1, "type:video")
        self.sub_svc.set_filter.assert_called_once_with(1, "type:video")

    def test_set_filter_other_feed_no_reload(self, qapp):
        controller = AppController(self.sub_svc, self.item_svc)
        controller._selected_feed_id = 1
        controller.setFilter(99, "type:video")
        self.item_svc.get_items.assert_not_called()

    def test_set_filter_empty_clears(self, qapp):
        self.item_svc.get_items.return_value = []
        controller = AppController(self.sub_svc, self.item_svc)
        controller._selected_feed_id = 1
        controller.setFilter(1, "   ")
        self.sub_svc.set_filter.assert_called_once_with(1, None)

    def test_mark_read(self, qapp):
        self.item_svc.get_items.return_value = []
        controller = AppController(self.sub_svc, self.item_svc)
        controller._selected_feed_id = 1
        controller.markRead(5)
        self.item_svc.mark_read.assert_called_once_with(5)

    def test_mark_read_no_feed_selected(self, qapp):
        controller = AppController(self.sub_svc, self.item_svc)
        controller.markRead(5)
        self.item_svc.mark_read.assert_called_once_with(5)
        self.item_svc.get_items.assert_not_called()

    def test_mark_all_read(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        self.item_svc.get_items.return_value = []
        controller = AppController(self.sub_svc, self.item_svc)
        controller.markAllRead(1)
        self.item_svc.mark_all_read.assert_called_once_with(1)

    def test_notify_new_items(self, qapp):
        self.sub_svc.list_feeds.return_value = [_feed_dto(1, unread=3)]
        self.item_svc.get_items.return_value = []
        controller = AppController(self.sub_svc, self.item_svc)
        signals = []
        controller.newItemsAvailable.connect(lambda fid, n: signals.append((fid, n)))
        controller.notify_new_items(1, 3)
        assert (1, 3) in signals

    def test_notify_new_items_reloads_selected(self, qapp):
        self.sub_svc.list_feeds.return_value = [_feed_dto(1, unread=3)]
        self.item_svc.get_items.return_value = [_item_dto(1)]
        controller = AppController(self.sub_svc, self.item_svc)
        controller._selected_feed_id = 1
        controller.notify_new_items(1, 2)
        self.item_svc.get_items.assert_called_with(1)

    def test_set_feed_sort_alpha_asc(self, qapp):
        self.sub_svc.list_feeds.return_value = [_feed_dto(1), _feed_dto(2)]
        controller = AppController(self.sub_svc, self.item_svc)
        controller.setFeedSort("alpha_asc")
        assert controller._feed_sort == "alpha_asc"
        assert controller.feedModel.rowCount() == 2

    def test_set_feed_sort_alpha_desc(self, qapp):
        feeds = [
            FeedDTO(id=1, url="https://example.com/feed/1", source_type="mfeed",
                    title="Zebra", description=None, icon=None, language=None,
                    filter_expr=None, unread_count=0),
            FeedDTO(id=2, url="https://example.com/feed/2", source_type="mfeed",
                    title="Apple", description=None, icon=None, language=None,
                    filter_expr=None, unread_count=0),
        ]
        self.sub_svc.list_feeds.return_value = feeds
        controller = AppController(self.sub_svc, self.item_svc)
        controller.setFeedSort("alpha_desc")
        from PySide6.QtCore import Qt
        first = controller.feedModel.data(controller.feedModel.index(0, 0), Qt.UserRole + 2)
        assert first == "Zebra"

    def test_set_feed_sort_unread(self, qapp):
        feeds = [_feed_dto(1, unread=5), _feed_dto(2, unread=20)]
        self.sub_svc.list_feeds.return_value = feeds
        controller = AppController(self.sub_svc, self.item_svc)
        controller.setFeedSort("unread")
        from PySide6.QtCore import Qt
        first_unread = controller.feedModel.data(controller.feedModel.index(0, 0), Qt.UserRole + 5)
        assert first_unread == 20

    def test_set_item_sort_newest(self, qapp):
        items = [
            _item_dto(1),
            ItemDTO(id=2, feed_id=1, item_id="https://example.com/item/2",
                    type="article", title="Item 2", url="https://example.com/item/2",
                    published_iso="2025-01-01T00:00:00+00:00",
                    description=None, thumbnail_url=None, duration=None, is_read=False),
        ]
        self.item_svc.get_items.return_value = items
        controller = AppController(self.sub_svc, self.item_svc)
        controller._selected_feed_id = 1
        controller.setItemSort("newest")
        from PySide6.QtCore import Qt
        first_pub = controller.itemModel.data(controller.itemModel.index(0, 0), Qt.UserRole + 4)
        assert "2026" in first_pub

    def test_set_item_sort_oldest(self, qapp):
        items = [
            _item_dto(1),
            ItemDTO(id=2, feed_id=1, item_id="https://example.com/item/2",
                    type="article", title="Item 2", url="https://example.com/item/2",
                    published_iso="2025-01-01T00:00:00+00:00",
                    description=None, thumbnail_url=None, duration=None, is_read=False),
        ]
        self.item_svc.get_items.return_value = items
        controller = AppController(self.sub_svc, self.item_svc)
        controller._selected_feed_id = 1
        controller.setItemSort("oldest")
        from PySide6.QtCore import Qt
        first_pub = controller.itemModel.data(controller.itemModel.index(0, 0), Qt.UserRole + 4)
        assert "2025" in first_pub

    def test_set_item_sort_alpha(self, qapp):
        items = [
            ItemDTO(id=1, feed_id=1, item_id="https://example.com/item/1",
                    type="article", title="Zebra Article", url="https://example.com/item/1",
                    published_iso="2026-01-01T00:00:00+00:00",
                    description=None, thumbnail_url=None, duration=None, is_read=False),
            ItemDTO(id=2, feed_id=1, item_id="https://example.com/item/2",
                    type="article", title="Apple Article", url="https://example.com/item/2",
                    published_iso="2026-01-02T00:00:00+00:00",
                    description=None, thumbnail_url=None, duration=None, is_read=False),
        ]
        self.item_svc.get_items.return_value = items
        controller = AppController(self.sub_svc, self.item_svc)
        controller._selected_feed_id = 1
        controller.setItemSort("alpha")
        from PySide6.QtCore import Qt
        first_title = controller.itemModel.data(controller.itemModel.index(0, 0), Qt.UserRole + 1)
        assert first_title == "Apple Article"

    def test_set_item_sort_no_feed_selected_no_op(self, qapp):
        controller = AppController(self.sub_svc, self.item_svc)
        controller.setItemSort("newest")
        self.item_svc.get_items.assert_not_called()

    def test_bulk_unsubscribe_clears_selected(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        self.item_svc.get_items.return_value = [_item_dto(1)]
        controller = AppController(self.sub_svc, self.item_svc)
        controller.selectFeed(1)
        controller.bulkUnsubscribe([1, 2])
        assert controller.selectedFeedId == 0
        assert controller.itemModel.rowCount() == 0
        assert self.sub_svc.unsubscribe.call_count == 2

    def test_bulk_unsubscribe_non_selected_feed(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        self.item_svc.get_items.return_value = [_item_dto(1)]
        controller = AppController(self.sub_svc, self.item_svc)
        controller.selectFeed(1)
        controller.bulkUnsubscribe([99])
        assert controller.selectedFeedId == 1

    def test_export_feeds(self, qapp):
        feeds = [_feed_dto(1), _feed_dto(2)]
        self.sub_svc.list_feeds.return_value = feeds
        controller = AppController(self.sub_svc, self.item_svc)
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            tmp = Path(f.name)
        controller.exportFeeds(tmp.as_uri())
        data = json.loads(tmp.read_text())
        assert data["version"] == 1
        assert len(data["feeds"]) == 2
        tmp.unlink()

    def test_export_feeds_write_error_emits_signal(self, qapp):
        self.sub_svc.list_feeds.return_value = [_feed_dto(1)]
        controller = AppController(self.sub_svc, self.item_svc)
        errors = []
        controller.errorOccurred.connect(errors.append)
        controller.exportFeeds("file:///nonexistent_dir/out.json")
        assert len(errors) == 1

    def test_import_feeds(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        controller = AppController(self.sub_svc, self.item_svc)
        data = {"version": 1, "feeds": [
            {"url": "https://example.com/feed/1", "source_type": "rss", "title": "Feed One"},
            {"url": "https://example.com/feed/2", "source_type": "atom", "title": None},
        ]}
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(data, f)
            tmp = Path(f.name)
        controller.importFeeds(tmp.as_uri())
        assert self.sub_svc.subscribe.call_count == 2
        tmp.unlink()

    def test_import_feeds_skips_bad_url(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        self.sub_svc.subscribe.side_effect = ValueError("bad url")
        controller = AppController(self.sub_svc, self.item_svc)
        data = {"version": 1, "feeds": [{"url": "https://example.com/feed", "source_type": "rss"}]}
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(data, f)
            tmp = Path(f.name)
        controller.importFeeds(tmp.as_uri())
        tmp.unlink()

    def test_import_feeds_skips_empty_url(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        controller = AppController(self.sub_svc, self.item_svc)
        data = {"version": 1, "feeds": [{"url": "", "source_type": "rss"}, {"url": "   "}]}
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            json.dump(data, f)
            tmp = Path(f.name)
        controller.importFeeds(tmp.as_uri())
        self.sub_svc.subscribe.assert_not_called()
        tmp.unlink()

    def test_import_feeds_bad_file_emits_error(self, qapp):
        controller = AppController(self.sub_svc, self.item_svc)
        errors = []
        controller.errorOccurred.connect(errors.append)
        controller.importFeeds("file:///nonexistent/path.json")
        assert len(errors) == 1
