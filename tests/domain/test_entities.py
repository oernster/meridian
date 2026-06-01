import pytest

from meridian.domain.entities.feed import Feed, UNSET_ID
from meridian.domain.entities.item import Item
from meridian.domain.value_objects.item_type import ItemType
from meridian.domain.value_objects.media import Author, ContentRating, Media, Thumbnail
from meridian.domain.value_objects.poll_config import PollConfig, POLL_FLOOR_SECONDS
from meridian.domain.value_objects.source_type import SourceType
from meridian.domain.value_objects.filter_expression import FilterExpression
from datetime import datetime, timezone


def _make_feed(**kwargs) -> Feed:
    defaults = dict(url="https://example.com/feed", source_type=SourceType.MFEED)
    return Feed(**{**defaults, **kwargs})


def _make_item(**kwargs) -> Item:
    defaults = dict(
        item_id="https://example.com/item/1",
        type=ItemType.ARTICLE,
        title="Test Item",
        url="https://example.com/item/1",
        published=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    return Item(**{**defaults, **kwargs})


class TestFeed:
    def test_valid_creation(self):
        feed = _make_feed()
        assert feed.url == "https://example.com/feed"
        assert feed.source_type == SourceType.MFEED
        assert feed.id == UNSET_ID

    def test_rejects_http_url(self):
        with pytest.raises(ValueError, match="HTTPS"):
            Feed(url="http://example.com/feed", source_type=SourceType.RSS)

    def test_platform_requires_platform_id(self):
        with pytest.raises(ValueError, match="platform_id"):
            Feed(url="https://example.com/feed", source_type=SourceType.PLATFORM)

    def test_platform_with_id(self):
        feed = Feed(
            url="https://example.com/feed",
            source_type=SourceType.PLATFORM,
            platform_id="my-platform",
        )
        assert feed.platform_id == "my-platform"

    def test_is_saved(self):
        unsaved = _make_feed()
        assert not unsaved.is_saved()
        saved = _make_feed(id=1)
        assert saved.is_saved()

    def test_with_metadata(self):
        feed = _make_feed(id=5)
        updated = feed.with_metadata(title="My Feed", language="en")
        assert updated.title == "My Feed"
        assert updated.language == "en"
        assert updated.id == 5
        assert updated.url == feed.url

    def test_frozen(self):
        feed = _make_feed()
        with pytest.raises((AttributeError, TypeError)):
            feed.url = "https://other.com"  # type: ignore


class TestItem:
    def test_valid_creation(self):
        item = _make_item()
        assert item.title == "Test Item"
        assert item.type == ItemType.ARTICLE

    def test_primary_thumbnail_url_empty(self):
        item = _make_item()
        assert item.primary_thumbnail_url() is None

    def test_primary_thumbnail_url_present(self):
        item = _make_item(thumbnail=(Thumbnail(url="https://example.com/thumb.jpg"),))
        assert item.primary_thumbnail_url() == "https://example.com/thumb.jpg"

    def test_primary_media_url_none(self):
        item = _make_item()
        assert item.primary_media_url() is None

    def test_primary_media_url_present(self):
        item = _make_item(media=(Media(url="https://example.com/video.mp4", mime_type="video/mp4"),))
        assert item.primary_media_url() == "https://example.com/video.mp4"

    def test_is_media_type_video(self):
        item = _make_item(type=ItemType.VIDEO)
        assert item.is_media_type()

    def test_is_media_type_article(self):
        item = _make_item(type=ItemType.ARTICLE)
        assert not item.is_media_type()

    def test_frozen(self):
        item = _make_item()
        with pytest.raises((AttributeError, TypeError)):
            item.title = "Changed"  # type: ignore


class TestPollConfig:
    def test_default_floor(self):
        config = PollConfig()
        assert config.min_interval_seconds == POLL_FLOOR_SECONDS

    def test_floor_enforced_on_low_value(self):
        config = PollConfig(min_interval_seconds=10)
        assert config.min_interval_seconds == POLL_FLOOR_SECONDS

    def test_higher_value_preserved(self):
        config = PollConfig(min_interval_seconds=600)
        assert config.min_interval_seconds == 600

    def test_effective_interval(self):
        config = PollConfig(min_interval_seconds=900)
        assert config.effective_interval == 900


class TestItemType:
    def test_from_str_known(self):
        assert ItemType.from_str("video") == ItemType.VIDEO

    def test_from_str_unknown_falls_back_to_article(self):
        assert ItemType.from_str("unknown_future_type") == ItemType.ARTICLE


class TestFilterExpression:
    def test_valid(self):
        fe = FilterExpression("type:video")
        assert fe.expr == "type:video"

    def test_strips_whitespace(self):
        fe = FilterExpression("  type:video  ")
        assert fe.expr == "type:video"

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            FilterExpression("")

    def test_whitespace_only_raises(self):
        with pytest.raises(ValueError):
            FilterExpression("   ")

    def test_non_string_raises(self):
        with pytest.raises(TypeError):
            FilterExpression(123)  # type: ignore

    def test_bool_true(self):
        assert bool(FilterExpression("type:video"))
