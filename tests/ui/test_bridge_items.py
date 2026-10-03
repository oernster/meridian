"""AppController: the item surface.

Read state and the arrival of new items, which is the one path driven from
the poller rather than from the user.
"""

from unittest.mock import AsyncMock, MagicMock

from tests.ui.bridge_dtos import feed_dto, item_dto, make_controller


class TestItems:
    def setup_method(self):
        self.sub_svc = MagicMock()
        self.item_svc = MagicMock()
        self.discovery_svc = MagicMock()
        self.discovery_svc.search = AsyncMock(return_value=[])

    def test_mark_read(self, qapp):
        self.item_svc.get_items.return_value = []
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller._selected_feed_id = 1
        controller.markRead(5)
        self.item_svc.mark_read.assert_called_once_with(5)

    def test_mark_read_no_feed_selected(self, qapp):
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.markRead(5)
        self.item_svc.mark_read.assert_called_once_with(5)
        self.item_svc.get_items.assert_not_called()

    def test_mark_all_read(self, qapp):
        self.sub_svc.list_feeds.return_value = []
        self.item_svc.get_items.return_value = []
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller.markAllRead(1)
        self.item_svc.mark_all_read.assert_called_once_with(1)

    def test_notify_new_items(self, qapp):
        self.sub_svc.list_feeds.return_value = [feed_dto(1, unread=3)]
        self.item_svc.get_items.return_value = []
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        signals = []
        controller.newItemsAvailable.connect(lambda fid, n: signals.append((fid, n)))
        controller.notify_new_items(1, 3)
        assert (1, 3) in signals

    def test_notify_new_items_reloads_selected(self, qapp):
        self.sub_svc.list_feeds.return_value = [feed_dto(1, unread=3)]
        self.item_svc.get_items.return_value = [item_dto(1)]
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        controller._selected_feed_id = 1
        controller.notify_new_items(1, 2)
        self.item_svc.get_items.assert_called_with(1)

    def test_a_store_failure_on_select_is_said_plainly(self, qapp, caplog):
        """The store's text carries SQL; the window gets a sentence, the log it."""
        self.item_svc.get_items.side_effect = RuntimeError("SELECT * FROM items")
        controller = make_controller(
            qapp, self.sub_svc, self.item_svc, self.discovery_svc
        )
        errors = []
        controller.errorOccurred.connect(errors.append)
        controller._selected_feed_id = 1
        controller.selectFeed(2)
        assert errors == ["This feed's items could not be read."]
        assert controller.selectedFeedId == 0
        assert "SELECT * FROM items" in caplog.text
