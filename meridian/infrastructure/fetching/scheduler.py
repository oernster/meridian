"""Asyncio-based poll scheduler. One task per subscribed feed."""
from __future__ import annotations

import asyncio
import logging
import threading
from collections.abc import Callable, Coroutine
from typing import Any

from meridian.application.interfaces.feed_repository import FeedRepository
from meridian.application.services.poll_orchestrator import PollOrchestrator
from meridian.infrastructure.fetching.http_fetcher import RateLimitedError

_LOG = logging.getLogger(__name__)

_TICK_SECONDS = 10
_INITIAL_DELAY_SECONDS = 5


class PollScheduler:
    def __init__(
        self,
        feed_repo: FeedRepository,
        orchestrator: PollOrchestrator,
        on_new_items: Callable[[int, int], Coroutine[Any, Any, None]] | None = None,
    ) -> None:
        self._feed_repo = feed_repo
        self._orchestrator = orchestrator
        self._on_new_items = on_new_items
        self._task: asyncio.Task | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())

    def start_in_thread(self) -> None:
        """Run the scheduler in a dedicated daemon thread with its own event loop."""
        def _thread_main() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._loop = loop
            loop.create_task(self._run())
            try:
                loop.run_forever()
            finally:
                loop.close()

        self._thread = threading.Thread(target=_thread_main, daemon=True, name="meridian-poll")
        self._thread.start()

    def stop(self) -> None:
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._loop.stop)
        elif self._task and not self._task.done():
            self._task.cancel()

    async def _run(self) -> None:
        await asyncio.sleep(_INITIAL_DELAY_SECONDS)
        while True:
            await self._tick()
            await asyncio.sleep(_TICK_SECONDS)

    async def _tick(self) -> None:
        feeds = self._feed_repo.list_all()
        tasks = [self._poll_one(feed.id) for feed in feeds]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _poll_one(self, feed_id: int) -> None:
        try:
            new_count = await self._orchestrator.poll_feed(feed_id)
            if new_count > 0 and self._on_new_items:
                await self._on_new_items(feed_id, new_count)
        except RateLimitedError as exc:
            _LOG.warning("Feed %d rate limited; backoff %ds", feed_id, exc.retry_after_seconds)
            self._orchestrator.apply_backoff(feed_id, exc.retry_after_seconds)
        except Exception:
            _LOG.exception("Poll failed for feed %d", feed_id)
