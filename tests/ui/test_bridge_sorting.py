"""AppController: the sort settings.

Feed order and item order are separate settings held by the controller. Each
is asserted through the model the QML actually reads.
"""

from unittest.mock import AsyncMock, MagicMock

from meridian.application.dto.feed_dto import FeedDTO
from meridian.application.dto.item_dto import ItemDTO
from tests.ui.bridge_dtos import feed_dto, item_dto, make_controller


class TestSorting:
    def setup_method(self):
        self.sub_svc = MagicMock()
        self.item_svc = MagicMock()
        self.discovery_svc = MagicMock()
        self.discovery_svc.search = AsyncMock(return_value=[])

    def test_set_feed_sort_alpha_asc(self, qapp):
        self.sub_svc.list_feeds.return_value = [feed_dto(1), feed_dto(2)]
        controller = make_controller(
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
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.setFeedSort("alpha_desc")
        from PySide6.QtCore import Qt

        first = controller.feedModel.data(
            controller.feedModel.index(0, 0), Qt.UserRole + 2
        )
        assert first == "Zebra"

    def test_set_feed_sort_unread(self, qapp):
        feeds = [feed_dto(1, unread=5), feed_dto(2, unread=20)]
        self.sub_svc.list_feeds.return_value = feeds
        controller = make_controller(
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
            item_dto(1),
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
        controller = make_controller(
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
            item_dto(1),
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
        controller = make_controller(
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
        controller = make_controller(
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
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.setItemSort("newest")
        self.item_svc.get_items.assert_not_called()
