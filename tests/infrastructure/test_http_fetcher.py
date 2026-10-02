import json
from itertools import pairwise

import httpx
import pytest
import respx

from meridian.domain.entities.feed import Feed
from meridian.domain.value_objects.source_type import SourceType
from meridian.infrastructure.fetching.http_fetcher import HttpFetcher, RateLimitedError
from meridian.infrastructure.fetching.https_client import (
    MAX_REDIRECT_HOPS,
    InsecureRedirectError,
)
from tests.infrastructure.redirect_transport import redirecting_transport

_MOVED = "https://new.example.com/feed"
_INSECURE = "http://insecure.example.com/feed"

_MFEED = json.dumps(
    {
        "mmsp": "1.0",
        "id": "https://example.com/feed",
        "title": "Test",
        "feed_url": "https://example.com/feed",
        "items": [],
    }
).encode()

_FEED = Feed(id=1, url="https://example.com/feed", source_type=SourceType.MFEED)


def _redirect(status: int, location: str, seen: list[str]) -> httpx.MockTransport:
    """The feed URL answers with one redirect; every other URL serves the feed."""
    return redirecting_transport({_FEED.url: (status, location)}, _MFEED, seen)


class TestHttpFetcher:
    @respx.mock
    async def test_successful_fetch(self):
        respx.get("https://example.com/feed").mock(
            return_value=httpx.Response(200, content=_MFEED, headers={"etag": '"abc"'})
        )
        fetcher = HttpFetcher(httpx.AsyncClient())
        result = await fetcher.fetch(_FEED)
        assert not result.not_modified
        assert result.etag == '"abc"'
        assert result.moved_to is None

    @respx.mock
    async def test_304_not_modified(self):
        respx.get("https://example.com/feed").mock(return_value=httpx.Response(304))
        fetcher = HttpFetcher(httpx.AsyncClient())
        result = await fetcher.fetch(_FEED, etag='"abc"')
        assert result.not_modified
        assert result.etag == '"abc"'

    async def test_301_moved(self):
        seen: list[str] = []
        fetcher = HttpFetcher(transport=_redirect(301, _MOVED, seen))
        result = await fetcher.fetch(_FEED)
        assert seen == [_FEED.url, _MOVED]
        assert result.moved_to == _MOVED
        assert not result.not_modified

    async def test_308_moved(self):
        fetcher = HttpFetcher(transport=_redirect(308, _MOVED, []))
        result = await fetcher.fetch(_FEED)
        assert result.moved_to == _MOVED

    async def test_temporary_https_redirect_followed_without_move(self):
        seen: list[str] = []
        fetcher = HttpFetcher(transport=_redirect(302, _MOVED, seen))
        result = await fetcher.fetch(_FEED)
        assert seen == [_FEED.url, _MOVED]
        assert result.moved_to is None

    async def test_301_http_location_rejected(self):
        seen: list[str] = []
        fetcher = HttpFetcher(transport=_redirect(301, _INSECURE, seen))
        with pytest.raises(InsecureRedirectError, match=_INSECURE):
            await fetcher.fetch(_FEED)
        assert seen == [_FEED.url]

    async def test_http_hop_after_https_hop_rejected(self):
        seen: list[str] = []
        redirects = {_FEED.url: (302, _MOVED), _MOVED: (302, _INSECURE)}
        transport = redirecting_transport(redirects, _MFEED, seen)
        with pytest.raises(InsecureRedirectError):
            await HttpFetcher(transport=transport).fetch(_FEED)
        assert seen == [_FEED.url, _MOVED]

    async def test_redirect_hops_capped(self):
        hops = [f"https://example.com/{n}" for n in range(MAX_REDIRECT_HOPS + 2)]
        chain = {here: (302, there) for here, there in pairwise(hops)}
        feed = Feed(id=1, url=hops[0], source_type=SourceType.MFEED)
        seen: list[str] = []
        fetcher = HttpFetcher(transport=redirecting_transport(chain, _MFEED, seen))
        with pytest.raises(httpx.TooManyRedirects):
            await fetcher.fetch(feed)
        assert len(seen) == MAX_REDIRECT_HOPS + 1

    async def test_redirect_hops_up_to_cap_followed(self):
        hops = [f"https://example.com/{n}" for n in range(MAX_REDIRECT_HOPS + 1)]
        chain = {here: (302, there) for here, there in pairwise(hops)}
        feed = Feed(id=1, url=hops[0], source_type=SourceType.MFEED)
        seen: list[str] = []
        fetcher = HttpFetcher(transport=redirecting_transport(chain, _MFEED, seen))
        await fetcher.fetch(feed)
        assert seen == hops

    @respx.mock
    async def test_429_raises_rate_limited(self):
        respx.get("https://example.com/feed").mock(
            return_value=httpx.Response(429, headers={"retry-after": "120"})
        )
        fetcher = HttpFetcher(httpx.AsyncClient())
        with pytest.raises(RateLimitedError) as exc_info:
            await fetcher.fetch(_FEED)
        assert exc_info.value.retry_after_seconds == 120

    @respx.mock
    async def test_429_no_retry_after_uses_floor(self):
        respx.get("https://example.com/feed").mock(return_value=httpx.Response(429))
        fetcher = HttpFetcher(httpx.AsyncClient())
        with pytest.raises(RateLimitedError) as exc_info:
            await fetcher.fetch(_FEED)
        assert exc_info.value.retry_after_seconds == 300

    @respx.mock
    async def test_document_too_large_raises(self):
        big = b"x" * (11 * 1024 * 1024)
        respx.get("https://example.com/feed").mock(
            return_value=httpx.Response(200, content=big)
        )
        fetcher = HttpFetcher(httpx.AsyncClient())
        with pytest.raises(ValueError, match="size limit"):
            await fetcher.fetch(_FEED)

    async def test_aclose(self):
        client = httpx.AsyncClient()
        fetcher = HttpFetcher(client)
        await fetcher.aclose()

    def test_default_client_created(self):
        fetcher = HttpFetcher()
        assert fetcher._client is not None

    @respx.mock
    async def test_last_modified_header_sent(self):
        respx.get("https://example.com/feed").mock(
            return_value=httpx.Response(200, content=_MFEED)
        )
        fetcher = HttpFetcher(httpx.AsyncClient())
        result = await fetcher.fetch(
            _FEED, last_modified="Wed, 01 Jan 2026 00:00:00 GMT"
        )
        assert not result.not_modified

    @respx.mock
    async def test_rss_dispatch(self):
        from meridian.domain.entities.feed import Feed
        from meridian.domain.value_objects.source_type import SourceType

        rss_feed = Feed(
            id=2, url="https://example.com/feed", source_type=SourceType.RSS
        )
        rss_body = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>T</title></channel></rss>"""  # noqa: E501
        respx.get("https://example.com/feed").mock(
            return_value=httpx.Response(200, content=rss_body)
        )
        fetcher = HttpFetcher(httpx.AsyncClient())
        result = await fetcher.fetch(rss_feed)
        assert result.items == []

    @respx.mock
    async def test_atom_dispatch(self):
        from meridian.domain.entities.feed import Feed
        from meridian.domain.value_objects.source_type import SourceType

        atom_feed = Feed(
            id=3, url="https://example.com/feed", source_type=SourceType.ATOM
        )
        atom_body = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>T</title></feed>"""  # noqa: E501
        respx.get("https://example.com/feed").mock(
            return_value=httpx.Response(200, content=atom_body)
        )
        fetcher = HttpFetcher(httpx.AsyncClient())
        result = await fetcher.fetch(atom_feed)
        assert result.items == []

    @respx.mock
    async def test_podcast_dispatch(self):
        from meridian.domain.entities.feed import Feed
        from meridian.domain.value_objects.source_type import SourceType

        pod_feed = Feed(
            id=4, url="https://example.com/feed", source_type=SourceType.PODCAST
        )
        pod_body = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>T</title></channel></rss>"""  # noqa: E501
        respx.get("https://example.com/feed").mock(
            return_value=httpx.Response(200, content=pod_body)
        )
        fetcher = HttpFetcher(httpx.AsyncClient())
        result = await fetcher.fetch(pod_feed)
        assert result.items == []

    @respx.mock
    async def test_platform_dispatch(self):
        from meridian.domain.entities.feed import Feed
        from meridian.domain.value_objects.source_type import SourceType

        plat_feed = Feed(
            id=5,
            url="https://example.com/feed",
            source_type=SourceType.PLATFORM,
            platform_id="test-platform",
        )
        rss_body = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>T</title></channel></rss>"""  # noqa: E501
        respx.get("https://example.com/feed").mock(
            return_value=httpx.Response(200, content=rss_body)
        )
        fetcher = HttpFetcher(httpx.AsyncClient())
        result = await fetcher.fetch(plat_feed)
        assert result.items == []
