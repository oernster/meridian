import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from meridian.infrastructure.fetching.http_fetcher import RateLimitedError
from meridian.infrastructure.fetching.scheduler import PollScheduler


class TestPollScheduler:
    def setup_method(self):
        self.feed_repo = MagicMock()
        self.orchestrator = MagicMock()
        self.orchestrator.poll_feed = AsyncMock(return_value=0)

    def test_start_creates_task(self):
        scheduler = PollScheduler(self.feed_repo, self.orchestrator)
        with patch("asyncio.create_task") as mock_create:
            scheduler.start()
            mock_create.assert_called_once()

    def test_stop_cancels_task(self):
        scheduler = PollScheduler(self.feed_repo, self.orchestrator)
        mock_task = MagicMock()
        mock_task.done.return_value = False
        scheduler._task = mock_task
        scheduler.stop()
        mock_task.cancel.assert_called_once()

    def test_stop_no_task_noop(self):
        scheduler = PollScheduler(self.feed_repo, self.orchestrator)
        scheduler.stop()

    def test_double_start_no_duplicate(self):
        scheduler = PollScheduler(self.feed_repo, self.orchestrator)
        mock_task = MagicMock()
        mock_task.done.return_value = False
        scheduler._task = mock_task
        with patch("asyncio.create_task") as mock_create:
            scheduler.start()
            mock_create.assert_not_called()

    async def test_poll_one_rate_limit_calls_backoff(self):
        self.orchestrator.poll_feed = AsyncMock(
            side_effect=RateLimitedError(120)
        )
        scheduler = PollScheduler(self.feed_repo, self.orchestrator)
        await scheduler._poll_one(1)
        self.orchestrator.apply_backoff.assert_called_once_with(1, 120)

    async def test_poll_one_exception_logged(self):
        self.orchestrator.poll_feed = AsyncMock(side_effect=RuntimeError("network error"))
        scheduler = PollScheduler(self.feed_repo, self.orchestrator)
        await scheduler._poll_one(1)

    async def test_poll_one_new_items_callback(self):
        self.orchestrator.poll_feed = AsyncMock(return_value=3)
        callback = AsyncMock()
        scheduler = PollScheduler(self.feed_repo, self.orchestrator, callback)
        await scheduler._poll_one(1)
        callback.assert_called_once_with(1, 3)

    async def test_tick_polls_all_feeds(self):
        from meridian.domain.entities.feed import Feed
        from meridian.domain.value_objects.source_type import SourceType
        self.feed_repo.list_all.return_value = [
            Feed(id=1, url="https://a.example.com/feed", source_type=SourceType.MFEED),
            Feed(id=2, url="https://b.example.com/feed", source_type=SourceType.MFEED),
        ]
        scheduler = PollScheduler(self.feed_repo, self.orchestrator)
        await scheduler._tick()
        assert self.orchestrator.poll_feed.call_count == 2

    async def test_run_ticks_then_sleeps(self):
        import asyncio
        from unittest.mock import patch
        self.feed_repo.list_all.return_value = []
        scheduler = PollScheduler(self.feed_repo, self.orchestrator)
        tick_count = 0
        async def counting_tick():
            nonlocal tick_count
            tick_count += 1
            if tick_count >= 2:
                raise asyncio.CancelledError()
        scheduler._tick = counting_tick
        sleep_calls = []
        async def fake_sleep(secs):
            sleep_calls.append(secs)
        with patch("meridian.infrastructure.fetching.scheduler.asyncio.sleep", new=fake_sleep):
            try:
                await scheduler._run()
            except asyncio.CancelledError:
                pass
        assert tick_count >= 1
        assert any(s == 10 for s in sleep_calls)
