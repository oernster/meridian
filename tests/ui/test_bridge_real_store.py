"""AppController over real services and a real SQLite file, offscreen.

The audit's findings sat where the stand-in services could not reach: export
was tested through a MagicMock that counted feeds, so the dropped filter was
invisible; the stored times lost their zone only in a real database. Every
test here builds the controller the way `main.py` does, minus the poller.
"""

import json
import threading
from datetime import datetime, timedelta, timezone

import pytest

from meridian.application.services.item_service import ItemService
from meridian.application.services.subscription_service import SubscriptionService
from meridian.domain.entities.item import Item
from meridian.domain.value_objects.item_type import ItemType
from meridian.infrastructure.db.session import build_session_factory
from meridian.infrastructure.repositories.sqlite_feed_repository import (
    SqliteFeedRepository,
)
from meridian.infrastructure.repositories.sqlite_item_repository import (
    SqliteItemRepository,
)
from tests.ui.bridge_dtos import make_controller, settle

_SPEC_EXAMPLE_THREE = (
    'keyword:"climate" AND lang:en AND published:>=2026-01-01T00:00:00Z'
)
_PLUS_FIVE = timezone(timedelta(hours=5))


class Store:
    def __init__(self, path):
        self.factory = build_session_factory(path)
        self.feeds = SqliteFeedRepository(self.factory)
        self.items = SqliteItemRepository(self.factory)
        self.subscriptions = SubscriptionService(self.feeds, self.items)

    def controller(self, qapp):
        return make_controller(
            qapp, self.subscriptions, ItemService(self.items, self.feeds)
        )

    def add_item(self, feed_id, name, published):
        self.items.save(
            Item(
                feed_id=feed_id,
                item_id=f"https://x.example/{name}",
                type=ItemType.ARTICLE,
                title=f"climate {name}",
                url=f"https://x.example/{name}",
                published=published,
                language="en",
            )
        )

    def close(self):
        self.factory.kw["bind"].dispose()


@pytest.fixture
def store(tmp_path):
    made = Store(tmp_path / "a.db")
    yield made
    made.close()


@pytest.fixture
def second_store(tmp_path):
    made = Store(tmp_path / "b.db")
    yield made
    made.close()


def _shown(controller):
    model = controller.itemModel
    role = next(k for k, v in model.roleNames().items() if bytes(v) == b"itemTitle")
    return [model.data(model.index(row, 0), role) for row in range(model.rowCount())]


def _recorded(controller):
    errors, reports = [], []
    controller.errorOccurred.connect(errors.append)
    controller.importReported.connect(lambda *args: reports.append(args))
    return errors, reports


class TestSelectingAFeed:
    def test_the_specifications_example_filter_shows_its_items(self, qapp, store):
        feed = store.subscriptions.subscribe("https://f.example/rss")
        store.add_item(feed.id, "new", datetime(2026, 1, 1, 10, tzinfo=_PLUS_FIVE))
        store.add_item(feed.id, "old", datetime(2025, 6, 1, tzinfo=timezone.utc))
        controller = store.controller(qapp)
        errors, _ = _recorded(controller)

        controller.setFilter(feed.id, _SPEC_EXAMPLE_THREE)
        controller.selectFeed(feed.id)

        assert (_shown(controller), errors) == (["climate new"], [])
        assert controller.selectedFeedId == feed.id

    def test_a_feed_that_cannot_be_read_never_shows_the_previous_one(self, qapp, store):
        shown = store.subscriptions.subscribe("https://f.example/rss")
        broken = store.subscriptions.subscribe("https://g.example/rss")
        store.add_item(shown.id, "f", datetime(2026, 1, 1, tzinfo=timezone.utc))
        store.add_item(broken.id, "g", datetime(2026, 1, 1, tzinfo=timezone.utc))
        # Written past the service, as an older version could have stored it.
        store.feeds.update_filter(broken.id, "type:video type:audio")
        controller = store.controller(qapp)
        errors, _ = _recorded(controller)
        controller.selectFeed(shown.id)

        controller.selectFeed(broken.id)

        assert _shown(controller) == []
        assert controller.selectedFeedId == 0, "Mark all read would act on it"
        assert errors == [
            (
                "This feed's filter cannot be used: Unexpected 'type:audio' after a "
                "complete expression"
            )
        ]
        assert not any(i.is_read for i in store.items.list_by_feed(broken.id))

    def test_newest_first_is_by_instant(self, qapp, store):
        feed = store.subscriptions.subscribe("https://f.example/rss")
        store.add_item(feed.id, "five", datetime(2026, 1, 1, 10, tzinfo=_PLUS_FIVE))
        store.add_item(feed.id, "six", datetime(2026, 1, 1, 6, tzinfo=timezone.utc))
        controller = store.controller(qapp)

        controller.selectFeed(feed.id)

        assert _shown(controller) == ["climate six", "climate five"]

    def test_an_invalid_filter_is_refused_with_a_message(self, qapp, store):
        feed = store.subscriptions.subscribe("https://f.example/rss")
        controller = store.controller(qapp)
        errors, _ = _recorded(controller)

        controller.setFilter(feed.id, "duration:>=soon")

        assert store.subscriptions.get_feed(feed.id).filter_expr is None
        assert errors == [
            (
                "The filter was not saved: 'duration:>=soon' is not a valid duration "
                "filter: a bound must be a number of seconds"
            )
        ]

    def test_the_dialog_is_given_the_parsers_terms(self, qapp, store):
        controller = store.controller(qapp)
        assert controller.filterTerms('keyword:"a AND b" AND lang:en') == [
            'keyword:"a AND b"',
            "lang:en",
        ]


class TestTheFeedListTravels:
    def test_export_then_import_brings_every_field_back(
        self, qapp, store, second_store, tmp_path
    ):
        """The README's path for keeping your data, end to end."""
        plain = store.subscriptions.subscribe("https://a.example/rss", title="A")
        store.subscriptions.set_filter(plain.id, 'NOT tag:"sponsored" AND lang:en')
        store.subscriptions.subscribe(
            "https://p.example/x",
            source_type="platform",
            platform_id="example",
            rss_fallback_url="https://p.example/rss",
        )
        target = tmp_path / "feeds.json"
        store.controller(qapp).exportFeeds(target.as_uri())

        controller = second_store.controller(qapp)
        errors, reports = _recorded(controller)
        controller.importFeeds(target.as_uri())
        settle(qapp, lambda: reports or errors)

        def fields(s):
            return sorted(
                (f.url, f.source_type, f.title, f.filter_expr, f.platform_id,
                 f.rss_fallback_url)
                for f in s.subscriptions.list_feeds()
            )  # fmt: skip

        assert (reports, errors) == ([("Imported 2 feeds.", True)], [])
        assert fields(second_store) == fields(store)

    def test_a_failed_export_leaves_the_previous_file_whole(
        self, qapp, store, tmp_path
    ):
        store.subscriptions.subscribe("https://a.example/rss")
        target = tmp_path / "feeds.json"
        target.mkdir()
        controller = store.controller(qapp)
        errors, _ = _recorded(controller)

        controller.exportFeeds(target.as_uri())

        assert len(errors) == 1 and errors[0].startswith("Export failed:")
        assert list(tmp_path.glob("feeds.json*.tmp")) == []

    def test_a_file_with_a_byte_order_mark_imports(self, qapp, store, tmp_path):
        source = tmp_path / "feeds.json"
        payload = {"version": 1, "feeds": [{"url": "https://a.example/rss"}]}
        source.write_bytes(json.dumps(payload).encode("utf-16"))
        controller = store.controller(qapp)
        errors, reports = _recorded(controller)

        controller.importFeeds(source.as_uri())
        settle(qapp, lambda: reports or errors)

        assert reports == [("Imported 1 feed.", True)]

    def test_a_newer_feed_list_is_refused_by_its_version(self, qapp, store, tmp_path):
        source = tmp_path / "feeds.json"
        source.write_text(json.dumps({"version": 2, "feeds": []}), encoding="utf-8")
        controller = store.controller(qapp)
        errors, reports = _recorded(controller)

        controller.importFeeds(source.as_uri())
        settle(qapp, lambda: reports or errors)

        assert errors == [
            (
                "Import failed: the file is feed list version 2; "
                "this Meridian reads version 1"
            )
        ]

    def test_the_import_runs_off_the_ui_thread(self, qapp, store, tmp_path):
        threads = []

        class Watching(SubscriptionService):
            def list_feeds(self):
                threads.append(threading.current_thread())
                return super().list_feeds()

        source = tmp_path / "feeds.json"
        source.write_text(json.dumps({"feeds": []}), encoding="utf-8")
        controller = make_controller(
            qapp,
            Watching(store.feeds, store.items),
            ItemService(store.items, store.feeds),
        )
        errors, reports = _recorded(controller)

        controller.importFeeds(source.as_uri())
        settle(qapp, lambda: reports or errors)

        assert threads[0].name == "meridian-import"
        assert threads[0] is not threading.main_thread()
