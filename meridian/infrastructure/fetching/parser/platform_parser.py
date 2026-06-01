"""Parser for platform source type. Falls back to RSS if no adapter registered."""

from __future__ import annotations

from meridian.domain.entities.item import Item
from meridian.domain.value_objects.poll_config import PollConfig
from meridian.infrastructure.fetching.parser import rss_parser

_ADAPTERS: dict[str, object] = {}


def register_adapter(platform_id: str, adapter) -> None:
    """Register a platform-specific adapter. Adapter must implement parse()."""
    _ADAPTERS[platform_id] = adapter


def parse(
    feed_id: int,
    feed_url: str,
    raw_bytes: bytes,
    platform_id: str | None = None,
    rss_fallback_url: str | None = None,
) -> tuple[list[Item], PollConfig]:
    if platform_id and platform_id in _ADAPTERS:
        adapter = _ADAPTERS[platform_id]
        return adapter.parse(feed_id, feed_url, raw_bytes)
    return rss_parser.parse(feed_id, rss_fallback_url or feed_url, raw_bytes)
