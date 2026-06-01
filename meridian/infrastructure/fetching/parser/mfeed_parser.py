"""Parser for native MMSP feed manifests (mfeed source type)."""

from __future__ import annotations

import json
from datetime import datetime, timezone

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


def parse(
    feed_id: int, feed_url: str, raw_bytes: bytes
) -> tuple[list[Item], PollConfig]:
    data = json.loads(raw_bytes)
    poll_data = data.get("poll", {})
    min_interval = max(
        poll_data.get("min_interval_seconds", POLL_FLOOR_SECONDS),
        POLL_FLOOR_SECONDS,
    )
    poll_config = PollConfig(
        min_interval_seconds=min_interval,
        recommended_interval_seconds=poll_data.get("recommended_interval_seconds"),
        ttl_seconds=poll_data.get("ttl_seconds"),
    )
    feed_title = data.get("title")
    items = [
        _parse_item(feed_id, feed_url, feed_title, raw_item)
        for raw_item in data.get("items", [])
    ]
    return items, poll_config


def _parse_item(feed_id: int, feed_url: str, feed_title: str | None, raw: dict) -> Item:
    return Item(
        feed_id=feed_id,
        item_id=raw["id"],
        type=ItemType.from_str(raw.get("type", "article")),
        title=raw["title"],
        url=raw["url"],
        published=_parse_dt(raw["published"]),
        updated=_parse_dt(raw["updated"]) if raw.get("updated") else None,
        description=raw.get("description"),
        language=raw.get("language"),
        duration=raw.get("duration"),
        canonical_url=raw.get("canonical_url"),
        preview_url=raw.get("preview_url"),
        license=raw.get("license"),
        live_status=raw.get("live_status"),
        scheduled_start=(
            _parse_dt(raw["scheduled_start"]) if raw.get("scheduled_start") else None
        ),
        expires=_parse_dt(raw["expires"]) if raw.get("expires") else None,
        authors=tuple(_parse_author(a) for a in raw.get("authors", [])),
        tags=tuple(raw.get("tags", [])),
        media=tuple(_parse_media(m) for m in raw.get("media", [])),
        thumbnail=tuple(_parse_thumbnail(t) for t in raw.get("thumbnail", [])),
        chapters=tuple(_parse_chapter(c) for c in raw.get("chapters", [])),
        captions=tuple(_parse_caption(c) for c in raw.get("captions", [])),
        transcript=(
            _parse_transcript(raw["transcript"]) if raw.get("transcript") else None
        ),
        series=_parse_series(raw["series"]) if raw.get("series") else None,
        content_rating=(
            _parse_content_rating(raw["content_rating"])
            if raw.get("content_rating")
            else None
        ),
        geo_restriction=(
            _parse_geo(raw["geo_restriction"]) if raw.get("geo_restriction") else None
        ),
        paywall=_parse_paywall(raw["paywall"]) if raw.get("paywall") else None,
        source=ItemSource(type="mfeed", feed_url=feed_url, feed_title=feed_title),
    )


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


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
    return GeoRestriction(type=raw["type"], regions=tuple(raw["regions"]))


def _parse_paywall(raw: dict) -> Paywall:
    return Paywall(
        paywalled=raw["paywalled"],
        preview_available=raw.get("preview_available", False),
    )
