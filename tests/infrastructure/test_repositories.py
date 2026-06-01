from datetime import datetime, timezone

import pytest
from meridian.domain.entities.feed import Feed
from meridian.domain.entities.item import Item
from meridian.domain.value_objects.item_type import ItemType
from meridian.domain.value_objects.media import (
    Author,
    ContentRating,
    Media,
    Series,
    Thumbnail,
)
from meridian.domain.value_objects.source_type import SourceType
from meridian.infrastructure.repositories.sqlite_feed_repository import (
    SqliteFeedRepository,
)
from meridian.infrastructure.repositories.sqlite_item_repository import (
    SqliteItemRepository,
)
from meridian.infrastructure.repositories.sqlite_poll_state_repository import (
    SqlitePollStateRepository,
)
from meridian.application.interfaces.poll_state_repository import PollState


def _feed(**kwargs) -> Feed:
    defaults = dict(url="https://example.com/feed", source_type=SourceType.MFEED)
    return Feed(**{**defaults, **kwargs})


def _item(feed_id: int, item_id: str = "https://example.com/item/1") -> Item:
    return Item(
        feed_id=feed_id,
        item_id=item_id,
        type=ItemType.VIDEO,
        title="Test Video",
        url="https://example.com/item/1",
        published=datetime(2026, 1, 1, tzinfo=timezone.utc),
        duration=600,
        authors=(Author(name="Alice", url="https://example.com/alice"),),
        tags=("tech", "python"),
        media=(
            Media(
                url="https://example.com/video.mp4",
                mime_type="video/mp4",
                role="primary",
            ),
        ),
        thumbnail=(
            Thumbnail(url="https://example.com/thumb.jpg", width=320, height=180),
        ),
        series=Series(
            id="https://example.com/series", title="My Series", episode_number=1
        ),
        content_rating=ContentRating(rating="general"),
    )


class TestSqliteFeedRepository:
    def test_save_and_get(self, session_factory):
        repo = SqliteFeedRepository(session_factory)
        saved = repo.save(_feed())
        assert saved.id > 0
        fetched = repo.get_by_id(saved.id)
        assert fetched is not None
        assert fetched.url == saved.url

    def test_get_by_url(self, session_factory):
        repo = SqliteFeedRepository(session_factory)
        saved = repo.save(_feed(url="https://unique-feed.example.com/feed"))
        result = repo.get_by_url(saved.url)
        assert result is not None
        assert result.id == saved.id

    def test_get_by_url_not_found(self, session_factory):
        repo = SqliteFeedRepository(session_factory)
        assert repo.get_by_url("https://nonexistent.example.com/") is None

    def test_list_all(self, session_factory):
        repo = SqliteFeedRepository(session_factory)
        before = len(repo.list_all())
        repo.save(_feed(url="https://list-test-a.example.com/feed"))
        repo.save(_feed(url="https://list-test-b.example.com/feed"))
        assert len(repo.list_all()) >= before + 2

    def test_delete(self, session_factory):
        repo = SqliteFeedRepository(session_factory)
        saved = repo.save(_feed(url="https://delete-test.example.com/feed"))
        repo.delete(saved.id)
        assert repo.get_by_id(saved.id) is None

    def test_delete_nonexistent_noop(self, session_factory):
        repo = SqliteFeedRepository(session_factory)
        repo.delete(99999)

    def test_update_filter(self, session_factory):
        repo = SqliteFeedRepository(session_factory)
        saved = repo.save(_feed(url="https://filter-test.example.com/feed"))
        repo.update_filter(saved.id, "type:video")
        fetched = repo.get_by_id(saved.id)
        assert fetched.filter_expr == "type:video"

    def test_update_filter_clear(self, session_factory):
        repo = SqliteFeedRepository(session_factory)
        saved = repo.save(_feed(url="https://filter-clear.example.com/feed"))
        repo.update_filter(saved.id, "type:video")
        repo.update_filter(saved.id, None)
        fetched = repo.get_by_id(saved.id)
        assert fetched.filter_expr is None

    def test_update_filter_nonexistent_noop(self, session_factory):
        repo = SqliteFeedRepository(session_factory)
        repo.update_filter(99999, "type:video")

    def test_save_existing_raises_if_not_found(self, session_factory):
        repo = SqliteFeedRepository(session_factory)
        phantom = Feed(
            id=99998,
            url="https://phantom.example.com/feed",
            source_type=SourceType.MFEED,
        )
        with pytest.raises(ValueError, match="not found"):
            repo.save(phantom)

    def test_save_updates_existing(self, session_factory):
        repo = SqliteFeedRepository(session_factory)
        saved = repo.save(_feed(url="https://update-test.example.com/feed"))
        updated = saved.with_metadata(title="Updated Title", language="fr")
        result = repo.save(updated)
        assert result.title == "Updated Title"
        assert result.language == "fr"

    def test_update_title(self, session_factory):
        repo = SqliteFeedRepository(session_factory)
        saved = repo.save(_feed(url="https://title-test.example.com/feed"))
        repo.update_title(saved.id, "Auto Discovered Title")
        fetched = repo.get_by_id(saved.id)
        assert fetched.title == "Auto Discovered Title"

    def test_update_title_nonexistent_noop(self, session_factory):
        repo = SqliteFeedRepository(session_factory)
        repo.update_title(99997, "Ghost Title")


class TestSqliteItemRepository:
    def _setup_feed(self, session_factory) -> Feed:
        from meridian.infrastructure.repositories.sqlite_feed_repository import (
            SqliteFeedRepository,
        )

        feed_repo = SqliteFeedRepository(session_factory)
        return feed_repo.save(
            _feed(url=f"https://items-test-{id(self)}.example.com/feed")
        )

    def test_save_and_get(self, session_factory):
        feed = self._setup_feed(session_factory)
        repo = SqliteItemRepository(session_factory)
        saved = repo.save(_item(feed.id))
        assert saved.id > 0
        fetched = repo.get_by_id(saved.id)
        assert fetched is not None
        assert fetched.item_id == saved.item_id

    def test_list_by_feed(self, session_factory):
        feed = self._setup_feed(session_factory)
        repo = SqliteItemRepository(session_factory)
        repo.save(_item(feed.id, "https://example.com/item/a"))
        repo.save(_item(feed.id, "https://example.com/item/b"))
        items = repo.list_by_feed(feed.id)
        assert len(items) == 2

    def test_mark_read(self, session_factory):
        feed = self._setup_feed(session_factory)
        repo = SqliteItemRepository(session_factory)
        saved = repo.save(_item(feed.id, "https://example.com/item/read-test"))
        assert not saved.is_read
        repo.mark_read(saved.id, datetime.now(tz=timezone.utc))
        fetched = repo.get_by_id(saved.id)
        assert fetched.is_read

    def test_mark_all_read(self, session_factory):
        feed = self._setup_feed(session_factory)
        repo = SqliteItemRepository(session_factory)
        repo.save(_item(feed.id, "https://example.com/item/all-read-a"))
        repo.save(_item(feed.id, "https://example.com/item/all-read-b"))
        repo.mark_all_read(feed.id, datetime.now(tz=timezone.utc))
        items = repo.list_by_feed(feed.id)
        assert all(i.is_read for i in items)

    def test_unread_count(self, session_factory):
        feed = self._setup_feed(session_factory)
        repo = SqliteItemRepository(session_factory)
        repo.save(_item(feed.id, "https://example.com/item/unread-a"))
        repo.save(_item(feed.id, "https://example.com/item/unread-b"))
        count = repo.unread_count(feed.id)
        assert count >= 2

    def test_exists_true(self, session_factory):
        feed = self._setup_feed(session_factory)
        repo = SqliteItemRepository(session_factory)
        item = _item(feed.id, "https://example.com/item/exists-test")
        repo.save(item)
        assert repo.exists(feed.id, "https://example.com/item/exists-test")

    def test_exists_false(self, session_factory):
        feed = self._setup_feed(session_factory)
        repo = SqliteItemRepository(session_factory)
        assert not repo.exists(feed.id, "https://example.com/item/nonexistent")

    def test_save_many(self, session_factory):
        feed = self._setup_feed(session_factory)
        repo = SqliteItemRepository(session_factory)
        items = [
            _item(feed.id, "https://example.com/item/many-a"),
            _item(feed.id, "https://example.com/item/many-b"),
        ]
        saved = repo.save_many(items)
        assert len(saved) == 2

    def test_get_by_id_not_found(self, session_factory):
        repo = SqliteItemRepository(session_factory)
        assert repo.get_by_id(99999) is None

    def test_mark_read_nonexistent_noop(self, session_factory):
        repo = SqliteItemRepository(session_factory)
        repo.mark_read(99999, datetime.now(tz=timezone.utc))

    def test_rich_fields_roundtrip(self, session_factory):
        feed = self._setup_feed(session_factory)
        repo = SqliteItemRepository(session_factory)
        saved = repo.save(_item(feed.id, "https://example.com/item/rich"))
        fetched = repo.get_by_id(saved.id)
        assert fetched.duration == 600
        assert len(fetched.authors) == 1
        assert fetched.authors[0].name == "Alice"
        assert fetched.tags == ("tech", "python")
        assert fetched.series is not None
        assert fetched.series.episode_number == 1


class TestSqlitePollStateRepository:
    def test_get_missing_returns_empty(self, session_factory):
        repo = SqlitePollStateRepository(session_factory)
        state = repo.get(99999)
        assert state.feed_id == 99999
        assert state.last_polled is None

    def test_save_and_get(self, session_factory):
        feed_repo = SqliteFeedRepository(session_factory)
        feed = feed_repo.save(_feed(url="https://poll-state-test.example.com/feed"))
        repo = SqlitePollStateRepository(session_factory)
        now = datetime.now(tz=timezone.utc)
        state = PollState(
            feed_id=feed.id,
            last_polled=now,
            etag='"abc123"',
            deprecated=False,
        )
        repo.save(state)
        fetched = repo.get(feed.id)
        assert fetched.etag == '"abc123"'
        assert fetched.last_polled is not None

    def test_update_existing(self, session_factory):
        feed_repo = SqliteFeedRepository(session_factory)
        feed = feed_repo.save(_feed(url="https://poll-state-update.example.com/feed"))
        repo = SqlitePollStateRepository(session_factory)
        repo.save(PollState(feed_id=feed.id, etag='"first"'))
        repo.save(PollState(feed_id=feed.id, etag='"second"'))
        fetched = repo.get(feed.id)
        assert fetched.etag == '"second"'
