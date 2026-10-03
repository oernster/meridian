"""Parser for Atom 1.0 feeds (Appendix C normalization)."""

from __future__ import annotations

from datetime import datetime, timezone

import defusedxml.ElementTree as ET

from meridian.domain.entities.item import Item
from meridian.domain.value_objects.item_type import ItemType
from meridian.domain.value_objects.media import Author, ItemSource, Media, Thumbnail
from meridian.domain.value_objects.poll_config import PollConfig, POLL_FLOOR_SECONDS
from meridian.infrastructure.fetching.parser.https_only import is_https

_ATOM_NS = "http://www.w3.org/2005/Atom"
_MEDIA_NS = "http://search.yahoo.com/mrss/"


def parse(
    feed_id: int, feed_url: str, raw_bytes: bytes
) -> tuple[list[Item], PollConfig]:
    root = ET.fromstring(raw_bytes)
    ns = _detect_ns(root)
    feed_title_el = root.find(f"{ns}title")
    feed_title = feed_title_el.text if feed_title_el is not None else None
    entries = root.findall(f"{ns}entry")
    items = [_parse_entry(feed_id, feed_url, feed_title, ns, e) for e in entries]
    return items, PollConfig(min_interval_seconds=POLL_FLOOR_SECONDS)


def _thumbnail(thumb_el) -> list[Thumbnail]:
    """The entry's thumbnail; none when it is absent or not HTTPS."""
    if thumb_el is None or not is_https(thumb_el.get("url")):
        return []
    width = thumb_el.get("width")
    height = thumb_el.get("height")
    return [
        Thumbnail(
            url=thumb_el.get("url"),
            width=int(width) if width else None,
            height=int(height) if height else None,
        )
    ]


def _detect_ns(root) -> str:
    tag = root.tag
    if tag.startswith("{"):
        return tag[: tag.index("}") + 1]
    return ""


def _parse_entry(
    feed_id: int, feed_url: str, feed_title: str | None, ns: str, el
) -> Item:
    item_id = _text(el, f"{ns}id") or ""
    title_el = el.find(f"{ns}title")
    title = title_el.text if title_el is not None and title_el.text else "(untitled)"
    url = _find_link(el, ns, "alternate") or item_id
    published_el = el.find(f"{ns}published")
    updated_el = el.find(f"{ns}updated")
    published = (
        _parse_dt(published_el.text)
        if published_el is not None and published_el.text
        else datetime.now(tz=timezone.utc)
    )
    updated = (
        _parse_dt(updated_el.text)
        if updated_el is not None and updated_el.text
        else None
    )
    content_el = el.find(f"{ns}content")
    summary_el = el.find(f"{ns}summary")
    desc_el = content_el if content_el is not None else summary_el
    description = desc_el.text if desc_el is not None else None
    authors = []
    for author_el in el.findall(f"{ns}author"):
        name_el = author_el.find(f"{ns}name")
        url_el = author_el.find(f"{ns}uri")
        if name_el is not None and name_el.text:
            authors.append(
                Author(
                    name=name_el.text,
                    url=url_el.text if url_el is not None else None,
                )
            )
    tags = []
    for cat_el in el.findall(f"{ns}category"):
        term = cat_el.get("term")
        if term:
            tags.append(term)
    media = []
    for link_el in el.findall(f"{ns}link"):
        if link_el.get("rel") == "enclosure":
            enc_url = link_el.get("href", "")
            if is_https(enc_url):
                enc_type = link_el.get("type", "")
                length = link_el.get("length")
                enc_size = int(length) if length else None
                media = [Media(url=enc_url, mime_type=enc_type, size_bytes=enc_size)]
            break
    # media:group (YouTube Atom): contains thumbnail, content and description
    group_el = el.find(f"{{{_MEDIA_NS}}}group")
    if group_el is not None:
        thumbnail = _thumbnail(group_el.find(f"{{{_MEDIA_NS}}}thumbnail"))
        content_el = group_el.find(f"{{{_MEDIA_NS}}}content")
        desc_el = group_el.find(f"{{{_MEDIA_NS}}}description")
        if desc_el is not None and desc_el.text and description is None:
            description = desc_el.text.strip()
        if content_el is not None and not media:
            content_url = content_el.get("url", "")
            content_type = content_el.get("type", "")
            if "youtube.com" not in content_url and is_https(content_url):
                media = [Media(url=content_url, mime_type=content_type)]
    else:
        thumbnail = _thumbnail(el.find(f"{{{_MEDIA_NS}}}thumbnail"))
    item_type = _infer_type(media, feed_url)
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


def _infer_type(media: list[Media], feed_url: str = "") -> ItemType:
    if "youtube.com" in feed_url:
        return ItemType.VIDEO
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
