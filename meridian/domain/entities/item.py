from dataclasses import dataclass
from datetime import datetime

from meridian.domain.value_objects.item_type import ItemType
from meridian.domain.value_objects.media import (
    Author,
    Caption,
    Chapter,
    ContentRating,
    GeoRestriction,
    ItemSource,
    Media,
    Paywall,
    Series,
    Thumbnail,
    Transcript,
)

UNSET_ID = 0


@dataclass(frozen=True, slots=True)
class Item:
    item_id: str
    type: ItemType
    title: str
    url: str
    published: datetime
    feed_id: int = UNSET_ID
    id: int = UNSET_ID
    updated: datetime | None = None
    description: str | None = None
    language: str | None = None
    duration: int | None = None
    canonical_url: str | None = None
    preview_url: str | None = None
    license: str | None = None
    live_status: str | None = None
    scheduled_start: datetime | None = None
    expires: datetime | None = None
    authors: tuple[Author, ...] = ()
    tags: tuple[str, ...] = ()
    media: tuple[Media, ...] = ()
    thumbnail: tuple[Thumbnail, ...] = ()
    chapters: tuple[Chapter, ...] = ()
    captions: tuple[Caption, ...] = ()
    transcript: Transcript | None = None
    series: Series | None = None
    content_rating: ContentRating | None = None
    geo_restriction: GeoRestriction | None = None
    paywall: Paywall | None = None
    source: ItemSource | None = None
    is_read: bool = False

    def primary_thumbnail_url(self) -> str | None:
        return self.thumbnail[0].url if self.thumbnail else None

    def primary_media_url(self) -> str | None:
        primary = [m for m in self.media if m.role == "primary"]
        return primary[0].url if primary else None

    def is_media_type(self) -> bool:
        return self.type in (
            ItemType.VIDEO,
            ItemType.AUDIO,
            ItemType.SHORT,
            ItemType.LIVESTREAM,
        )
