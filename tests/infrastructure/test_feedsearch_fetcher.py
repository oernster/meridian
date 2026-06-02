import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from meridian.application.interfaces.discovery_fetcher import DiscoveryError
from meridian.infrastructure.fetching.feedsearch_fetcher import (
    FeedsearchFetcher,
    _extract_url,
    _parse_candidate,
)
from meridian.domain.value_objects.source_type import SourceType


def _run(coro):
    return asyncio.run(coro)


def _mock_response(data, status_code: int = 200) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = data
    resp.raise_for_status = MagicMock()
    return resp


def _mock_error_response(status_code: int) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    err = httpx.HTTPStatusError("error", request=MagicMock(), response=resp)
    resp.raise_for_status.side_effect = err
    return resp


def _feedly_item(
    feed_id: str = "feed/https://example.com/feed.xml",
    title: str = "Example",
    description: str = "A feed",
    icon_url: str = "https://example.com/icon.png",
) -> dict:
    return {
        "feedId": feed_id,
        "title": title,
        "description": description,
        "iconUrl": icon_url,
    }


class TestFeedsearchFetcher:
    def test_successful_search(self):
        data = {"results": [_feedly_item()]}
        client = MagicMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response(data))
        fetcher = FeedsearchFetcher(client=client)
        results = _run(fetcher.search("python"))
        assert len(results) == 1
        assert results[0].url == "https://example.com/feed.xml"
        assert results[0].title == "Example"

    def test_passes_query_and_limit(self):
        client = MagicMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response({"results": []}))
        fetcher = FeedsearchFetcher(client=client)
        _run(fetcher.search("tech", limit=50))
        call_kwargs = client.get.call_args
        assert call_kwargs.kwargs["params"]["query"] == "tech"
        assert call_kwargs.kwargs["params"]["count"] == 50

    def test_page_param_accepted_but_not_forwarded(self):
        client = MagicMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response({"results": []}))
        fetcher = FeedsearchFetcher(client=client)
        _run(fetcher.search("tech", limit=25, page=2))
        params = client.get.call_args.kwargs["params"]
        assert "start" not in params

    def test_timeout_raises_discovery_error(self):
        client = MagicMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        fetcher = FeedsearchFetcher(client=client)
        with pytest.raises(DiscoveryError, match="timed out"):
            _run(fetcher.search("python"))

    def test_connect_error_raises_discovery_error(self):
        client = MagicMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        fetcher = FeedsearchFetcher(client=client)
        with pytest.raises(DiscoveryError, match="reach"):
            _run(fetcher.search("python"))

    def test_http_status_error_raises_discovery_error(self):
        client = MagicMock(spec=httpx.AsyncClient)
        resp = _mock_error_response(403)
        client.get = AsyncMock(return_value=resp)
        fetcher = FeedsearchFetcher(client=client)
        with pytest.raises(DiscoveryError, match="403"):
            _run(fetcher.search("python"))

    def test_unexpected_response_not_dict_raises_discovery_error(self):
        client = MagicMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response([]))
        fetcher = FeedsearchFetcher(client=client)
        with pytest.raises(DiscoveryError, match="format"):
            _run(fetcher.search("python"))

    def test_unexpected_response_missing_results_key(self):
        client = MagicMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response({"other": "data"}))
        fetcher = FeedsearchFetcher(client=client)
        with pytest.raises(DiscoveryError, match="format"):
            _run(fetcher.search("python"))

    def test_items_missing_url_skipped(self):
        data = {
            "results": [
                {"feedId": "", "website": "", "title": "No URL"},
                _feedly_item(feed_id="feed/https://valid.com/feed"),
            ]
        }
        client = MagicMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response(data))
        fetcher = FeedsearchFetcher(client=client)
        results = _run(fetcher.search("python"))
        assert len(results) == 1
        assert results[0].url == "https://valid.com/feed"

    def test_empty_results(self):
        client = MagicMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response({"results": []}))
        fetcher = FeedsearchFetcher(client=client)
        results = _run(fetcher.search("obscure"))
        assert results == []

    def test_non_dict_items_skipped(self):
        data = {"results": ["string", None, {}]}
        client = MagicMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(return_value=_mock_response(data))
        fetcher = FeedsearchFetcher(client=client)
        results = _run(fetcher.search("python"))
        assert results == []

    def test_cancelled_error_propagates(self):
        client = MagicMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(side_effect=asyncio.CancelledError())
        fetcher = FeedsearchFetcher(client=client)
        with pytest.raises(asyncio.CancelledError):
            _run(fetcher.search("python"))

    def test_discovery_error_reraises(self):
        client = MagicMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(side_effect=DiscoveryError("already wrapped"))
        fetcher = FeedsearchFetcher(client=client)
        with pytest.raises(DiscoveryError, match="already wrapped"):
            _run(fetcher.search("python"))

    def test_unexpected_exception_wrapped(self):
        client = MagicMock(spec=httpx.AsyncClient)
        client.get = AsyncMock(side_effect=RuntimeError("unexpected"))
        fetcher = FeedsearchFetcher(client=client)
        with pytest.raises(DiscoveryError, match="Unexpected error"):
            _run(fetcher.search("python"))

    def test_aclose(self):
        client = MagicMock(spec=httpx.AsyncClient)
        client.aclose = AsyncMock()
        fetcher = FeedsearchFetcher(client=client)
        _run(fetcher.aclose())
        client.aclose.assert_awaited_once()


class TestExtractUrl:
    def test_strips_feed_prefix(self):
        assert (
            _extract_url({"feedId": "feed/https://example.com/feed"})
            == "https://example.com/feed"
        )

    def test_falls_back_to_website(self):
        assert (
            _extract_url(
                {"feedId": "https://example.com/feed", "website": "https://example.com"}
            )
            == "https://example.com"
        )

    def test_empty_feed_id_uses_website(self):
        assert (
            _extract_url({"feedId": "", "website": "https://example.com/rss"})
            == "https://example.com/rss"
        )

    def test_missing_both_returns_empty(self):
        assert _extract_url({}) == ""


class TestParseCandidate:
    def test_url_extracted_from_feed_id(self):
        item = _feedly_item(feed_id="feed/https://example.com/rss")
        c = _parse_candidate(item)
        assert c.url == "https://example.com/rss"

    def test_source_type_inferred_from_url(self):
        item = _feedly_item(feed_id="feed/https://example.com/feed.atom")
        c = _parse_candidate(item)
        assert c.source_type == SourceType.ATOM.value

    def test_empty_title_becomes_none(self):
        item = _feedly_item()
        item["title"] = ""
        c = _parse_candidate(item)
        assert c.title is None

    def test_empty_description_becomes_none(self):
        item = _feedly_item()
        item["description"] = ""
        c = _parse_candidate(item)
        assert c.description is None

    def test_favicon_from_icon_url(self):
        item = _feedly_item(icon_url="https://example.com/icon.png")
        c = _parse_candidate(item)
        assert c.favicon_url == "https://example.com/icon.png"

    def test_favicon_none_when_missing(self):
        item = {"feedId": "feed/https://example.com/feed"}
        c = _parse_candidate(item)
        assert c.favicon_url is None
