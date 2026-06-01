from abc import ABC, abstractmethod
from datetime import datetime

from meridian.domain.entities.item import Item


class ItemRepository(ABC):
    @abstractmethod
    def save(self, item: Item) -> Item: ...

    @abstractmethod
    def save_many(self, items: list[Item]) -> list[Item]: ...

    @abstractmethod
    def get_by_id(self, item_id: int) -> Item | None: ...

    @abstractmethod
    def list_by_feed(self, feed_id: int) -> list[Item]: ...

    @abstractmethod
    def mark_read(self, item_id: int, read_at: datetime) -> None: ...

    @abstractmethod
    def mark_all_read(self, feed_id: int, read_at: datetime) -> None: ...

    @abstractmethod
    def unread_count(self, feed_id: int) -> int: ...

    @abstractmethod
    def exists(self, feed_id: int, item_id_uri: str) -> bool: ...
