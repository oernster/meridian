from meridian.application.dto.feed_candidate_dto import FeedCandidateDTO
from meridian.application.interfaces.discovery_fetcher import DiscoveryFetcher
from meridian.application.interfaces.feed_repository import FeedRepository


class DiscoveryService:
    def __init__(
        self,
        fetcher: DiscoveryFetcher,
        feed_repo: FeedRepository,
    ) -> None:
        self._fetcher = fetcher
        self._feed_repo = feed_repo

    async def search(
        self,
        query: str,
        limit: int = 25,
        page: int = 0,
    ) -> list[FeedCandidateDTO]:
        candidates = await self._fetcher.search(query, limit=limit, page=page)
        subscribed_urls = {f.url for f in self._feed_repo.list_all()}
        return [
            FeedCandidateDTO(
                url=c.url,
                title=c.title,
                description=c.description,
                favicon_url=c.favicon_url,
                source_type=c.source_type,
                is_subscribed=c.url in subscribed_urls,
            )
            for c in candidates
        ]
