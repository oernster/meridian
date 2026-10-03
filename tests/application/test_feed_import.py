"""Importing a feed list: every entry is added, already held or named as refused.

The import used to log a refusal and say nothing, so these tests hold the
report to the whole file: nothing in it may go unaccounted for.
"""

import pytest

from meridian.application.dto.feed_dto import FeedDTO
from meridian.application.services.feed_import import (
    NAMED_SKIP_LIMIT,
    ImportReport,
    NotAFeedList,
    SkippedEntry,
    import_feeds,
)


def _dto(url: str) -> FeedDTO:
    return FeedDTO(1, url, "rss", None, None, None, None, None, 0)


class FakeSubscriptions:
    """Holds feeds by address; refuses any address listed in `refuse`."""

    def __init__(self, held=(), refuse=None):
        self.held = list(held)
        self.refuse = refuse or {}
        self.calls = []

    def list_feeds(self):
        return [_dto(url) for url in self.held]

    def subscribe(self, url, source_type=None, title=None):
        self.calls.append((url, source_type, title))
        if url in self.refuse:
            raise self.refuse[url]
        self.held.append(url)
        return _dto(url)


def _envelope(*entries):
    return {"version": 1, "feeds": list(entries)}


class TestTally:
    def test_every_new_feed_is_added(self):
        subs = FakeSubscriptions()
        report = import_feeds(
            _envelope(
                {"url": "https://a/feed", "source_type": "rss", "title": " A "},
                {"url": "https://b/feed", "source_type": "atom", "title": None},
            ),
            subs,
        )
        assert report == ImportReport(2, 0, ())
        assert report.complete
        assert subs.calls == [
            ("https://a/feed", "rss", "A"),
            ("https://b/feed", "atom", None),
        ]

    def test_a_feed_already_held_is_counted_not_resubscribed(self):
        subs = FakeSubscriptions(held=["https://a/feed"])
        report = import_feeds(_envelope({"url": "https://a/feed"}), subs)
        assert report == ImportReport(0, 1, ())
        assert subs.calls == []

    def test_a_duplicate_within_the_file_is_already_held_the_second_time(self):
        subs = FakeSubscriptions()
        report = import_feeds(
            _envelope({"url": "https://a/feed"}, {"url": " https://a/feed "}), subs
        )
        assert report == ImportReport(1, 1, ())

    def test_a_refused_feed_is_named_with_its_reason_and_the_rest_still_import(
        self,
    ):
        subs = FakeSubscriptions(refuse={"https://bad/feed": ValueError("bad url")})
        report = import_feeds(
            _envelope({"url": "https://bad/feed"}, {"url": "https://good/feed"}),
            subs,
        )
        assert report.added == 1
        assert report.skipped == (SkippedEntry("https://bad/feed", "bad url"),)
        assert not report.complete

    def test_a_refusal_with_no_message_is_named_by_its_kind(self):
        subs = FakeSubscriptions(refuse={"https://x/feed": RuntimeError()})
        report = import_feeds(_envelope({"url": "https://x/feed"}), subs)
        assert report.skipped == (SkippedEntry("https://x/feed", "RuntimeError"),)

    @pytest.mark.parametrize("url", ["", "   ", None, 42])
    def test_an_entry_without_an_address_is_reported_by_position(self, url):
        report = import_feeds(_envelope({"url": url}), FakeSubscriptions())
        assert report.skipped == (SkippedEntry("Entry 1", "no address"),)

    def test_an_entry_that_is_not_an_object_is_reported_by_position(self):
        report = import_feeds(
            _envelope({"url": "https://a/feed"}, "https://b/feed"), FakeSubscriptions()
        )
        assert report.skipped == (SkippedEntry("Entry 2", "not a feed entry"),)

    def test_a_title_that_is_not_text_is_dropped(self):
        subs = FakeSubscriptions()
        import_feeds(_envelope({"url": "https://a/feed", "title": 7}), subs)
        assert subs.calls == [("https://a/feed", None, None)]


class TestShape:
    @pytest.mark.parametrize(
        "data", [[], "feeds", None, {}, {"feeds": "x"}, {"feeds": {"url": "y"}}]
    )
    def test_anything_but_the_envelope_is_refused_whole(self, data):
        with pytest.raises(NotAFeedList, match="not a Meridian feed list"):
            import_feeds(data, FakeSubscriptions())


class TestDescribe:
    def test_an_empty_list_says_so(self):
        assert ImportReport(0, 0, ()).describe() == "The file lists no feeds."

    def test_one_feed_is_singular(self):
        assert ImportReport(1, 0, ()).describe() == "Imported 1 feed."

    def test_added_and_already_held_are_both_said(self):
        assert ImportReport(3, 2, ()).describe() == (
            "Imported 3 feeds.\n2 feeds already subscribed."
        )

    def test_nothing_new_is_said_plainly(self):
        assert ImportReport(0, 1, ()).describe() == (
            "No new feeds were imported.\n1 feed already subscribed."
        )

    def test_every_refused_feed_is_named(self):
        report = ImportReport(
            1,
            0,
            (
                SkippedEntry("https://x", "bad url"),
                SkippedEntry("Entry 3", "no address"),
            ),
        )
        assert report.describe() == (
            "Imported 1 feed.\n2 feeds could not be imported:\n"
            "https://x: bad url\nEntry 3: no address"
        )

    def test_past_the_limit_the_rest_are_counted(self):
        extra = 3
        skipped = tuple(
            SkippedEntry(f"https://f/{n}", "bad url")
            for n in range(NAMED_SKIP_LIMIT + extra)
        )
        lines = ImportReport(0, 0, skipped).describe().splitlines()
        named = [line for line in lines if line.startswith("https://")]
        assert len(named) == NAMED_SKIP_LIMIT
        assert lines[-1] == f"... and {extra} more."
