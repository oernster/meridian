from datetime import datetime, timezone

from meridian.application.dto.item_dto import AuthorDTO, ItemDTO, MediaDTO
from meridian.application.interfaces.feed_repository import FeedRepository
from meridian.application.interfaces.item_repository import ItemRepository
from meridian.domain.entities.item import Item
from meridian.domain.services.deduplication import deduplicate
from meridian.domain.services.filter_evaluator import FilterEvaluator
from meridian.domain.value_objects.filter_expression import FilterExpression


class ItemService:
    def __init__(
        self,
        item_repo: ItemRepository,
        feed_repo: FeedRepository,
    ) -> None:
        self._item_repo = item_repo
        self._feed_repo = feed_repo

    def get_items(self, feed_id: int) -> list[ItemDTO]:
        feed = self._feed_repo.get_by_id(feed_id)
        items = self._item_repo.list_by_feed(feed_id)
        items = deduplicate(items)
        if feed and feed.filter_expr:
            evaluator = FilterEvaluator(FilterExpression(feed.filter_expr))
            items = evaluator.filter(items)
        return [self._to_dto(i) for i in items]

    def mark_read(self, item_id: int) -> None:
        self._item_repo.mark_read(item_id, datetime.now(tz=timezone.utc))

    def mark_all_read(self, feed_id: int) -> None:
        self._item_repo.mark_all_read(feed_id, datetime.now(tz=timezone.utc))

    def _to_dto(self, item: Item) -> ItemDTO:
        return ItemDTO(
            id=item.id,
            feed_id=item.feed_id,
            item_id=item.item_id,
            type=item.type.value,
            title=item.title,
            url=item.url,
            published_iso=item.published.isoformat(),
            description=item.description,
            thumbnail_url=item.primary_thumbnail_url(),
            duration=item.duration,
            is_read=item.is_read,
            language=item.language,
            live_status=item.live_status,
            authors=tuple(
                AuthorDTO(name=a.name, url=a.url, avatar=a.avatar) for a in item.authors
            ),
            tags=item.tags,
            media=tuple(
                MediaDTO(
                    url=m.url,
                    mime_type=m.mime_type,
                    role=m.role,
                    duration=m.duration,
                    width=m.width,
                    height=m.height,
                    quality_label=m.quality_label,
                )
                for m in item.media
            ),
        )
