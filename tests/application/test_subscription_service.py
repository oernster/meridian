from unittest.mock import MagicMock

import pytest

from meridian.application.services.subscription_service import SubscriptionService
from meridian.domain.entities.feed import Feed
from meridian.domain.value_objects.source_type import SourceType


def _make_feed(id: int = 1, url: str = "https://example.com/feed") -> Feed:
    return Feed(id=id, url=url, source_type=SourceType.MFEED)


class TestSubscriptionService:
    def setup_method(self):
        self.feed_repo = MagicMock()
        self.item_repo = MagicMock()
        self.item_repo.unread_count.return_value = 0
        self.svc = SubscriptionService(self.feed_repo, self.item_repo)

    def test_subscribe_new(self):
        self.feed_repo.get_by_url.return_value = None
        saved = _make_feed(id=5)
        self.feed_repo.save.return_value = saved
        dto = self.svc.subscribe("https://example.com/feed", "mfeed")
        assert dto.id == 5
        assert dto.source_type == "mfeed"
        self.feed_repo.save.assert_called_once()

    def test_subscribe_existing_returns_existing(self):
        existing = _make_feed(id=3)
        self.feed_repo.get_by_url.return_value = existing
        dto = self.svc.subscribe("https://example.com/feed", "mfeed")
        assert dto.id == 3
        self.feed_repo.save.assert_not_called()

    def test_subscribe_invalid_url_raises(self):
        self.feed_repo.get_by_url.return_value = None
        with pytest.raises(ValueError):
            self.svc.subscribe("http://insecure.com/feed", "mfeed")

    def test_unsubscribe(self):
        self.svc.unsubscribe(7)
        self.feed_repo.delete.assert_called_once_with(7)

    def test_list_feeds_empty(self):
        self.feed_repo.list_all.return_value = []
        assert self.svc.list_feeds() == []

    def test_list_feeds_with_items(self):
        self.feed_repo.list_all.return_value = [_make_feed(id=1), _make_feed(id=2, url="https://other.com/feed")]
        self.item_repo.unread_count.return_value = 3
        result = self.svc.list_feeds()
        assert len(result) == 2
        assert result[0].unread_count == 3

    def test_get_feed_found(self):
        self.feed_repo.get_by_id.return_value = _make_feed(id=1)
        dto = self.svc.get_feed(1)
        assert dto is not None
        assert dto.id == 1

    def test_get_feed_not_found(self):
        self.feed_repo.get_by_id.return_value = None
        assert self.svc.get_feed(99) is None

    def test_set_filter(self):
        self.svc.set_filter(1, "type:video")
        self.feed_repo.update_filter.assert_called_once_with(1, "type:video")

    def test_set_filter_clear(self):
        self.svc.set_filter(1, None)
        self.feed_repo.update_filter.assert_called_once_with(1, None)
