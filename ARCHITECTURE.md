# Meridian Architecture

## Invariant

`UI -> Application -> Domain <- Infrastructure`

- **Domain**: stdlib only. No I/O. No framework imports. Pure Python dataclasses and services.
- **Application**: Domain + stdlib only. Never imports Infrastructure or UI. Defines interfaces (ABCs) that Infrastructure implements.
- **Infrastructure**: Implements Application interfaces. Owns I/O (SQLite, HTTP). Never imported by Domain or Application.
- **UI**: Client of Application only via `AppController`. No direct access to Domain entities or Infrastructure.

Structural tests in `tests/structural/test_boundaries.py` enforce this via AST scanning. Boundary violation = test failure.

## Components

```
meridian/
  domain/
    entities/         Feed, Item (frozen dataclasses)
    value_objects/    SourceType, ItemType, PollConfig, Media types, FilterExpression
    services/         FilterEvaluator (Appendix A ABNF), Deduplication
  application/
    dto/              FeedDTO, ItemDTO (cross-boundary data carriers)
    interfaces/       FeedRepository, ItemRepository, FeedFetcher, PollStateRepository (ABCs)
    services/         SubscriptionService, ItemService, PollOrchestrator
  infrastructure/
    db/               SQLAlchemy ORM models, session factory (SQLite)
    repositories/     SqliteFeedRepository, SqliteItemRepository, SqlitePollStateRepository
    fetching/
      parser/         mfeed_parser, rss_parser, atom_parser, podcast_parser, platform_parser
      http_fetcher    HttpFetcher (httpx, MMSP/1.0 UA, conditional GET, 300s floor)
      scheduler       PollScheduler (asyncio, per-feed poll tasks)
  ui/
    bridge.py         FeedListModel, ItemListModel, AppController (QObject/QML bridge)
    qml/              main.qml, FeedReader.qml, SubscriptionManager.qml
  main.py             Explicit composition root
```

## Dependency Direction

```
main.py
  builds: session_factory, repositories, fetcher, services, controller, scheduler
  
AppController (UI)
  <- SubscriptionService (Application)
  <- ItemService (Application)

SubscriptionService / ItemService / PollOrchestrator (Application)
  <- FeedRepository, ItemRepository, PollStateRepository (interfaces)
  <- FeedFetcher (interface)

SqliteFeedRepository, SqliteItemRepository, SqlitePollStateRepository (Infrastructure)
  -> implements Application interfaces
  -> uses SQLAlchemy ORM

HttpFetcher (Infrastructure)
  -> implements FeedFetcher
  -> delegates to source-type parsers
  -> enforces 300s poll floor, MMSP/1.0 User-Agent, HTTPS-only

FilterEvaluator (Domain service)
  -> tokenizes and parses Appendix A ABNF filter expressions
  -> evaluates against Item entities (pure, no I/O)
```

## Execution Flow

1. `main.py` builds all dependencies and wires composition root
2. `QQmlApplicationEngine` loads `main.qml`, `controller` injected via context property
3. `AppController.loadFeeds()` called on startup: queries `SubscriptionService`, populates `FeedListModel`
4. User selects feed: `AppController.selectFeed(id)` -> `ItemService.get_items(id)` -> dedup + filter -> `ItemListModel`
5. `PollScheduler` runs background asyncio tasks, ticks every 10s, polls each feed when due
6. On new items: `AppController.notify_new_items()` refreshes models

## Design Choices

- **Frozen domain entities**: all domain objects are `@dataclass(frozen=True, slots=True)`. State mutation happens in Infrastructure (ORM rows) and is re-hydrated into new entity instances.
- **PollState separate from Feed**: feed subscription intent (Feed entity) is immutable; poll operational state (PollState) lives in Infrastructure, separate table.
- **No push/notify**: per MMSP spec, no subscriber notifications on new items. `PollScheduler` is silent; items appear on next user-initiated view.
- **Platform adapters**: registered at runtime via `platform_parser.register_adapter()`. None built-in; RSS fallback always available.
- **HTML sanitization**: `bleach` used at render time in QML via `TextArea.textFormat = Text.RichText`. Do not trust raw HTML from feeds.
- **HTTPS enforcement**: Feed URLs validated in `Feed.__post_init__`. Non-HTTPS media URLs excluded in parsers. HttpFetcher rejects non-HTTPS 301 locations.

## Quality Enforcement

- `--cov-fail-under=100` in `pyproject.toml`
- Structural AST boundary tests in `tests/structural/`
- Module size limit: 400 lines enforced via structural test (domain + application layers)
- No magic numbers: `POLL_FLOOR_SECONDS = 300` in `poll_config.py`, referenced everywhere

## License

Apache-2.0 (matches MMSP specification ecosystem).
PySide6: LGPL-3.0 (dynamically linked; compliant by default install).
