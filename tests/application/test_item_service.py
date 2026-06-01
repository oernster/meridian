from datetime import datetime, timezone
from unittest.mock import MagicMock

from meridian.application.services.item_service import ItemService
from meridian.domain.entities.feed import Feed
from meridian.domain.entities.item import Item
from meridian.domain.value_objects.item_type import ItemType
from meridian.domain.value_objects.source_type import SourceType


def _make_feed(filter_expr: str | None = None) -> Feed:
    return Feed(id=1, url="https://example.com/feed", source_type=SourceType.MFEED, filter_expr=filter_expr)


def _make_item(item_id: str = "https://example.com/1", itype: ItemType = ItemType.ARTICLE) -> Item:
    return Item(
        id=1,
        feed_id=1,
        item_id=item_id,
        type=itype,
        title="Test",
        url="https://example.com/1",
        published=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


class TestItemService:
    def setup_method(self):
        self.item_repo = MagicMock()
        self.feed_repo = MagicMock()
        self.svc = ItemService(self.item_repo, self.feed_repo)

    def test_get_items_no_filter(self):
        self.feed_repo.get_by_id.return_value = _make_feed()
        self.item_repo.list_by_feed.return_value = [_make_item()]
        result = self.svc.get_items(1)
        assert len(result) == 1
        assert result[0].type == "article"

    def test_get_items_with_filter(self):
        self.feed_repo.get_by_id.return_value = _make_feed(filter_expr="type:video")
        items = [
            _make_item(item_id="https://example.com/1", itype=ItemType.VIDEO),
            _make_item(item_id="https://example.com/2", itype=ItemType.ARTICLE),
        ]
        self.item_repo.list_by_feed.return_value = items
        result = self.svc.get_items(1)
        assert len(result) == 1
        assert result[0].type == "video"

    def test_get_items_feed_not_found(self):
        self.feed_repo.get_by_id.return_value = None
        self.item_repo.list_by_feed.return_value = []
        result = self.svc.get_items(99)
        assert result == []

    def test_mark_read(self):
        self.svc.mark_read(5)
        self.item_repo.mark_read.assert_called_once()
        args = self.item_repo.mark_read.call_args[0]
        assert args[0] == 5

    def test_mark_all_read(self):
        self.svc.mark_all_read(1)
        self.item_repo.mark_all_read.assert_called_once()
        args = self.item_repo.mark_all_read.call_args[0]
        assert args[0] == 1
