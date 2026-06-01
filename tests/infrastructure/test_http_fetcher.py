import json

import httpx
import pytest
import respx

from meridian.domain.entities.feed import Feed
from meridian.domain.value_objects.source_type import SourceType
from meridian.infrastructure.fetching.http_fetcher import HttpFetcher, RateLimitedError

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

    @respx.mock
    async def test_301_moved(self):
        respx.get("https://example.com/feed").mock(
            return_value=httpx.Response(
                301, headers={"location": "https://new.example.com/feed"}
            )
        )
        fetcher = HttpFetcher(httpx.AsyncClient())
        result = await fetcher.fetch(_FEED)
        assert result.moved_to == "https://new.example.com/feed"

    @respx.mock
    async def test_301_http_location_rejected(self):
        respx.get("https://example.com/feed").mock(
            return_value=httpx.Response(
                301, headers={"location": "http://insecure.example.com/feed"}
            )
        )
        fetcher = HttpFetcher(httpx.AsyncClient())
        result = await fetcher.fetch(_FEED)
        assert result.moved_to is None

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
