from abc import ABC, abstractmethod

from meridian.domain.entities.feed import Feed


class FeedRepository(ABC):
    @abstractmethod
    def save(self, feed: Feed) -> Feed: ...

    @abstractmethod
    def get_by_id(self, feed_id: int) -> Feed | None: ...

    @abstractmethod
    def get_by_url(self, url: str) -> Feed | None: ...

    @abstractmethod
    def list_all(self) -> list[Feed]: ...

    @abstractmethod
    def delete(self, feed_id: int) -> None: ...

    @abstractmethod
    def update_filter(self, feed_id: int, filter_expr: str | None) -> None: ...

    @abstractmethod
    def update_title(self, feed_id: int, title: str) -> None: ...
