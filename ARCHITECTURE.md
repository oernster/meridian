# Meridian Architecture

## Layer Invariant

```
UI -> Application -> Domain <- Infrastructure
```

- **Domain**: stdlib only. No I/O, no framework imports. Pure Python dataclasses and services.
- **Application**: Domain + stdlib only. Never imports Infrastructure or UI. Defines interfaces (ABCs) that Infrastructure implements.
- **Infrastructure**: Implements Application interfaces. Owns all I/O (SQLite, HTTP). Never imported by Domain or Application.
- **UI**: Client of Application only via `AppController`. No direct access to Domain entities or Infrastructure.

Structural boundary tests in `tests/structural/test_boundaries.py` enforce this via AST scanning at every test run. A boundary violation is a test failure.

## Directory Structure

```
meridian/
  domain/
    entities/
      feed.py               Feed (frozen dataclass: id, url, title, source_type, filter_expr)
      item.py               Item (frozen dataclass: feed_id, item_id, type, title, url, published, description, media, authors, tags)
    value_objects/
      source_type.py        SourceType enum (rss, atom, mfeed, podcast, youtube)
      item_type.py          ItemType enum (article, video, audio, short, livestream, podcast)
      media.py              Media, Thumbnail, Author, ItemSource value objects
      poll_config.py        PollConfig (min_interval_seconds); POLL_FLOOR_SECONDS = 300
      filter_expression.py  FilterExpression wrapper
    services/
      filter_evaluator.py   ABNF filter evaluation against Item entities (pure, no I/O)
      deduplication.py      Dedup logic (item_id uniqueness within a feed)

  application/
    dto/
      feed_dto.py           FeedDTO (cross-boundary carrier: id, url, title, source_type, unread_count, ...)
      item_dto.py           ItemDTO (cross-boundary carrier: all item fields as primitives)
      feed_candidate_dto.py FeedCandidateDTO (discovery result: url, title, description, is_subscribed flag)
    interfaces/
      feed_repository.py    FeedRepository ABC (get_by_id, list, save, delete, update_filter, update_title)
      item_repository.py    ItemRepository ABC (list_by_feed, save, mark_read, mark_all_read, unread_count, exists)
      poll_state_repository.py  PollStateRepository ABC (get, save)
      discovery_fetcher.py  DiscoveryFetcher ABC + DiscoveryError; DEFAULT_RESULT_CAP = 25
    services/
      subscription_service.py   subscribe, unsubscribe, list_feeds, set_filter, get_feed
      item_service.py           get_items (dedup + filter), mark_read, mark_all_read
      poll_orchestrator.py      poll_feed (HTTP fetch, parse, persist new items, auto-discover title)
      discovery_service.py      search_feeds (delegates to DiscoveryFetcher, enriches with is_subscribed flag)
      source_type_inference.py  infer SourceType from URL/content-type; extracted from SubscriptionService

  infrastructure/
    db/
      orm_models.py         SQLAlchemy ORM: FeedRow, ItemRow, PollStateRow; session_factory()
    repositories/
      sqlite_feed_repository.py
      sqlite_item_repository.py
      sqlite_poll_state_repository.py
    fetching/
      http_fetcher.py       HttpFetcher: httpx async client, MMSP/1.0 UA, conditional GET (ETag/Last-Modified), HTTPS-only, 300s poll floor
      scheduler.py          PollScheduler: asyncio task per feed, 10s tick, per-feed backoff state
      feedsearch_fetcher.py FeedsearchFetcher: implements DiscoveryFetcher via feedsearch.dev REST API (httpx async)
      parser/
        platform_parser.py  Dispatcher: registered adapters first, RSS fallback
        rss_parser.py       RSS 2.0 + RSS 1.0/RDF; content:encoded preferred over description
        atom_parser.py      Atom 1.0; content preferred over summary; media:group (YouTube)
        podcast_parser.py   RSS with <itunes:*> extensions
        mfeed_parser.py     MMSP JSON feed format

  ui/
    bridge.py
      FeedListModel         QAbstractListModel: feedId, feedUrl, feedTitle, feedIcon, feedSourceType, feedUnreadCount, feedDescription, feedFilter (UserRole+0..7); remove_rows_by_ids() for in-place removal
      ItemListModel         QAbstractListModel: all ItemDTO fields as QML roles
      AppController         QObject: loadFeeds, selectFeed, subscribe, unsubscribe, bulkUnsubscribe, markRead, markAllRead, setFeedSort, setItemSort, setFilter (calls loadFeeds to refresh filter label), updateFeedUrl, importFeeds, exportFeeds, searchFeeds, cancelSearch, subscribeFromDiscovery, bulkSubscribeFromDiscovery, setResultCap
    qml/
      main.qml              Application window: feed sidebar (checkboxes, sort, bulk remove, right-click context menu), header bar, theme toggle (persists via Qt.labs.settings); full keyboard nav with Enter/Space/Left/Right on all interactive controls; Tab wraps from last control back to Import via feedReader.lastFocusItem
      FeedReader.qml        Two-panel reader: item list with sort + mark-all-read; detail pane with media player, full-text description (ScrollView), open-in-browser. Exposes firstHeaderBtn (set by parent to importBtn) and lastFocusItem (always openBtnRect) for cross-component Tab wrap. openBtnRect is a direct child of the detail pane Rectangle, NOT inside ScrollView (ScrollView's Flickable is a FocusScope that traps Tab).
      SubscriptionManager.qml  Drawer: add subscription URL field, subscribe button, bulk select/remove, per-feed filter/edit/remove buttons; full keyboard nav (Tab chain, Enter/Space/Left/Right); filter dialog shows existing terms as tabbable toggleable rows, new terms appended on accept
      FeedDiscovery.qml     Feed discovery drawer: topic search via feedsearch.dev, category autocomplete (~46 categories), result cap selector, candidate list with per-item and bulk subscribe. Escape closes panel (from queryField: closes autocomplete, then cancels search, then closes; from all other controls: closes immediately).
      AboutDialog.qml       About dialog (keyboard: Enter/Escape closes)
      LicenceDialog.qml     Licence dialog (keyboard: scroll text, Tab to Close, Enter/Escape closes)

  main.py                   Composition root (excluded from coverage)
  version.py                __version__ string

tests/
  structural/
    test_boundaries.py      AST-based layer boundary enforcement + module size limits
  domain/                   Unit tests for domain services and entities
  application/              Unit tests for application services (mocked infrastructure)
  infrastructure/
    parser/                 Parser tests for RSS, Atom, podcast, mfeed formats
    test_repositories.py    SQLite repository integration tests
  ui/
    test_bridge.py          QML bridge unit tests (pytest-qt)
```

## Dependency Graph

```
main.py
  builds: session_factory, repositories, fetcher, services, controller, scheduler

AppController (UI)
  <- SubscriptionService
  <- ItemService

SubscriptionService / ItemService / PollOrchestrator (Application)
  <- FeedRepository, ItemRepository, PollStateRepository (interfaces)
  <- FeedFetcher (interface)

SqliteFeedRepository, SqliteItemRepository, SqlitePollStateRepository (Infrastructure)
  implements Application interfaces via SQLAlchemy ORM

HttpFetcher (Infrastructure)
  implements FeedFetcher
  delegates to platform_parser -> rss/atom/podcast/mfeed parsers
  enforces: HTTPS-only, 300s poll floor, MMSP/1.0 User-Agent, conditional GET

FilterEvaluator (Domain)
  pure evaluation of ABNF filter expressions against Item entities
```

## Execution Flow

1. `main.py` wires all dependencies and calls `QQmlApplicationEngine.load("main.qml")`
2. `controller` injected as QML context property
3. `AppController.loadFeeds()` on startup: `SubscriptionService.list_feeds()` → `FeedListModel.refresh()`
4. User selects feed: `AppController.selectFeed(id)` → `ItemService.get_items(id)` (dedup + filter) → `ItemListModel.refresh()`
5. User selects item: QML `_loadItem()` renders title, meta, media player or description in detail pane
6. `PollScheduler` runs background asyncio tasks, ticks every 10s, polls each feed when its interval has elapsed
7. On new items: `AppController.notify_new_items()` refreshes the relevant `ItemListModel` if that feed is selected
8. Bulk feed removal: `bulkUnsubscribe()` calls `remove_rows_by_ids()` on `FeedListModel` (row-level removal, scroll position preserved)

## Key Design Decisions

**Frozen domain entities**: all domain objects are `@dataclass(frozen=True, slots=True)`. State mutation lives in Infrastructure ORM rows; entities are re-hydrated into new instances on each read.

**PollState separate from Feed**: subscription intent (`Feed`) is immutable; polling operational state (`PollState`) is a separate Infrastructure table. A Feed can be added without ever being polled.

**No push/notify**: per MMSP spec, no subscriber notifications on new items. `PollScheduler` is silent; new items appear on the next user-initiated view or on the 10s scheduler tick for the selected feed.

**content:encoded preferred**: RSS parser reads `content:encoded` before `<description>` so full-text article HTML is shown where available.

**In-place model removal**: `bulkUnsubscribe` uses `beginRemoveRows`/`endRemoveRows` instead of a full model reset so the feed list scroll position is preserved after bulk deletion.

**Platform adapters**: registered at runtime via `platform_parser.register_adapter()`. No adapters are built-in; RSS is always the fallback.

**HTML rendering**: `TextArea { textFormat: Text.RichText }` in QML. Plain-text descriptions (no HTML tags) are converted to `<br/>`-separated HTML before display. Raw HTML from `content:encoded` is passed through directly.

**HTTPS enforcement**: `Feed.__post_init__` rejects non-HTTPS URLs. Non-HTTPS media URLs are excluded in parsers. `HttpFetcher` rejects non-HTTPS redirect targets.

**Keyboard navigation**: Qt Quick Controls `Button` handles Space natively but not Enter/Return. Every `StyledButton` instance and interactive `Rectangle` in the QML layer has an explicit `Keys.onReturnPressed` handler. Dialog footer buttons are given IDs and Left/Right key handlers to allow lateral navigation between Cancel and OK without leaving the keyboard. Qt6 TextField intercepts Tab internally; tab-chain control uses `activeFocusOnTab` on surrounding items rather than `KeyNavigation.tab` on the field itself.

Tab wrap-around uses explicit `forceActiveFocus()` with `event.accepted = true` on every boundary. `KeyNavigation.tab` and `setFocus()` both fail across QML `FocusScope` boundaries; only `forceActiveFocus()` works. Critical invariant: `ScrollView`'s `contentItem` is a `Flickable`, which is a `FocusScope` — any focusable control inside a `ScrollView` is trapped and Tab can never escape it. Controls that must participate in the outer Tab chain must be placed outside the `ScrollView` in the component tree.

**Theme persistence**: dark/light mode stored via `Qt.labs.settings` with `category: "Theme"`, property `isDark: true`. Reads on startup; written on toggle. Uses same `QSettings` backend as volume (category `"Player"`); no conflict since categories are separate.

## Quality Enforcement

- `--cov-fail-under=100`: 100% branch coverage required
- Structural AST tests enforce layer boundaries and 400-line module size limits (domain + application layers)
- `POLL_FLOOR_SECONDS = 300` is the single source of truth for the polling floor; no magic numbers in logic

## Licence

Apache-2.0 (matches MMSP specification ecosystem).
PySide6: LGPL-3.0 (dynamically linked; compliant by default install).
bleach: Apache-2.0.
SQLAlchemy: MIT.
httpx: BSD-3-Clause.
