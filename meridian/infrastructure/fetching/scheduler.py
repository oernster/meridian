"""Asyncio-based poll scheduler. One task per subscribed feed."""
from __future__ import annotations

import asyncio
import logging
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

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())

    def stop(self) -> None:
        if self._task and not self._task.done():
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
