from abc import ABC, abstractmethod

from meridian.application.dto.feed_candidate_dto import FeedCandidateDTO

DEFAULT_RESULT_CAP = 25


class DiscoveryError(Exception):
    pass


class DiscoveryFetcher(ABC):
    @abstractmethod
    async def search(
        self,
        query: str,
        limit: int = DEFAULT_RESULT_CAP,
        page: int = 0,
    ) -> list[FeedCandidateDTO]: ...
