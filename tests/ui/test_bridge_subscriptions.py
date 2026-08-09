"""AppController: the subscription surface.

Adding, removing and re-pointing feeds, plus the per-feed filter. The JSON
round trip of the list is next door in `test_bridge_import_export.py`.
"""

from unittest.mock import AsyncMock, MagicMock

from tests.ui.bridge_dtos import feed_dto, item_dto, make_controller


class TestSubscriptions:
    def setup_method(self):
        self.sub_svc = MagicMock()
        self.item_svc = MagicMock()
        self.discovery_svc = MagicMock()
        self.discovery_svc.search = AsyncMock(return_value=[])

    def test_load_feeds(self, qapp):
        self.sub_svc.list_feeds.return_value = [feed_dto(1), feed_dto(2)]
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.loadFeeds()
        assert controller.feedModel.rowCount() == 2

    def test_select_feed(self, qapp):
        self.item_svc.get_items.return_value = [item_dto(1)]
        self.sub_svc.list_feeds.return_value = []
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.selectFeed(1)
        assert controller.itemModel.rowCount() == 1
        assert controller.selectedFeedId == 1

    def test_subscribe_success(self, qapp):
        self.sub_svc.subscribe.return_value = feed_dto(5)
        self.sub_svc.list_feeds.return_value = [feed_dto(5)]
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.subscribe("https://example.com/feed/5")
        self.sub_svc.subscribe.assert_called_once_with("https://example.com/feed/5")

    def test_subscribe_error_emits_signal(self, qapp):
        self.sub_svc.subscribe.side_effect = ValueError("bad URL")
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        errors = []
        controller.errorOccurred.connect(errors.append)
        controller.subscribe("http://insecure.com/feed")
        assert len(errors) == 1
        assert "bad URL" in errors[0]

    def test_unsubscribe_clears_items_if_selected(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        self.item_svc.get_items.return_value = [item_dto(1)]
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.selectFeed(1)
        controller.unsubscribe(1)
        assert controller.selectedFeedId == 0
        assert controller.itemModel.rowCount() == 0

    def test_unsubscribe_other_feed_no_clear(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        self.item_svc.get_items.return_value = [item_dto(1)]
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.selectFeed(1)
        controller.unsubscribe(99)
        assert controller.selectedFeedId == 1

    def test_set_filter(self, qapp):
        self.item_svc.get_items.return_value = []
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller._selected_feed_id = 1
        controller.setFilter(1, "type:video")
        self.sub_svc.set_filter.assert_called_once_with(1, "type:video")

    def test_set_filter_other_feed_no_reload(self, qapp):
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller._selected_feed_id = 1
        controller.setFilter(99, "type:video")
        self.item_svc.get_items.assert_not_called()

    def test_set_filter_empty_clears(self, qapp):
        self.item_svc.get_items.return_value = []
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller._selected_feed_id = 1
        controller.setFilter(1, "   ")
        self.sub_svc.set_filter.assert_called_once_with(1, None)

    def test_bulk_unsubscribe_clears_selected(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        self.item_svc.get_items.return_value = [item_dto(1)]
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.selectFeed(1)
        controller.bulkUnsubscribe([1, 2])
        assert controller.selectedFeedId == 0
        assert controller.itemModel.rowCount() == 0
        assert self.sub_svc.unsubscribe.call_count == 2

    def test_bulk_unsubscribe_non_selected_feed(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        self.item_svc.get_items.return_value = [item_dto(1)]
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.selectFeed(1)
        controller.bulkUnsubscribe([99])
        assert controller.selectedFeedId == 1

    def test_update_feed_url_success(self, qapp):
        self.sub_svc.list_feeds.return_value = [feed_dto(1)]
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.updateFeedUrl(1, "https://new.example.com/feed")
        self.sub_svc.update_url.assert_called_once_with(
            1, "https://new.example.com/feed"
        )

    def test_update_feed_url_error_emits_signal(self, qapp):
        self.sub_svc.update_url.side_effect = ValueError("invalid url")
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        errors = []
        controller.errorOccurred.connect(errors.append)
        controller.updateFeedUrl(1, "not-a-url")
        assert len(errors) == 1
        assert "invalid url" in errors[0]
