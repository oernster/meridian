import asyncio
from unittest.mock import AsyncMock, MagicMock

from meridian.application.dto.feed_candidate_dto import FeedCandidateDTO
from meridian.application.services.discovery_service import DiscoveryService
from meridian.domain.entities.feed import Feed
from meridian.domain.value_objects.source_type import SourceType


def _candidate(url: str = "https://example.com/feed") -> FeedCandidateDTO:
    return FeedCandidateDTO(
        url=url,
        title="Feed",
        description="A feed",
        favicon_url=None,
        source_type="rss",
    )


def _feed(url: str) -> Feed:
    return Feed(id=1, url=url, source_type=SourceType.RSS)


class TestDiscoveryService:
    def setup_method(self):
        self.fetcher = MagicMock()
        self.feed_repo = MagicMock()
        self.svc = DiscoveryService(self.fetcher, self.feed_repo)

    def _run(self, coro):
        return asyncio.run(coro)

    def test_search_returns_candidates(self):
        self.fetcher.search = AsyncMock(return_value=[_candidate()])
        self.feed_repo.list_all.return_value = []
        results = self._run(self.svc.search("python"))
        assert len(results) == 1
        assert results[0].url == "https://example.com/feed"

    def test_search_passes_limit_and_page(self):
        self.fetcher.search = AsyncMock(return_value=[])
        self.feed_repo.list_all.return_value = []
        self._run(self.svc.search("tech", limit=50, page=2))
        self.fetcher.search.assert_awaited_once_with("tech", limit=50, page=2)

    def test_is_subscribed_flagged_for_known_url(self):
        url = "https://example.com/feed"
        self.fetcher.search = AsyncMock(return_value=[_candidate(url)])
        self.feed_repo.list_all.return_value = [_feed(url)]
        results = self._run(self.svc.search("python"))
        assert results[0].is_subscribed is True

    def test_is_subscribed_false_for_new_url(self):
        self.fetcher.search = AsyncMock(
            return_value=[_candidate("https://new.com/feed")]
        )
        self.feed_repo.list_all.return_value = [_feed("https://existing.com/feed")]
        results = self._run(self.svc.search("python"))
        assert results[0].is_subscribed is False

    def test_empty_results(self):
        self.fetcher.search = AsyncMock(return_value=[])
        self.feed_repo.list_all.return_value = []
        results = self._run(self.svc.search("obscure"))
        assert results == []

    def test_multiple_candidates_mixed_subscribed(self):
        candidates = [
            _candidate("https://a.com/feed"),
            _candidate("https://b.com/feed"),
            _candidate("https://c.com/feed"),
        ]
        self.fetcher.search = AsyncMock(return_value=candidates)
        self.feed_repo.list_all.return_value = [_feed("https://b.com/feed")]
        results = self._run(self.svc.search("tech"))
        assert results[0].is_subscribed is False
        assert results[1].is_subscribed is True
        assert results[2].is_subscribed is False
