# Meridian Architecture

## Invariants

These are the rules the codebase is not allowed to break. Each one names the test that enforces it, so a violation is a red suite rather than a review comment.

| Invariant | Enforced by |
|---|---|
| Domain imports neither Application, Infrastructure nor UI; Application imports neither Infrastructure nor UI. Dependency direction is `UI -> Application -> Domain <- Infrastructure`, checked by AST scanning every module. | `tests/structural/test_boundaries.py::test_layer_boundary` |
| No Python module or QML component under `meridian/`, and no module under `tests/`, exceeds 400 lines. Four QML files and one test module were already over it and are carried in `_LEGACY_OVER_LIMIT` as tracked debt; that set may only shrink, and an entry that no longer needs the allowance fails the suite. | `tests/structural/test_boundaries.py::test_all_source_files_within_line_limit` and `::test_legacy_allowlist_has_no_stale_entries` |
| Every source file is `black`-formatted at line length 88. | `tests/structural/test_boundaries.py::test_black_compliance` |
| Every source file is `flake8`-clean. | `tests/structural/test_boundaries.py::test_flake8_compliance` |
| Branch coverage of the `meridian` package is 100%, with `main.py` the only omission. | `--cov-fail-under=100` in `pyproject.toml`, over the whole suite |
| The version string is read from the root `VERSION` file and appears nowhere else in source. | `tests/test_version.py::test_version_matches_the_root_version_file` and `::test_candidates_cover_package_parent_then_package` |
| A feed URL has to use `http://` or `https://`; anything else raises. | `tests/domain/test_entities.py::TestFeed::test_rejects_invalid_scheme` and `::test_accepts_http_url` |
| A redirect is only followed to an HTTPS target; a plain-HTTP `Location` is discarded. | `tests/infrastructure/test_http_fetcher.py::TestHttpFetcher::test_301_http_location_rejected` |
| Non-HTTPS media, enclosure and transcript URLs are dropped during parsing. | `tests/infrastructure/parser/test_rss_parser.py::test_https_only_enclosure` and `::test_media_content_http_excluded`, `test_atom_parser.py::test_enclosure_http_url_excluded`, `test_podcast_parser.py::test_transcript_http_excluded` |
| The poll interval can never fall below `POLL_FLOOR_SECONDS`; a 429 without `Retry-After` backs off to that floor. | `tests/domain/test_entities.py::TestPollConfig::test_floor_enforced_on_low_value` and `tests/infrastructure/test_http_fetcher.py::TestHttpFetcher::test_429_no_retry_after_uses_floor` |
| A response larger than `_MAX_DOCUMENT_BYTES` is refused rather than parsed. | `tests/infrastructure/test_http_fetcher.py::TestHttpFetcher::test_document_too_large_raises` |
| Polling is conditional: `ETag` and `Last-Modified` are sent and a 304 short-circuits. | `tests/infrastructure/test_http_fetcher.py::TestHttpFetcher::test_304_not_modified` and `::test_last_modified_header_sent` |
| Domain entities and value objects are frozen; mutation raises. | `tests/domain/test_entities.py::TestFeed::test_frozen` and `TestItem::test_frozen` |
| A `PLATFORM` feed cannot exist without a `platform_id`. | `tests/domain/test_entities.py::TestFeed::test_platform_requires_platform_id` |
| A filter expression cannot be empty, whitespace-only or a non-string. | `tests/domain/test_entities.py::TestFilterExpression` |

## Layer invariant in detail

```
UI -> Application -> Domain <- Infrastructure
```

- **Domain**: stdlib only. No I/O, no framework imports. Pure Python dataclasses and services.
- **Application**: Domain + stdlib only. Never imports Infrastructure or UI. Defines interfaces (ABCs) that Infrastructure implements.
- **Infrastructure**: Implements Application interfaces. Owns all I/O (SQLite, HTTP). Never imported by Domain or Application.
- **UI**: Client of Application only via `AppController`. No direct access to Domain entities or Infrastructure.

Cross-layer data moves as DTOs defined in `application/dto`, never as Domain entities crossing into the UI.

## Directory Structure

```
VERSION                       Single source of truth for the version string

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
      http_fetcher.py       HttpFetcher: httpx async client, MMSP/1.0 UA, conditional GET (ETag/Last-Modified), HTTPS-only redirects, 10 MB document cap, 300s poll floor
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
      SubscriptionManager.qml  Drawer: add subscription URL field (enabled only for an https:// URL), subscribe button, bulk select/remove, per-feed filter/edit/remove buttons; full keyboard nav (Tab chain, Enter/Space/Left/Right); filter dialog shows existing terms as tabbable toggleable rows, new terms appended on accept
      FeedDiscovery.qml     Feed discovery drawer: topic search via feedsearch.dev, category autocomplete (~46 categories), result cap selector, candidate list with per-item and bulk subscribe. Escape closes panel (from queryField: closes autocomplete, then cancels search, then closes; from all other controls: closes immediately).
      AboutDialog.qml       About dialog (keyboard: Enter/Escape closes)
      LicenceDialog.qml     Licence dialog (keyboard: scroll text, Tab to Close, Enter/Escape closes)

  main.py                   Composition root (excluded from coverage)
  version.py                Application identity; reads the root VERSION file with a 0.0.0-dev fallback

tests/
  structural/
    test_boundaries.py      AST-based layer boundary enforcement + module size limits + black and flake8
  domain/                   Unit tests for domain services and entities
  application/              Unit tests for application services (fakes for infrastructure)
  infrastructure/
    parser/                 Parser tests for RSS, Atom, podcast, mfeed formats
    test_repositories.py    SQLite repository integration tests
  ui/
    test_bridge.py          QML bridge unit tests (pytest-qt)
  test_version.py           VERSION file resolution and fallback
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
  enforces: HTTPS-only redirects, 300s poll floor, MMSP/1.0 User-Agent, conditional GET, 10 MB document cap

FilterEvaluator (Domain)
  pure evaluation of ABNF filter expressions against Item entities
```

## Execution Flow

1. `main.py` wires all dependencies and calls `QQmlApplicationEngine.load("main.qml")`
2. `controller` injected as QML context property
3. `AppController.loadFeeds()` on startup: `SubscriptionService.list_feeds()` then `FeedListModel.refresh()`
4. User selects feed: `AppController.selectFeed(id)` then `ItemService.get_items(id)` (dedup + filter) then `ItemListModel.refresh()`
5. User selects item: QML `_loadItem()` renders title, meta, media player or description in detail pane
6. `PollScheduler` runs background asyncio tasks, ticks every 10s, polls each feed when its interval has elapsed
7. On new items: `AppController.notify_new_items()` refreshes the relevant `ItemListModel` if that feed is selected
8. Bulk feed removal: `bulkUnsubscribe()` calls `remove_rows_by_ids()` on `FeedListModel` (row-level removal, scroll position preserved)

## Key Design Decisions

**Version in a file, not in source**: the root `VERSION` file holds the only copy of the version string. `meridian/version.py` reads it (falling back to `0.0.0-dev` when it cannot be found), `pyproject.toml` takes its dynamic version from the same file, the build scripts bundle it alongside the application; `stamp_version.py` writes it into the delimited tokens in `docs/`. A release bump is a one-line edit followed by one script.

**Frozen domain entities**: all domain objects are `@dataclass(frozen=True, slots=True)`. State mutation lives in Infrastructure ORM rows; entities are re-hydrated into new instances on each read.

**PollState separate from Feed**: subscription intent (`Feed`) is immutable; polling operational state (`PollState`) is a separate Infrastructure table. A Feed can be added without ever being polled.

**No push/notify**: per MMSP spec, no subscriber notifications on new items. `PollScheduler` is silent; new items appear on the next user-initiated view or on the 10s scheduler tick for the selected feed.

**content:encoded preferred**: RSS parser reads `content:encoded` before `<description>` so full-text article HTML is shown where available.

**In-place model removal**: `bulkUnsubscribe` uses `beginRemoveRows`/`endRemoveRows` instead of a full model reset so the feed list scroll position is preserved after bulk deletion.

**Platform adapters**: registered at runtime via `platform_parser.register_adapter()`. No adapters are built-in; RSS is always the fallback.

**HTML rendering**: `TextArea { textFormat: Text.RichText }` in QML. Plain-text descriptions (no HTML tags) are converted to `<br/>`-separated HTML before display. Raw HTML from `content:encoded` is passed through directly.

**Transport policy**: `Feed.__post_init__` accepts `http://` and `https://` and rejects every other scheme, so an imported or discovered plain-HTTP feed still loads. Everything downstream of that is stricter: the Add Subscription field in `SubscriptionManager.qml` only enables Subscribe for an `https://` URL, `HttpFetcher` discards a non-HTTPS redirect target; the parsers drop non-HTTPS media, enclosure and thumbnail URLs.

**Keyboard navigation**: Qt Quick Controls `Button` handles Space natively but not Enter/Return. Every `StyledButton` instance and interactive `Rectangle` in the QML layer has an explicit `Keys.onReturnPressed` handler. Dialog footer buttons are given IDs and Left/Right key handlers to allow lateral navigation between Cancel and OK without leaving the keyboard. Qt6 TextField intercepts Tab internally; tab-chain control uses `activeFocusOnTab` on surrounding items rather than `KeyNavigation.tab` on the field itself.

Tab wrap-around uses explicit `forceActiveFocus()` with `event.accepted = true` on every boundary. `KeyNavigation.tab` and `setFocus()` both fail across QML `FocusScope` boundaries; only `forceActiveFocus()` works. Critical invariant: `ScrollView`'s `contentItem` is a `Flickable`, which is a `FocusScope`, so any focusable control inside a `ScrollView` is trapped and Tab can never escape it. Controls that must participate in the outer Tab chain must be placed outside the `ScrollView` in the component tree.

**Theme persistence**: dark/light mode stored via `Qt.labs.settings` with `category: "Theme"`, property `isDark: true`. Reads on startup; written on toggle. Uses same `QSettings` backend as volume (category `"Player"`); no conflict since categories are separate.

## Quality Enforcement

- `--cov-fail-under=100`: 100% branch coverage required
- Structural AST tests enforce layer boundaries; the 400-line size limit is enforced over QML and the test tree as well as the Python package, with an explicit allowlist that can only shrink
- `black` and `flake8` run as in-suite assertions, so unformatted or lint-failing code is a test failure
- `POLL_FLOOR_SECONDS = 300` is the single source of truth for the polling floor; no magic numbers in logic

## Licence

Meridian is dual-licensed, split by component (see `LICENSE` for the map):

- Model (`domain`, `application`, `infrastructure`, `main.py`, `version.py`, build scripts, tests): Apache-2.0 (matches the MMSP specification ecosystem).
- User interface (`ui`) only: LGPL-3.0-or-later, to align with Qt's licensing.

Third-party runtime dependencies:

PySide6: LGPL-3.0 (dynamically linked; compliant by default install).
bleach: Apache-2.0.
SQLAlchemy: MIT.
httpx: BSD-3-Clause.
defusedxml: PSF.
python-dateutil: Apache-2.0 / BSD-3-Clause.
