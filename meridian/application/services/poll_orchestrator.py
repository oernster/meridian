from datetime import datetime, timedelta, timezone

from meridian.application.interfaces.feed_fetcher import FeedFetcher
from meridian.application.interfaces.feed_repository import FeedRepository
from meridian.application.interfaces.item_repository import ItemRepository
from meridian.application.interfaces.poll_state_repository import (
    PollState,
    PollStateRepository,
)
from meridian.domain.entities.feed import Feed
from meridian.domain.value_objects.poll_config import POLL_FLOOR_SECONDS


class PollOrchestrator:
    def __init__(
        self,
        feed_repo: FeedRepository,
        item_repo: ItemRepository,
        poll_state_repo: PollStateRepository,
        fetcher: FeedFetcher,
    ) -> None:
        self._feed_repo = feed_repo
        self._item_repo = item_repo
        self._poll_state_repo = poll_state_repo
        self._fetcher = fetcher

    async def poll_feed(self, feed_id: int) -> int:
        feed = self._feed_repo.get_by_id(feed_id)
        if feed is None:
            return 0
        state = self._poll_state_repo.get(feed_id)
        if not self._is_due(state):
            return 0
        result = await self._fetcher.fetch(
            feed,
            etag=state.etag,
            last_modified=state.last_modified,
        )
        now = datetime.now(tz=timezone.utc)
        if result.moved_to:
            self._poll_state_repo.save(
                PollState(
                    feed_id=feed_id,
                    last_polled=now,
                    moved_to=result.moved_to,
                )
            )
            return 0
        if result.not_modified:
            next_poll = now + timedelta(seconds=result.poll_config.effective_interval)
            self._poll_state_repo.save(
                PollState(
                    feed_id=feed_id,
                    last_polled=now,
                    next_poll=next_poll,
                    etag=state.etag,
                    last_modified=state.last_modified,
                )
            )
            return 0
        new_items = [
            i for i in result.items
            if not self._item_repo.exists(feed_id, i.item_id)
        ]
        if new_items:
            self._item_repo.save_many(new_items)
        next_poll = now + timedelta(seconds=result.poll_config.effective_interval)
        self._poll_state_repo.save(
            PollState(
                feed_id=feed_id,
                last_polled=now,
                next_poll=next_poll,
                etag=result.etag,
                last_modified=result.last_modified,
            )
        )
        return len(new_items)

    @staticmethod
    def _ensure_utc(dt: datetime) -> datetime:
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    def _is_due(self, state: PollState) -> bool:
        now = datetime.now(tz=timezone.utc)
        if state.backoff_until:
            return now >= self._ensure_utc(state.backoff_until)
        if state.next_poll is None:
            return True
        return now >= self._ensure_utc(state.next_poll)

    def seconds_until_next_poll(self, feed_id: int) -> int:
        state = self._poll_state_repo.get(feed_id)
        if state.next_poll is None:
            return 0
        delta = (self._ensure_utc(state.next_poll) - datetime.now(tz=timezone.utc)).total_seconds()
        return max(0, int(delta))

    def apply_backoff(self, feed_id: int, retry_after_seconds: int) -> None:
        effective = max(retry_after_seconds, POLL_FLOOR_SECONDS)
        state = self._poll_state_repo.get(feed_id)
        backoff_until = datetime.now(tz=timezone.utc) + timedelta(seconds=effective)
        self._poll_state_repo.save(
            PollState(
                feed_id=feed_id,
                last_polled=state.last_polled,
                next_poll=state.next_poll,
                etag=state.etag,
                last_modified=state.last_modified,
                backoff_until=backoff_until,
            )
        )
