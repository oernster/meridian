from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from meridian.application.interfaces.feed_fetcher import FetchResult
from meridian.application.interfaces.poll_state_repository import PollState
from meridian.application.services.poll_orchestrator import PollOrchestrator
from meridian.domain.entities.feed import Feed
from meridian.domain.entities.item import Item
from meridian.domain.value_objects.item_type import ItemType
from meridian.domain.value_objects.media import ItemSource
from meridian.domain.value_objects.poll_config import PollConfig, POLL_FLOOR_SECONDS
from meridian.domain.value_objects.source_type import SourceType


def _make_feed(title: str | None = None) -> Feed:
    return Feed(id=1, url="https://example.com/feed", source_type=SourceType.MFEED, title=title)


def _make_item(feed_title: str | None = "Example Feed") -> Item:
    return Item(
        feed_id=1,
        item_id="https://example.com/item/1",
        type=ItemType.ARTICLE,
        title="Test",
        url="https://example.com/item/1",
        published=datetime(2026, 1, 1, tzinfo=timezone.utc),
        source=ItemSource(type="mfeed", feed_url="https://example.com/feed", feed_title=feed_title),
    )


def _make_result(**kwargs) -> FetchResult:
    defaults = dict(
        items=[_make_item()],
        poll_config=PollConfig(),
        etag=None,
        last_modified=None,
        moved_to=None,
    )
    return FetchResult(**{**defaults, **kwargs})


class TestPollOrchestrator:
    def setup_method(self):
        self.feed_repo = MagicMock()
        self.item_repo = MagicMock()
        self.poll_state_repo = MagicMock()
        self.fetcher = MagicMock()
        self.fetcher.fetch = AsyncMock()
        self.orch = PollOrchestrator(
            self.feed_repo, self.item_repo, self.poll_state_repo, self.fetcher
        )

    async def test_poll_feed_not_found(self):
        self.feed_repo.get_by_id.return_value = None
        count, feeds_changed = await self.orch.poll_feed(1)
        assert count == 0
        assert feeds_changed is False
        self.fetcher.fetch.assert_not_called()

    async def test_poll_not_due(self):
        self.feed_repo.get_by_id.return_value = _make_feed()
        self.poll_state_repo.get.return_value = PollState(
            feed_id=1,
            next_poll=datetime.now(tz=timezone.utc) + timedelta(seconds=600),
        )
        count, feeds_changed = await self.orch.poll_feed(1)
        assert count == 0
        assert feeds_changed is False

    async def test_poll_new_items(self):
        self.feed_repo.get_by_id.return_value = _make_feed(title="Existing")
        self.poll_state_repo.get.return_value = PollState(feed_id=1)
        self.fetcher.fetch.return_value = _make_result()
        self.item_repo.exists.return_value = False
        self.item_repo.save_many.return_value = [_make_item()]
        count, feeds_changed = await self.orch.poll_feed(1)
        assert count == 1
        assert feeds_changed is False
        self.item_repo.save_many.assert_called_once()

    async def test_poll_no_new_items(self):
        self.feed_repo.get_by_id.return_value = _make_feed(title="Existing")
        self.poll_state_repo.get.return_value = PollState(feed_id=1)
        self.fetcher.fetch.return_value = _make_result()
        self.item_repo.exists.return_value = True
        count, feeds_changed = await self.orch.poll_feed(1)
        assert count == 0
        assert feeds_changed is False

    async def test_poll_title_discovered(self):
        self.feed_repo.get_by_id.return_value = _make_feed(title=None)
        self.poll_state_repo.get.return_value = PollState(feed_id=1)
        self.fetcher.fetch.return_value = _make_result()
        self.item_repo.exists.return_value = True
        count, feeds_changed = await self.orch.poll_feed(1)
        assert feeds_changed is True
        self.feed_repo.update_title.assert_called_once_with(1, "Example Feed")

    async def test_poll_title_already_set_no_update(self):
        self.feed_repo.get_by_id.return_value = _make_feed(title="My Feed")
        self.poll_state_repo.get.return_value = PollState(feed_id=1)
        self.fetcher.fetch.return_value = _make_result()
        self.item_repo.exists.return_value = False
        await self.orch.poll_feed(1)
        self.feed_repo.update_title.assert_not_called()

    async def test_poll_title_none_in_item_no_update(self):
        self.feed_repo.get_by_id.return_value = _make_feed(title=None)
        self.poll_state_repo.get.return_value = PollState(feed_id=1)
        self.fetcher.fetch.return_value = _make_result(items=[_make_item(feed_title=None)])
        self.item_repo.exists.return_value = True
        count, feeds_changed = await self.orch.poll_feed(1)
        assert feeds_changed is False
        self.feed_repo.update_title.assert_not_called()

    async def test_poll_title_no_items_no_update(self):
        self.feed_repo.get_by_id.return_value = _make_feed(title=None)
        self.poll_state_repo.get.return_value = PollState(feed_id=1)
        self.fetcher.fetch.return_value = _make_result(items=[])
        count, feeds_changed = await self.orch.poll_feed(1)
        assert feeds_changed is False
        self.feed_repo.update_title.assert_not_called()

    async def test_poll_not_modified(self):
        self.feed_repo.get_by_id.return_value = _make_feed()
        self.poll_state_repo.get.return_value = PollState(feed_id=1, etag='"abc"')
        self.fetcher.fetch.return_value = _make_result(items=[], not_modified=True)
        count, feeds_changed = await self.orch.poll_feed(1)
        assert count == 0
        assert feeds_changed is False
        self.item_repo.save_many.assert_not_called()

    async def test_poll_moved_to(self):
        self.feed_repo.get_by_id.return_value = _make_feed()
        self.poll_state_repo.get.return_value = PollState(feed_id=1)
        self.fetcher.fetch.return_value = _make_result(
            items=[], moved_to="https://new.example.com/feed"
        )
        count, feeds_changed = await self.orch.poll_feed(1)
        assert count == 0
        assert feeds_changed is False
        saved_state = self.poll_state_repo.save.call_args[0][0]
        assert saved_state.moved_to == "https://new.example.com/feed"

    def test_apply_backoff(self):
        self.poll_state_repo.get.return_value = PollState(feed_id=1)
        self.orch.apply_backoff(1, 120)
        saved_state = self.poll_state_repo.save.call_args[0][0]
        assert saved_state.backoff_until is not None

    def test_apply_backoff_respects_floor(self):
        self.poll_state_repo.get.return_value = PollState(feed_id=1)
        self.orch.apply_backoff(1, 10)
        saved_state = self.poll_state_repo.save.call_args[0][0]
        delta = saved_state.backoff_until - datetime.now(tz=timezone.utc)
        assert delta.total_seconds() >= POLL_FLOOR_SECONDS - 1

    def test_seconds_until_next_poll_none(self):
        self.poll_state_repo.get.return_value = PollState(feed_id=1)
        assert self.orch.seconds_until_next_poll(1) == 0

    def test_seconds_until_next_poll_future(self):
        self.poll_state_repo.get.return_value = PollState(
            feed_id=1,
            next_poll=datetime.now(tz=timezone.utc) + timedelta(seconds=300),
        )
        secs = self.orch.seconds_until_next_poll(1)
        assert 299 <= secs <= 301

    async def test_poll_skipped_during_backoff(self):
        self.feed_repo.get_by_id.return_value = _make_feed()
        self.poll_state_repo.get.return_value = PollState(
            feed_id=1,
            backoff_until=datetime.now(tz=timezone.utc) + timedelta(seconds=600),
        )
        count, feeds_changed = await self.orch.poll_feed(1)
        assert count == 0
        assert feeds_changed is False
        self.fetcher.fetch.assert_not_called()
