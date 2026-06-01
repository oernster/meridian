import json
from datetime import datetime, timezone

import pytest

from meridian.infrastructure.fetching.parser import mfeed_parser
from meridian.domain.value_objects.item_type import ItemType

_MINIMAL_FEED = {
    "mmsp": "1.0",
    "id": "https://example.com/feed",
    "title": "Test Feed",
    "feed_url": "https://example.com/feed",
    "items": [
        {
            "id": "https://example.com/item/1",
            "type": "video",
            "title": "Test Video",
            "url": "https://example.com/item/1",
            "published": "2026-01-01T00:00:00Z",
        }
    ],
}

_RICH_ITEM = {
    "id": "https://example.com/item/2",
    "type": "audio",
    "title": "Podcast Episode",
    "url": "https://example.com/item/2",
    "published": "2026-03-01T12:00:00Z",
    "updated": "2026-03-02T00:00:00Z",
    "description": "An episode",
    "language": "en",
    "duration": 3600,
    "canonical_url": "https://canonical.example.com/item/2",
    "preview_url": "https://example.com/preview.mp4",
    "license": "CC-BY-4.0",
    "authors": [{"name": "Alice", "url": "https://alice.example.com"}],
    "tags": ["tech", "python"],
    "media": [{"url": "https://example.com/audio.mp3", "mime_type": "audio/mpeg", "role": "primary"}],
    "thumbnail": [{"url": "https://example.com/thumb.jpg", "width": 400, "height": 300}],
    "series": {"id": "https://example.com/series", "title": "Tech Talks", "episode_number": 5},
    "content_rating": {"rating": "general", "descriptors": ["mild_language"]},
    "paywall": {"paywalled": False},
    "geo_restriction": {"type": "allowlist", "regions": ["GB", "DE"]},
    "transcript": {"url": "https://example.com/transcript.txt", "mime_type": "text/plain", "language": "en"},
    "captions": [{"url": "https://example.com/captions.vtt", "mime_type": "text/vtt", "language": "en"}],
    "chapters": [{"title": "Intro", "start_seconds": 0, "end_seconds": 120}],
}


def _raw(feed: dict) -> bytes:
    return json.dumps(feed).encode()


class TestMfeedParser:
    def test_minimal_feed(self):
        items, config = mfeed_parser.parse(1, "https://example.com/feed", _raw(_MINIMAL_FEED))
        assert len(items) == 1
        assert items[0].type == ItemType.VIDEO
        assert items[0].title == "Test Video"

    def test_poll_config_default(self):
        _, config = mfeed_parser.parse(1, "https://example.com/feed", _raw(_MINIMAL_FEED))
        assert config.min_interval_seconds == 300

    def test_poll_config_custom(self):
        feed = {**_MINIMAL_FEED, "poll": {"min_interval_seconds": 900}}
        _, config = mfeed_parser.parse(1, "https://example.com/feed", _raw(feed))
        assert config.min_interval_seconds == 900

    def test_poll_config_floor_enforced(self):
        feed = {**_MINIMAL_FEED, "poll": {"min_interval_seconds": 10}}
        _, config = mfeed_parser.parse(1, "https://example.com/feed", _raw(feed))
        assert config.min_interval_seconds == 300

    def test_rich_item(self):
        feed = {**_MINIMAL_FEED, "items": [_RICH_ITEM]}
        items, _ = mfeed_parser.parse(1, "https://example.com/feed", _raw(feed))
        item = items[0]
        assert item.type == ItemType.AUDIO
        assert item.duration == 3600
        assert item.language == "en"
        assert len(item.authors) == 1
        assert item.authors[0].name == "Alice"
        assert item.tags == ("tech", "python")
        assert len(item.media) == 1
        assert len(item.thumbnail) == 1
        assert item.series is not None
        assert item.series.episode_number == 5
        assert item.content_rating is not None
        assert item.content_rating.descriptors == ("mild_language",)
        assert item.paywall is not None
        assert not item.paywall.paywalled
        assert item.geo_restriction is not None
        assert item.geo_restriction.regions == ("GB", "DE")
        assert item.transcript is not None
        assert len(item.captions) == 1
        assert len(item.chapters) == 1

    def test_unknown_type_normalizes_to_article(self):
        feed = {
            **_MINIMAL_FEED,
            "items": [{**_MINIMAL_FEED["items"][0], "type": "future_unknown_type"}],
        }
        items, _ = mfeed_parser.parse(1, "https://example.com/feed", _raw(feed))
        assert items[0].type == ItemType.ARTICLE

    def test_source_field_set(self):
        items, _ = mfeed_parser.parse(1, "https://example.com/feed", _raw(_MINIMAL_FEED))
        assert items[0].source is not None
        assert items[0].source.type == "mfeed"

    def test_empty_items(self):
        feed = {**_MINIMAL_FEED, "items": []}
        items, _ = mfeed_parser.parse(1, "https://example.com/feed", _raw(feed))
        assert items == []

    def test_datetime_no_timezone(self):
        from meridian.infrastructure.fetching.parser.mfeed_parser import _parse_dt
        from datetime import timezone
        dt = _parse_dt("2026-01-01T00:00:00")
        assert dt.tzinfo == timezone.utc

    def test_poll_config_with_recommended(self):
        feed = {**_MINIMAL_FEED, "poll": {"min_interval_seconds": 600, "recommended_interval_seconds": 900, "ttl_seconds": 3600}}
        _, config = mfeed_parser.parse(1, "https://example.com/feed", _raw(feed))
        assert config.recommended_interval_seconds == 900
        assert config.ttl_seconds == 3600
