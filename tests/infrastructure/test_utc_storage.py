"""Every stored time comes back as the instant it went in, marked as UTC.

SQLite has no time zone type. SQLAlchemy's `DateTime(timezone=True)` wrote the
wall-clock digits and dropped the offset, then read them back with no zone at
all; `10:00+05:00` (05:00Z) and `06:00Z` returned as 10:00 and 06:00 and sorted
in the wrong order, while a filter bound written with an offset could not be
compared with them at all. Each test here goes through a real database file.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from meridian.application.interfaces.poll_state_repository import PollState
from meridian.application.services.item_service import ItemService
from meridian.domain.entities.feed import Feed
from meridian.domain.entities.item import Item
from meridian.domain.value_objects.item_type import ItemType
from meridian.domain.value_objects.source_type import SourceType
from meridian.infrastructure.db.session import build_session_factory
from meridian.infrastructure.repositories.sqlite_feed_repository import (
    SqliteFeedRepository,
)
from meridian.infrastructure.repositories.sqlite_item_repository import (
    SqliteItemRepository,
)
from meridian.infrastructure.repositories.sqlite_poll_state_repository import (
    SqlitePollStateRepository,
)

_PLUS_FIVE = timezone(timedelta(hours=5))
_SPEC_EXAMPLE_THREE = (
    'keyword:"climate" AND lang:en AND published:>=2026-01-01T00:00:00Z'
)


@pytest.fixture
def store(tmp_path):
    factory = build_session_factory(tmp_path / "utc.db")
    feeds = SqliteFeedRepository(factory)
    feed = feeds.save(Feed(url="https://f.example/rss", source_type=SourceType.RSS))
    yield factory, feeds, SqliteItemRepository(factory), feed
    factory.kw["bind"].dispose()


def _item(feed_id: int, name: str, published: datetime, **kwargs) -> Item:
    return Item(
        feed_id=feed_id,
        item_id=f"https://f.example/{name}",
        type=ItemType.ARTICLE,
        title=f"climate {name}",
        url=f"https://f.example/{name}",
        published=published,
        language="en",
        **kwargs,
    )


class TestItemTimes:
    def test_an_offset_time_comes_back_as_the_same_instant_in_utc(self, store):
        _, _, items, feed = store
        sent = datetime(2026, 1, 1, 10, 0, tzinfo=_PLUS_FIVE)
        items.save(_item(feed.id, "a", sent))

        [back] = items.list_by_feed(feed.id)

        assert back.published == sent
        assert back.published.tzinfo == timezone.utc
        assert back.published.hour == 5

    def test_every_optional_time_keeps_its_zone_too(self, store):
        _, _, items, feed = store
        when = datetime(2026, 2, 1, 9, 30, tzinfo=_PLUS_FIVE)
        items.save(
            _item(
                feed.id,
                "b",
                when,
                updated=when,
                scheduled_start=when,
                expires=when,
            )
        )

        [back] = items.list_by_feed(feed.id)

        for value in (back.updated, back.scheduled_start, back.expires):
            assert value == when and value.tzinfo == timezone.utc

    def test_newest_first_is_by_instant_not_by_wall_clock(self, store):
        _, _, items, feed = store
        earlier = _item(feed.id, "a", datetime(2026, 1, 1, 10, 0, tzinfo=_PLUS_FIVE))
        later = _item(feed.id, "b", datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc))
        items.save_many([earlier, later])

        assert [i.title for i in items.list_by_feed(feed.id)] == [
            "climate b",
            "climate a",
        ]

    def test_a_time_with_no_zone_is_taken_as_utc(self, store):
        _, _, items, feed = store
        items.save(_item(feed.id, "c", datetime(2026, 1, 1, 6, 0)))  # noqa: DTZ001

        [back] = items.list_by_feed(feed.id)

        assert back.published == datetime(2026, 1, 1, 6, 0, tzinfo=timezone.utc)

    def test_a_row_written_before_the_fix_is_read_as_utc(self, store):
        """Old rows hold bare digits; reading them must not break a filter."""
        factory, _, items, feed = store
        items.save(_item(feed.id, "d", datetime(2026, 1, 1, tzinfo=timezone.utc)))
        with factory() as session:
            session.execute(
                text("UPDATE items SET published = '2026-03-01 08:00:00.000000'")
            )
            session.commit()

        [back] = items.list_by_feed(feed.id)

        assert back.published == datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc)

    def test_read_state_times_keep_their_zone(self, store):
        factory, _, items, feed = store
        saved = items.save(_item(feed.id, "e", datetime(2026, 1, 1, tzinfo=_PLUS_FIVE)))
        read_at = datetime(2026, 1, 2, 12, 0, tzinfo=_PLUS_FIVE)
        items.mark_read(saved.id, read_at)

        with factory() as session:
            stored = session.execute(text("SELECT read_at FROM items")).scalar_one()

        assert stored.startswith("2026-01-02 07:00:00")


class TestPollStateTimes:
    def test_poll_times_come_back_as_utc_instants(self, store):
        factory, _, _, feed = store
        states = SqlitePollStateRepository(factory)
        when = datetime(2026, 1, 1, 10, 0, tzinfo=_PLUS_FIVE)
        states.save(
            PollState(
                feed_id=feed.id, last_polled=when, next_poll=when, backoff_until=when
            )
        )

        back = states.get(feed.id)

        for value in (back.last_polled, back.next_poll, back.backoff_until):
            assert value == when and value.tzinfo == timezone.utc

    def test_an_unset_time_stays_unset(self, store):
        factory, _, _, feed = store
        states = SqlitePollStateRepository(factory)
        states.save(PollState(feed_id=feed.id))

        assert states.get(feed.id).next_poll is None


class TestTheSpecificationsExampleOnStoredItems:
    """MMSP Appendix A.2 example 3 against items read back from the store."""

    def test_the_example_filter_shows_the_items_it_describes(self, store):
        _, feeds, items, feed = store
        items.save_many(
            [
                _item(feed.id, "new", datetime(2026, 1, 1, 10, 0, tzinfo=_PLUS_FIVE)),
                _item(feed.id, "old", datetime(2025, 12, 31, 18, 0, tzinfo=_PLUS_FIVE)),
            ]
        )
        feeds.update_filter(feed.id, _SPEC_EXAMPLE_THREE)

        shown = ItemService(items, feeds).get_items(feed.id)

        assert [i.title for i in shown] == ["climate new"]
        assert shown[0].published_iso == "2026-01-01T05:00:00+00:00"
