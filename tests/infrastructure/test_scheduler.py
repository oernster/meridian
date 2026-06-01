import asyncio
import xml.etree.ElementTree as ET
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from meridian.infrastructure.fetching.http_fetcher import RateLimitedError
from meridian.infrastructure.fetching.scheduler import PollScheduler


class TestPollScheduler:
    def setup_method(self):
        self.feed_repo = MagicMock()
        self.orchestrator = MagicMock()
        self.orchestrator.poll_feed = AsyncMock(return_value=(0, False))

    def test_start_creates_task(self):
        scheduler = PollScheduler(self.feed_repo, self.orchestrator)
        sentinel = object()
        with patch.object(scheduler, "_run", new=MagicMock(return_value=sentinel)):
            with patch("asyncio.create_task") as mock_create:
                scheduler.start()
                mock_create.assert_called_once_with(sentinel)

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

    def test_start_in_thread_creates_daemon_thread(self):
        scheduler = PollScheduler(self.feed_repo, self.orchestrator)
        with patch.object(scheduler, "_run", new=AsyncMock(side_effect=asyncio.CancelledError)):
            scheduler.start_in_thread()
            assert scheduler._thread is not None
            assert scheduler._thread.daemon is True
            assert scheduler._thread.name == "meridian-poll"
            # Give thread time to set _loop
            import time
            deadline = time.monotonic() + 2.0
            while scheduler._loop is None and time.monotonic() < deadline:
                time.sleep(0.01)
            assert scheduler._loop is not None
            scheduler._loop.call_soon_threadsafe(scheduler._loop.stop)
            scheduler._thread.join(timeout=2.0)

    def test_start_in_thread_cleanup_cancels_pending_tasks(self):
        import time

        async def slow_run():
            await asyncio.sleep(999)

        scheduler = PollScheduler(self.feed_repo, self.orchestrator)
        with patch.object(scheduler, "_run", new=MagicMock(side_effect=slow_run)):
            scheduler.start_in_thread()
            deadline = time.monotonic() + 2.0
            while scheduler._loop is None and time.monotonic() < deadline:
                time.sleep(0.01)
            time.sleep(0.05)  # let task enter sleep
            scheduler._loop.call_soon_threadsafe(scheduler._loop.stop)
            scheduler._thread.join(timeout=3.0)
            assert scheduler._loop.is_closed()

    def test_stop_uses_loop_when_available(self):
        scheduler = PollScheduler(self.feed_repo, self.orchestrator)
        mock_loop = MagicMock()
        mock_loop.is_closed.return_value = False
        scheduler._loop = mock_loop
        scheduler.stop()
        mock_loop.call_soon_threadsafe.assert_called_once_with(mock_loop.stop)

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
        self.orchestrator.poll_feed = AsyncMock(return_value=(3, False))
        callback = AsyncMock()
        scheduler = PollScheduler(self.feed_repo, self.orchestrator, callback)
        await scheduler._poll_one(1)
        callback.assert_called_once_with(1, 3)

    async def test_poll_one_feeds_changed_triggers_callback(self):
        self.orchestrator.poll_feed = AsyncMock(return_value=(0, True))
        callback = AsyncMock()
        scheduler = PollScheduler(self.feed_repo, self.orchestrator, callback)
        await scheduler._poll_one(1)
        callback.assert_called_once_with(1, 0)

    async def test_poll_one_http_404_calls_backoff(self):
        response = MagicMock()
        response.status_code = 404
        exc = httpx.HTTPStatusError("404", request=MagicMock(), response=response)
        self.orchestrator.poll_feed = AsyncMock(side_effect=exc)
        scheduler = PollScheduler(self.feed_repo, self.orchestrator)
        await scheduler._poll_one(1)
        self.orchestrator.apply_backoff.assert_called_once_with(1, 86400)

    async def test_poll_one_http_non_404_calls_backoff(self):
        response = MagicMock()
        response.status_code = 500
        exc = httpx.HTTPStatusError("500", request=MagicMock(), response=response)
        self.orchestrator.poll_feed = AsyncMock(side_effect=exc)
        scheduler = PollScheduler(self.feed_repo, self.orchestrator)
        await scheduler._poll_one(1)
        self.orchestrator.apply_backoff.assert_called_once_with(1, 3600)

    async def test_poll_one_connect_error_calls_backoff(self):
        self.orchestrator.poll_feed = AsyncMock(side_effect=httpx.ConnectError("refused"))
        scheduler = PollScheduler(self.feed_repo, self.orchestrator)
        await scheduler._poll_one(1)
        self.orchestrator.apply_backoff.assert_called_once_with(1, 3600)

    async def test_poll_one_xml_parse_error_calls_backoff(self):
        self.orchestrator.poll_feed = AsyncMock(
            side_effect=ET.ParseError("syntax error: line 1, column 0")
        )
        scheduler = PollScheduler(self.feed_repo, self.orchestrator)
        await scheduler._poll_one(1)
        self.orchestrator.apply_backoff.assert_called_once_with(1, 3600)

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
