"""SubscriptionService against a real SQLite store: what it refuses, what it counts.

A subscribe used to commit and then read the feed's unread count, so a read
failing after the commit reported a stored feed as refused (measured under an
injected "database is locked"). A filter was stored whatever it said, so a
malformed one only failed later, when the feed was opened.
"""

import sqlite3

import pytest

from meridian.application.services.feed_import import import_feeds
from meridian.application.services.filter_rules import filter_terms
from meridian.application.services.subscription_service import SubscriptionService
from meridian.domain.value_objects.filter_expression import FilterSyntaxError
from meridian.infrastructure.db.session import build_session_factory
from meridian.infrastructure.repositories.sqlite_feed_repository import (
    SqliteFeedRepository,
)
from meridian.infrastructure.repositories.sqlite_item_repository import (
    SqliteItemRepository,
)


class LockedAfterCommit(SqliteItemRepository):
    """Every read of an unread count fails, as a locked database would."""

    def unread_count(self, feed_id):
        raise sqlite3.OperationalError("database is locked")


@pytest.fixture
def factory(tmp_path):
    made = build_session_factory(tmp_path / "rules.db")
    yield made
    made.kw["bind"].dispose()


def _service(factory, items=SqliteItemRepository):
    return SubscriptionService(SqliteFeedRepository(factory), items(factory))


class TestAddedIsCountedFromTheSave:
    def test_a_read_failing_after_the_commit_does_not_unsay_the_save(self, factory):
        locked = _service(factory, LockedAfterCommit)
        report = import_feeds(
            {"feeds": [{"url": f"https://q{n}.example/rss"} for n in range(3)]},
            locked,
        )
        assert (report.added, report.skipped) == (3, ())
        assert len(_service(factory).list_feeds()) == 3

    def test_a_new_feed_has_nothing_unread(self, factory):
        dto = _service(factory, LockedAfterCommit).subscribe("https://a.example/rss")
        assert dto.unread_count == 0 and dto.id > 0


class TestFilters:
    def test_an_invalid_filter_is_refused_and_the_old_one_kept(self, factory):
        service = _service(factory)
        feed = service.subscribe("https://a.example/rss")
        service.set_filter(feed.id, "lang:en")
        with pytest.raises(FilterSyntaxError, match="after a complete"):
            service.set_filter(feed.id, "type:video type:audio")
        assert service.get_feed(feed.id).filter_expr == "lang:en"

    def test_a_valid_filter_is_stored_and_none_clears_it(self, factory):
        service = _service(factory)
        feed = service.subscribe("https://a.example/rss")
        service.set_filter(feed.id, "published:>=2026-01-01")
        assert service.get_feed(feed.id).filter_expr == "published:>=2026-01-01"
        service.set_filter(feed.id, None)
        assert service.get_feed(feed.id).filter_expr is None

    def test_a_feed_subscribed_with_a_filter_keeps_it(self, factory):
        service = _service(factory)
        feed = service.subscribe("https://a.example/rss", filter_expr="lang:en")
        assert service.get_feed(feed.id).filter_expr == "lang:en"


class TestFilterTerms:
    def test_quoted_and_is_not_a_split(self):
        assert filter_terms('keyword:"a AND b" AND lang:en') == [
            'keyword:"a AND b"',
            "lang:en",
        ]

    def test_an_unreadable_filter_is_one_term_so_it_can_still_be_edited(self):
        assert filter_terms(" type:video type:audio ") == ["type:video type:audio"]

    def test_no_filter_is_no_terms(self):
        assert filter_terms("   ") == []


class TestAddresses:
    @pytest.mark.parametrize("url", ["https://", "https://not a url at all"])
    def test_an_address_with_no_host_is_never_stored(self, factory, url):
        service = _service(factory)
        with pytest.raises(ValueError):
            service.subscribe(url)
        assert service.list_feeds() == []

    def test_a_feed_cannot_be_repointed_at_a_bad_address(self, factory):
        """It used to be written straight to the row, unchecked."""
        service = _service(factory)
        feed = service.subscribe("https://a.example/rss")
        with pytest.raises(ValueError, match="must use http"):
            service.update_url(feed.id, "ftp://a.example/rss")
        assert service.get_feed(feed.id).url == "https://a.example/rss"
