"""Parser for Atom 1.0 feeds (Appendix C normalization)."""
from __future__ import annotations

from datetime import datetime, timezone

import defusedxml.ElementTree as ET

from meridian.domain.entities.item import Item
from meridian.domain.value_objects.item_type import ItemType
from meridian.domain.value_objects.media import Author, ItemSource, Media, Thumbnail
from meridian.domain.value_objects.poll_config import PollConfig, POLL_FLOOR_SECONDS

_ATOM_NS = "http://www.w3.org/2005/Atom"
_MEDIA_NS = "http://search.yahoo.com/mrss/"


def parse(feed_id: int, feed_url: str, raw_bytes: bytes) -> tuple[list[Item], PollConfig]:
    root = ET.fromstring(raw_bytes)
    ns = _detect_ns(root)
    feed_title_el = root.find(f"{ns}title")
    feed_title = feed_title_el.text if feed_title_el is not None else None
    entries = root.findall(f"{ns}entry")
    items = [_parse_entry(feed_id, feed_url, feed_title, ns, e) for e in entries]
    return items, PollConfig(min_interval_seconds=POLL_FLOOR_SECONDS)


def _detect_ns(root) -> str:
    tag = root.tag
    if tag.startswith("{"):
        return tag[:tag.index("}") + 1]
    return ""


def _parse_entry(feed_id: int, feed_url: str, feed_title: str | None, ns: str, el) -> Item:
    item_id = _text(el, f"{ns}id") or ""
    title_el = el.find(f"{ns}title")
    title = title_el.text if title_el is not None and title_el.text else "(untitled)"
    url = _find_link(el, ns, "alternate") or item_id
    published_el = el.find(f"{ns}published")
    updated_el = el.find(f"{ns}updated")
    published = _parse_dt(published_el.text) if published_el is not None and published_el.text else datetime.now(tz=timezone.utc)
    updated = _parse_dt(updated_el.text) if updated_el is not None and updated_el.text else None
    content_el = el.find(f"{ns}content")
    summary_el = el.find(f"{ns}summary")
    desc_el = content_el if content_el is not None else summary_el
    description = desc_el.text if desc_el is not None else None
    authors = []
    for author_el in el.findall(f"{ns}author"):
        name_el = author_el.find(f"{ns}name")
        url_el = author_el.find(f"{ns}uri")
        if name_el is not None and name_el.text:
            authors.append(Author(
                name=name_el.text,
                url=url_el.text if url_el is not None else None,
            ))
    tags = []
    for cat_el in el.findall(f"{ns}category"):
        term = cat_el.get("term")
        if term:
            tags.append(term)
    media = []
    for link_el in el.findall(f"{ns}link"):
        if link_el.get("rel") == "enclosure":
            enc_url = link_el.get("href", "")
            if enc_url.startswith("https://"):
                enc_type = link_el.get("type", "")
                length = link_el.get("length")
                enc_size = int(length) if length else None
                media = [Media(url=enc_url, mime_type=enc_type, size_bytes=enc_size)]
            break
    item_type = _infer_type(media)
    thumbnail = []
    thumb_el = el.find(f"{{{_MEDIA_NS}}}thumbnail")
    if thumb_el is not None:
        thumb_url = thumb_el.get("url")
        if thumb_url:
            thumbnail = [Thumbnail(
                url=thumb_url,
                width=int(thumb_el.get("width")) if thumb_el.get("width") else None,
                height=int(thumb_el.get("height")) if thumb_el.get("height") else None,
            )]
    return Item(
        feed_id=feed_id,
        item_id=item_id or url,
        type=item_type,
        title=title,
        url=url,
        published=published,
        updated=updated,
        description=description,
        authors=tuple(authors),
        tags=tuple(tags),
        media=tuple(media),
        thumbnail=tuple(thumbnail),
        source=ItemSource(type="atom", feed_url=feed_url, feed_title=feed_title),
    )


def _find_link(el, ns: str, rel: str) -> str | None:
    for link_el in el.findall(f"{ns}link"):
        if link_el.get("rel") == rel:
            return link_el.get("href")
    return None


def _infer_type(media: list[Media]) -> ItemType:
    for m in media:
        if m.mime_type.startswith("video/"):
            return ItemType.VIDEO
        if m.mime_type.startswith("audio/"):
            return ItemType.AUDIO
        if m.mime_type.startswith("image/"):
            return ItemType.IMAGE
    return ItemType.ARTICLE


def _text(el, tag: str) -> str | None:
    child = el.find(tag)
    return child.text.strip() if child is not None and child.text else None


def _parse_dt(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
