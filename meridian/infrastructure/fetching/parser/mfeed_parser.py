"""Parser for native MMSP feed manifests (mfeed source type).

The manifest is rejected whole only where MMSP 5.6 says so: an unsupported
version, a document that is not a JSON object or an `items` member that is
not an array. An item is skipped alone where MMSP 6.15 says so; a
malformed optional field is dropped from an item that is kept; the readers in
`mfeed_fields` carry both rules. One bad item used to discard the whole feed.
"""

from __future__ import annotations

import json
import logging

from meridian.domain.entities.item import Item
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
from meridian.domain.value_objects.poll_config import PollConfig, POLL_FLOOR_SECONDS
from meridian.infrastructure.fetching.mmsp import (
    PROTOCOL_MAJOR,
    PROTOCOL_VERSION,
    accepts_document_version,
)
from meridian.infrastructure.fetching.parser.https_only import is_https
from meridian.infrastructure.fetching.parser.mfeed_fields import (
    InvalidItem,
    entries,
    optional_int,
    optional_object,
    optional_text,
    optional_time,
    required_text,
    required_time,
    texts,
)

_LOG = logging.getLogger(__name__)


def parse(
    feed_id: int, feed_url: str, raw_bytes: bytes
) -> tuple[list[Item], PollConfig]:
    data = json.loads(raw_bytes)
    if not isinstance(data, dict):
        raise ValueError("The document is not an MMSP feed: it is not a JSON object")

    declared = data.get("mmsp")
    if not accepts_document_version(declared):
        raise ValueError(
            f"Unsupported MMSP document version {declared!r}: this client "
            f"speaks {PROTOCOL_VERSION} and reads any {PROTOCOL_MAJOR}.x feed"
        )
    raw_items = data.get("items")
    if not isinstance(raw_items, list):
        raise ValueError("The feed's REQUIRED items member is not an array")

    feed_title = optional_text(data, "title")
    items: list[Item] = []
    for raw in raw_items:
        try:
            items.append(_parse_item(feed_id, feed_url, feed_title, raw))
        except InvalidItem:
            continue
    skipped = len(raw_items) - len(items)
    if skipped:
        _LOG.warning(
            "Feed %d (%s): skipped %d of %d items that break MMSP 6.1",
            feed_id,
            feed_url,
            skipped,
            len(raw_items),
        )
    return items, _poll_config(data.get("poll"))


def _poll_config(raw: object) -> PollConfig:
    poll = raw if isinstance(raw, dict) else {}
    return PollConfig(
        min_interval_seconds=optional_int(poll, "min_interval_seconds")
        or POLL_FLOOR_SECONDS,
        recommended_interval_seconds=optional_int(poll, "recommended_interval_seconds"),
        ttl_seconds=optional_int(poll, "ttl_seconds"),
    )


def _parse_item(
    feed_id: int, feed_url: str, feed_title: str | None, raw: object
) -> Item:
    if not isinstance(raw, dict):
        raise InvalidItem("the item is not an object")
    return Item(
        feed_id=feed_id,
        item_id=required_text(raw, "id"),
        type=ItemType.from_str(required_text(raw, "type")),
        title=required_text(raw, "title"),
        url=required_text(raw, "url"),
        published=required_time(raw, "published"),
        updated=optional_time(raw, "updated"),
        description=optional_text(raw, "description"),
        language=optional_text(raw, "language"),
        duration=optional_int(raw, "duration"),
        canonical_url=optional_text(raw, "canonical_url"),
        preview_url=optional_text(raw, "preview_url"),
        license=optional_text(raw, "license"),
        live_status=optional_text(raw, "live_status"),
        scheduled_start=optional_time(raw, "scheduled_start"),
        expires=optional_time(raw, "expires"),
        authors=entries(raw, "authors", _parse_author),
        tags=texts(raw, "tags"),
        media=entries(raw, "media", _parse_media, keep=_secure),
        thumbnail=entries(raw, "thumbnail", _parse_thumbnail, keep=_secure),
        chapters=entries(raw, "chapters", _parse_chapter),
        captions=entries(raw, "captions", _parse_caption, keep=_secure),
        transcript=optional_object(raw, "transcript", _parse_transcript),
        series=optional_object(raw, "series", _parse_series),
        content_rating=optional_object(raw, "content_rating", _parse_content_rating),
        geo_restriction=optional_object(raw, "geo_restriction", _parse_geo),
        paywall=optional_object(raw, "paywall", _parse_paywall),
        source=ItemSource(type="mfeed", feed_url=feed_url, feed_title=feed_title),
    )


def _secure(entry: dict) -> bool:
    """Whether Meridian may fetch the entry's address: HTTPS only."""
    return is_https(entry.get("url"))


def _parse_author(raw: dict) -> Author:
    return Author(name=raw["name"], url=raw.get("url"), avatar=raw.get("avatar"))


def _parse_media(raw: dict) -> Media:
    return Media(
        url=raw["url"],
        mime_type=raw["mime_type"],
        size_bytes=raw.get("size_bytes"),
        duration=raw.get("duration"),
        width=raw.get("width"),
        height=raw.get("height"),
        bitrate_kbps=raw.get("bitrate_kbps"),
        role=raw.get("role", "primary"),
        quality_label=raw.get("quality_label"),
    )


def _parse_thumbnail(raw: dict) -> Thumbnail:
    return Thumbnail(url=raw["url"], width=raw.get("width"), height=raw.get("height"))


def _parse_chapter(raw: dict) -> Chapter:
    return Chapter(
        title=raw["title"],
        start_seconds=raw["start_seconds"],
        end_seconds=raw.get("end_seconds"),
        image_url=raw.get("image_url"),
    )


def _parse_transcript(raw: dict) -> Transcript:
    if not is_https(raw.get("url")):
        raise ValueError("a transcript is only fetched over HTTPS")
    return Transcript(
        url=raw["url"], mime_type=raw["mime_type"], language=raw.get("language")
    )


def _parse_caption(raw: dict) -> Caption:
    return Caption(
        url=raw["url"],
        mime_type=raw["mime_type"],
        language=raw["language"],
        label=raw.get("label"),
    )


def _parse_series(raw: dict) -> Series:
    return Series(
        id=raw["id"],
        title=raw["title"],
        episode_number=raw.get("episode_number"),
        season_number=raw.get("season_number"),
        total_episodes=raw.get("total_episodes"),
    )


def _parse_content_rating(raw: dict) -> ContentRating:
    return ContentRating(
        rating=raw["rating"],
        system=raw.get("system"),
        descriptors=tuple(raw.get("descriptors", [])),
        spoiler=raw.get("spoiler", False),
    )


def _parse_geo(raw: dict) -> GeoRestriction:
    regions = raw["regions"]
    if not isinstance(regions, list):
        raise TypeError("regions is not an array")
    return GeoRestriction(type=raw["type"], regions=tuple(regions))


def _parse_paywall(raw: dict) -> Paywall:
    return Paywall(
        paywalled=raw["paywalled"],
        preview_available=raw.get("preview_available", False),
    )
