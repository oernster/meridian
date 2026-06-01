"""Parser for RSS 2.0 and RSS 1.0 (RDF) feeds."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import defusedxml.ElementTree as ET

from meridian.domain.entities.item import Item
from meridian.domain.value_objects.item_type import ItemType
from meridian.domain.value_objects.media import Author, ItemSource, Media, Thumbnail
from meridian.domain.value_objects.poll_config import PollConfig, POLL_FLOOR_SECONDS

_MEDIA_NS = "http://search.yahoo.com/mrss/"
_DC_NS = "http://purl.org/dc/elements/1.1/"
_CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"
_RSS1_DEFAULT_NS = b'xmlns="http://purl.org/rss/1.0/"'


def parse(
    feed_id: int, feed_url: str, raw_bytes: bytes
) -> tuple[list[Item], PollConfig]:
    # Strip RSS 1.0 default namespace so element names become unqualified.
    # RSS 1.0 (RDF) puts <item> elements as siblings of <channel> at root level.
    raw_bytes = raw_bytes.replace(_RSS1_DEFAULT_NS, b"")
    root = ET.fromstring(raw_bytes)
    channel_el = root.find("channel")
    channel = channel_el if channel_el is not None else root
    feed_title = _text(channel, "title")
    item_els = channel.findall("item") or root.findall("item")
    items = [_parse_item(feed_id, feed_url, feed_title, el) for el in item_els]
    ttl_el = channel.find("ttl")
    min_interval = POLL_FLOOR_SECONDS
    if ttl_el is not None and ttl_el.text:
        try:
            min_interval = max(int(ttl_el.text) * 60, POLL_FLOOR_SECONDS)
        except ValueError:
            pass
    return items, PollConfig(min_interval_seconds=min_interval)


def _parse_item(feed_id: int, feed_url: str, feed_title: str | None, el) -> Item:
    guid = _text(el, "guid") or _text(el, "link") or ""
    if guid and not guid.startswith("http"):
        guid = f"{feed_url}#{guid}"
    url = _text(el, "link") or guid
    pub_date = _text(el, "pubDate") or _text_dc(el, "date")
    published = _parse_rss_date(pub_date) if pub_date else datetime.now(tz=timezone.utc)
    enclosure = el.find("enclosure")
    media_els = el.findall(f"{{{_MEDIA_NS}}}content")
    media = _parse_enclosure(enclosure) + [_parse_media_content(m) for m in media_els]
    media = [m for m in media if m is not None]
    thumb_el = el.find(f"{{{_MEDIA_NS}}}thumbnail")
    thumbnail = []
    if thumb_el is not None:
        w = thumb_el.get("width")
        h = thumb_el.get("height")
        thumb_url = thumb_el.get("url")
        if thumb_url:
            thumbnail = [
                Thumbnail(
                    url=thumb_url,
                    width=int(w) if w else None,
                    height=int(h) if h else None,
                )
            ]
    item_type = _infer_type(media)
    author_str = _text(el, "author") or _text_dc(el, "creator")
    authors = []
    if author_str:
        paren = re.search(r"\(([^)]+)\)", author_str)
        name = paren.group(1).strip() if paren else author_str.strip()
        if name:
            authors = [Author(name=name)]
    tags = [cat.text for cat in el.findall("category") if cat.text]
    return Item(
        feed_id=feed_id,
        item_id=guid or url,
        type=item_type,
        title=_text(el, "title") or "(untitled)",
        url=url,
        published=published,
        description=_text_content_encoded(el) or _text(el, "description"),
        authors=tuple(authors),
        tags=tuple(tags),
        media=tuple(media),
        thumbnail=tuple(thumbnail),
        source=ItemSource(type="rss", feed_url=feed_url, feed_title=feed_title),
    )


def _parse_enclosure(el) -> list[Media]:
    if el is None:
        return []
    url = el.get("url", "")
    mime = el.get("type", "")
    size = el.get("length")
    if not url or not url.startswith("https://"):
        return []
    return [
        Media(
            url=url,
            mime_type=mime,
            size_bytes=int(size) if size else None,
        )
    ]


def _parse_media_content(el) -> Media | None:
    url = el.get("url", "")
    if not url or not url.startswith("https://"):
        return None
    mime = el.get("type", "")
    dur = el.get("duration")
    return Media(
        url=url,
        mime_type=mime,
        duration=int(dur) if dur else None,
    )


def _infer_type(media: list[Media]) -> ItemType:
    for m in media:
        if m.mime_type.startswith("video/"):
            return ItemType.VIDEO
        if m.mime_type.startswith("audio/"):
            return ItemType.AUDIO
        if m.mime_type.startswith("image/"):
            return ItemType.IMAGE
    return ItemType.ARTICLE


def _text_content_encoded(el) -> str | None:
    child = el.find(f"{{{_CONTENT_NS}}}encoded")
    return child.text.strip() if child is not None and child.text else None


def _text(el, tag: str) -> str | None:
    child = el.find(tag)
    return child.text.strip() if child is not None and child.text else None


def _text_dc(el, local_name: str) -> str | None:
    child = el.find(f"{{{_DC_NS}}}{local_name}")
    return child.text.strip() if child is not None and child.text else None


def _parse_rss_date(value: str) -> datetime:
    try:
        return parsedate_to_datetime(value)
    except Exception:
        pass
    try:
        dt = datetime.fromisoformat(value)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return datetime.now(tz=timezone.utc)
