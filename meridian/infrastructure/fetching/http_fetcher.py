"""HTTP fetcher implementing FeedFetcher interface."""
from __future__ import annotations

import httpx

from meridian.application.interfaces.feed_fetcher import FeedFetcher, FetchResult
from meridian.domain.entities.feed import Feed
from meridian.domain.value_objects.poll_config import PollConfig, POLL_FLOOR_SECONDS
from meridian.domain.value_objects.source_type import SourceType
from meridian.infrastructure.fetching.parser import (
    atom_parser,
    mfeed_parser,
    platform_parser,
    podcast_parser,
    rss_parser,
)

_USER_AGENT = "MMSP/1.0"
_MAX_DOCUMENT_BYTES = 10 * 1024 * 1024


class HttpFetcher(FeedFetcher):
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
            timeout=30.0,
        )

    async def fetch(
        self,
        feed: Feed,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> FetchResult:
        headers: dict[str, str] = {}
        if etag:
            headers["If-None-Match"] = etag
        if last_modified:
            headers["If-Modified-Since"] = last_modified
        response = await self._client.get(feed.url, headers=headers)
        if response.status_code == 301:
            location = response.headers.get("location", "")
            return FetchResult(
                items=[],
                poll_config=PollConfig(),
                etag=None,
                last_modified=None,
                moved_to=location if location.startswith("https://") else None,
            )
        if response.status_code == 304:
            return FetchResult(
                items=[],
                poll_config=PollConfig(),
                etag=etag,
                last_modified=last_modified,
                moved_to=None,
                not_modified=True,
            )
        if response.status_code == 429:
            retry_after = response.headers.get("retry-after")
            raise RateLimitedError(
                int(retry_after) if retry_after and retry_after.isdigit() else POLL_FLOOR_SECONDS
            )
        response.raise_for_status()
        raw = response.content
        if len(raw) > _MAX_DOCUMENT_BYTES:
            raise ValueError(f"Feed document exceeds size limit: {len(raw)} bytes")
        items, poll_config = self._parse(feed, raw)
        return FetchResult(
            items=items,
            poll_config=poll_config,
            etag=response.headers.get("etag"),
            last_modified=response.headers.get("last-modified"),
            moved_to=None,
        )

    def _parse(self, feed: Feed, raw: bytes) -> tuple[list, PollConfig]:
        match feed.source_type:
            case SourceType.MFEED:
                return mfeed_parser.parse(feed.id, feed.url, raw)
            case SourceType.RSS:
                return rss_parser.parse(feed.id, feed.url, raw)
            case SourceType.ATOM:
                return atom_parser.parse(feed.id, feed.url, raw)
            case SourceType.PODCAST:
                return podcast_parser.parse(feed.id, feed.url, raw)
            case SourceType.PLATFORM:
                return platform_parser.parse(
                    feed.id,
                    feed.url,
                    raw,
                    platform_id=feed.platform_id,
                    rss_fallback_url=feed.rss_fallback_url,
                )
            case _:  # pragma: no cover
                raise AssertionError(f"Unhandled source type: {feed.source_type}")

    async def aclose(self) -> None:
        await self._client.aclose()


class RateLimitedError(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Rate limited; retry after {retry_after_seconds}s")
