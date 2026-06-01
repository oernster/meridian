"""Parser for podcast feeds (RSS + iTunes/Podcast Index namespace, Appendix D)."""
from __future__ import annotations

from datetime import datetime, timezone

import defusedxml.ElementTree as ET

from meridian.domain.entities.item import Item
from meridian.domain.value_objects.item_type import ItemType
from meridian.domain.value_objects.media import (
    Author, ContentRating, ItemSource, Media, Series, Thumbnail, Transcript,
)
from meridian.domain.value_objects.poll_config import PollConfig, POLL_FLOOR_SECONDS
from meridian.infrastructure.fetching.parser import rss_parser

_ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
_PC_NS = "https://podcastindex.org/namespace/1.0"


def parse(feed_id: int, feed_url: str, raw_bytes: bytes) -> tuple[list[Item], PollConfig]:
    root = ET.fromstring(raw_bytes)
    channel_el = root.find("channel")
    channel = channel_el if channel_el is not None else root
    feed_title = rss_parser._text(channel, "title")
    items = [
        _parse_item(feed_id, feed_url, feed_title, el)
        for el in channel.findall("item")
    ]
    ttl_el = channel.find("ttl")
    min_interval = POLL_FLOOR_SECONDS
    if ttl_el is not None and ttl_el.text:
        try:
            min_interval = max(int(ttl_el.text) * 60, POLL_FLOOR_SECONDS)
        except ValueError:
            pass
    return items, PollConfig(min_interval_seconds=min_interval)


def _parse_item(feed_id: int, feed_url: str, feed_title: str | None, el) -> Item:
    base = rss_parser._parse_item(feed_id, feed_url, feed_title, el)
    itunes_title = _itunes(el, "title")
    title = itunes_title or base.title
    duration = _parse_duration(el)
    episode_num = _itunes_int(el, "episode")
    season_num = _itunes_int(el, "season")
    series: Series | None = None
    if episode_num is not None or season_num is not None:
        series = Series(
            id=f"{feed_url}#series",
            title=feed_title or "Podcast",
            episode_number=episode_num,
            season_number=season_num,
        )
    thumb_url = _itunes_attr(el, "image", "href")
    thumbnail = base.thumbnail
    if thumb_url and thumb_url.startswith("https://") and not thumbnail:
        thumbnail = (Thumbnail(url=thumb_url),)
    explicit = _itunes(el, "explicit")
    content_rating: ContentRating | None = None
    if explicit is not None:
        rating = "explicit" if explicit.lower() == "yes" else "general"
        content_rating = ContentRating(rating=rating)
    transcript_url = _pc_attr(el, "transcript", "url")
    transcript_mime = _pc_attr(el, "transcript", "type")
    transcript_lang = _pc_attr(el, "transcript", "language")
    transcript: Transcript | None = None
    if transcript_url and transcript_mime and transcript_url.startswith("https://"):
        transcript = Transcript(
            url=transcript_url,
            mime_type=transcript_mime,
            language=transcript_lang,
        )
    host_name = _pc_person(el, "host")
    authors = base.authors
    if host_name and not authors:
        authors = (Author(name=host_name),)
    return Item(
        feed_id=base.feed_id,
        item_id=base.item_id,
        type=ItemType.AUDIO,
        title=title,
        url=base.url,
        published=base.published,
        description=base.description,
        duration=duration,
        authors=authors,
        tags=base.tags,
        media=base.media,
        thumbnail=thumbnail,
        series=series,
        content_rating=content_rating,
        transcript=transcript,
        source=ItemSource(type="podcast", feed_url=feed_url, feed_title=feed_title),
    )


def _parse_duration(el) -> int | None:
    raw = _itunes(el, "duration")
    if raw is None:
        return None
    parts = raw.split(":")
    try:
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + int(s)
        if len(parts) == 2:
            m, s = parts
            return int(m) * 60 + int(s)
        return int(parts[0])
    except ValueError:
        return None


def _itunes(el, tag: str) -> str | None:
    child = el.find(f"{{{_ITUNES_NS}}}{tag}")
    return child.text.strip() if child is not None and child.text else None


def _itunes_int(el, tag: str) -> int | None:
    val = _itunes(el, tag)
    try:
        return int(val) if val else None
    except ValueError:
        return None


def _itunes_attr(el, tag: str, attr: str) -> str | None:
    child = el.find(f"{{{_ITUNES_NS}}}{tag}")
    return child.get(attr) if child is not None else None


def _pc_attr(el, tag: str, attr: str) -> str | None:
    child = el.find(f"{{{_PC_NS}}}{tag}")
    return child.get(attr) if child is not None else None


def _pc_person(el, role: str) -> str | None:
    for person_el in el.findall(f"{{{_PC_NS}}}person"):
        if person_el.get("role", "").lower() == role and person_el.text:
            return person_el.text.strip()
    return None
