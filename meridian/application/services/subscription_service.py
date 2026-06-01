from meridian.application.dto.feed_dto import FeedDTO
from meridian.application.interfaces.feed_repository import FeedRepository
from meridian.application.interfaces.item_repository import ItemRepository
from meridian.domain.entities.feed import Feed
from meridian.domain.value_objects.source_type import SourceType


class SubscriptionService:
    def __init__(
        self,
        feed_repo: FeedRepository,
        item_repo: ItemRepository,
    ) -> None:
        self._feed_repo = feed_repo
        self._item_repo = item_repo

    def subscribe(
        self,
        url: str,
        source_type: str,
        platform_id: str | None = None,
        rss_fallback_url: str | None = None,
    ) -> FeedDTO:
        existing = self._feed_repo.get_by_url(url)
        if existing is not None:
            return self._to_dto(existing)
        feed = Feed(
            url=url,
            source_type=SourceType(source_type),
            platform_id=platform_id,
            rss_fallback_url=rss_fallback_url,
        )
        saved = self._feed_repo.save(feed)
        return self._to_dto(saved)

    def unsubscribe(self, feed_id: int) -> None:
        self._feed_repo.delete(feed_id)

    def list_feeds(self) -> list[FeedDTO]:
        feeds = self._feed_repo.list_all()
        return [self._to_dto(f) for f in feeds]

    def get_feed(self, feed_id: int) -> FeedDTO | None:
        feed = self._feed_repo.get_by_id(feed_id)
        return self._to_dto(feed) if feed else None

    def set_filter(self, feed_id: int, filter_expr: str | None) -> None:
        self._feed_repo.update_filter(feed_id, filter_expr)

    def _to_dto(self, feed: Feed) -> FeedDTO:
        unread = self._item_repo.unread_count(feed.id) if feed.is_saved() else 0
        return FeedDTO(
            id=feed.id,
            url=feed.url,
            source_type=feed.source_type.value,
            title=feed.title,
            description=feed.description,
            icon=feed.icon,
            language=feed.language,
            filter_expr=feed.filter_expr,
            unread_count=unread,
            platform_id=feed.platform_id,
            rss_fallback_url=feed.rss_fallback_url,
        )
