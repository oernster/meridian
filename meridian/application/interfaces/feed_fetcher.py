from abc import ABC, abstractmethod
from dataclasses import dataclass

from meridian.domain.entities.feed import Feed
from meridian.domain.entities.item import Item
from meridian.domain.value_objects.poll_config import PollConfig


@dataclass(frozen=True, slots=True)
class FetchResult:
    items: list[Item]
    poll_config: PollConfig
    etag: str | None
    last_modified: str | None
    moved_to: str | None
    not_modified: bool = False


class FeedFetcher(ABC):
    @abstractmethod
    async def fetch(
        self,
        feed: Feed,
        etag: str | None = None,
        last_modified: str | None = None,
    ) -> FetchResult:
        ...
