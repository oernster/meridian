from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class PollState:
    feed_id: int
    last_polled: datetime | None = None
    next_poll: datetime | None = None
    etag: str | None = None
    last_modified: str | None = None
    backoff_until: datetime | None = None
    moved_to: str | None = None
    deprecated: bool = False
    deprecated_reason: str | None = None


class PollStateRepository(ABC):
    @abstractmethod
    def get(self, feed_id: int) -> PollState:
        ...

    @abstractmethod
    def save(self, state: PollState) -> None:
        ...
