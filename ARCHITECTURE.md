# Meridian Architecture

## Invariants

These are the rules the codebase is not allowed to break. Each one names the test that enforces it, so a violation is a red suite rather than a review comment.

| Invariant | Enforced by |
|---|---|
| Domain imports neither Application, Infrastructure nor UI; Application imports neither Infrastructure nor UI. Dependency direction is `UI -> Application -> Domain <- Infrastructure`, checked by AST scanning every module. | `tests/structural/test_boundaries.py::test_layer_boundary` |
| No Python module or QML component under `meridian/` exceeds 400 lines; nor does any module under `tests/` or `installer/`; nor does any of them sit in the danger band of 381 to 399. `_LEGACY_OVER_LIMIT`, the allowance for files that predated the scan widening, is empty: every file in scope now clears the cap on its own. The set may only shrink, so an entry that no longer needs the allowance fails the suite. Both band bounds derive from the cap rather than being written as second literals, so they cannot drift apart. | `tests/structural/test_boundaries.py::test_all_source_files_within_line_limit`, `::test_no_source_file_sits_in_the_danger_band` and `::test_legacy_allowlist_has_no_stale_entries` |
| Every Python file is `black`-formatted at line length 88: `meridian/`, `installer/`, `tests/` and every root delivery script. The delivery scripts are exempt from the size cap, never from the formatters. | `tests/structural/test_boundaries.py::test_black_compliance` |
| Every Python file in the same set is `flake8`-clean. | `tests/structural/test_boundaries.py::test_flake8_compliance` |
| Branch coverage is 100% over the `meridian` package, `installer/ops` and the installer's operation dispatch. Seven omissions, each named and reasoned: `meridian/main.py` (composition root), `shortcuts.create_shortcut` (writes a real `.lnk` through COM into the running user's own profile), `uninstall_ops._schedule_delete_after_exit` (spawns a detached PowerShell holding a real deletion), `launch_ops.launch` and `launch_ops.bring_process_window_to_front` (start a real application and put its window in front, which is a side effect on the developer's machine rather than a test) and two `# pragma: no cover` branches that only a broken system reaches, the `case _` exhaustiveness guard in `http_fetcher` and the stale-generation guard in `bridge._on_done`. The shortcut and uninstall callers are covered and assert what they are handed; the launch pair is called from the installer window, which is outside the gate, so what is gated instead is `exe_to_launch`, the decision of whether to call it. | `--cov-fail-under=100` in `pyproject.toml`, over the whole suite |
| Every QML file compiles. The coverage gate reads Python only and `qmllint` cannot be turned into a gate here (unqualified-access warnings by the hundred, inherent to a context-property front end, plus an exit code of 0 regardless), so compiling is the check that holds: it catches a syntax error, a property assigned on a type that has none or an unresolvable component, which is what extracting components can introduce. | `tests/ui/test_qml_compiles.py` |
| The keyboard focus ring closes: across the window (header to sidebar to reader), through the reader itself (sort chips to mark-all-read to the item list, across into the detail pane and back out to the header) and across the discovery drawer. Each handover between components is a signal the composing file connects; a missed connection compiles and leaves every component correct alone, so each is asserted with real key events through a real window rather than by inspection. | `tests/ui/test_main_window_focus_ring.py`, `test_feed_reader.py` and `test_discovery_focus_ring.py` |
| Long help content reads itself at one pace for the whole application: still for 5000ms on opening, down one pixel every second 40ms tick, 5000ms at the bottom, back up at fifteen pixels a tick, 2000ms at the top, repeat. A reader taking hold suspends the cycle for 2500ms and it resumes from where they left it, never switching off; a surface that is closed or covered is frozen in place rather than stopped. | `tests/ui/test_auto_scroller.py` and `test_dialog_auto_scroll.py` |
| Clicking a row activates it: a feed row reaches `selectFeed` and an item row loads the detail pane and marks the item read, both with a real mouse press through a real window. The keyboard path into a list reports through the view's own `onCurrentIndexChanged` and never touches the delegate, so it cannot stand in for this. | `tests/ui/test_row_activation.py` |
| Every installer operation reports its progress as a percentage, so the bar fills rather than standing empty for the duration. Install and upgrade always did; repair and uninstall reported their work in bare strings, which the window writes to the status line while leaving the bar untouched, so both ran behind an empty groove that read as a progress bar failing to appear. The bar is now also indeterminate from the moment work starts until the first percentage arrives, so a stage with nothing to measure shows movement rather than nothing. | `tests/test_installer_progress.py`, `tests/test_installer_repair_ops.py::test_repair_moves_the_progress_bar_rather_than_only_the_status_line` and `tests/test_installer_uninstall_ops.py::test_feedback_wrapper_reports_either_side_of_the_work` |
| The installer starts the application when it has finished only if the user left the box ticked, only if the operation succeeded, only after an install, upgrade, reinstall or repair and only when the executable it recorded is still there. Uninstall is refused by operation rather than by what survives on disk, since a deletion still settling would otherwise read as something worth starting. The rule is a pure function inside the coverage gate precisely because the Qt slot calling it is outside one. | `tests/test_installer_launch_ops.py` |
| Removing a feed, singly or in bulk, asks before it acts. The sidebar and the context menu only report the request; the window is what opens the confirmation, so only its `accepted` reaches the controller. | `tests/ui/test_main_window_focus_ring.py::test_removing_the_selection_asks_first` |
| The MMSP protocol version is stated once, in `infrastructure/fetching/mmsp.py`; both the User-Agent and the parser's version gate derive from it. A feed declaring any 1.MINOR is read and anything else is refused, per specification Section 5.7. Where the MMSP-Spec repository is checked out beside this one, that rule is asserted against the published feed schema, so the two expressions of it cannot drift apart. | `tests/infrastructure/test_mmsp_conformance.py` |
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
      source_type.py        SourceType enum (mfeed, rss, atom, podcast, platform). A YouTube channel is an Atom feed and is read by the Atom parser; `platform` is for a registered adapter
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
      mmsp.py               The MMSP protocol version and the Section 5.7 rule for which documents are readable
      http_fetcher.py       HttpFetcher: httpx async client, User-Agent derived from the protocol version, conditional GET (ETag/Last-Modified), HTTPS-only redirects, 10 MB document cap, 300s poll floor
      scheduler.py          PollScheduler: asyncio task per feed, 10s tick, per-feed backoff state
      feedsearch_fetcher.py FeedsearchFetcher: implements DiscoveryFetcher against Feedly's public search API at cloud.feedly.com (httpx async). The name is a leftover from an earlier directory; Feedly indexes RSS, Atom and podcast sources only, so no MFEED feed is discoverable here
      parser/
        platform_parser.py  Dispatcher: registered adapters first, RSS fallback
        rss_parser.py       RSS 2.0 + RSS 1.0/RDF; content:encoded preferred over description
        atom_parser.py      Atom 1.0; content preferred over summary; media:group (YouTube)
        podcast_parser.py   RSS with <itunes:*> extensions
        mfeed_parser.py     MMSP JSON feed format

  ui/
    models.py
      FeedListModel         QAbstractListModel: feedId, feedUrl, feedTitle, feedIcon, feedSourceType, feedUnreadCount, feedDescription, feedFilter (UserRole+0..7); remove_rows_by_ids() for in-place removal
      ItemListModel         QAbstractListModel: every ItemDTO field as a QML role (UserRole+0..10)
      FeedCandidateModel    QAbstractListModel: the discovery results (UserRole+0..5); mark_subscribed() flips one row rather than resetting the model
    bridge.py
      AppController         QObject: loadFeeds, selectFeed, subscribe, unsubscribe, bulkUnsubscribe, markRead, markAllRead, setFeedSort, setItemSort, setFilter (calls loadFeeds to refresh filter label), updateFeedUrl, importFeeds, exportFeeds, searchFeeds, cancelSearch, subscribeFromDiscovery, bulkSubscribeFromDiscovery, setResultCap
    qml/
      main.qml              Application window, composition only: owns the feed selection (which the sidebar shows, the context menu acts on and the removal confirmations consume), the palette, plus the wiring from each panel's signals to the controller. A 0x0 focus absorber holds focus at startup so nothing wears a border before the first Tab. Header, sidebar and reader name nothing outside themselves; the focus ring passes between them here
      Theme.qml             The palette: Catppuccin Mocha and Latte, with `isDark` choosing. A plain property, not a binding, so the toggle sticks and the window writes the new value back to Qt.labs.settings
      HeaderBar.qml         Header: Import, Export, Search, Manage on the left; the two licences, About and the theme toggle on the right. Reports what was pressed rather than acting. firstFocusItem is the Import button, which FeedReader wraps its own Tab chain back to
      HeaderButton.qml      One header button. Neighbours are Items rather than signals, because they all live in one row and genuinely know each other; leaving one unset marks the end of the row and raises an overflow signal instead
      FeedSidebar.qml       Select-all, the bulk remove button, the sort chips and the feed list. The chips are a SortChipRow, shared with the reader; the sidebar only says where the row overflows at either end
      FeedRow.qml           One feed in the sidebar list, used as its delegate. Six `required` properties named for FeedListModel's roles, so the view binds them by name. Current-row styling comes from the attached ListView property, so the row never needs its own index
      FeedContextMenu.qml   The sidebar's right-click menu. Closes itself before reporting, since both entries lead to a confirmation that would otherwise open underneath it
      ConfirmDialog.qml     A modal message with Cancel and OK; or OK alone (okOnly). Carries the chrome the single removal, the bulk removal and the error report each wrote out in full
      FeedReader.qml        Two-panel reader, composition only: the join between the list and the pane, the stored playback volume and the wiring to the controller. Selecting a row reports outwards from the list; loading the pane and marking the item read happen here, so neither panel knows the other exists. Exposes firstHeaderBtn (set by the window to importBtn) and lastFocusItem (the pane's openButton) for cross-component Tab wrap
      ItemListPanel.qml     The reader's left panel: sort chips, mark-all-read and the item list. Reads the model directly through one map of role offsets, because a delegate for an unrealised row does not exist, so currentItem cannot answer what the current row holds
      ItemRow.qml           One item in the reader list, used as its delegate. Eight `required` properties named for ItemListModel's roles, so the view binds them by name; the duration caption is formatted by the panel and handed in
      ItemDetailPane.qml    The right pane: placeholder, article and open-in-browser. Its state is ordinary properties, which is what a component can have and the inline block could not (three hidden Labels parked outside the layout, so a rebuild would not lose them). openButton is a direct child of the pane, NOT inside the ScrollView (ScrollView's Flickable is a FocusScope that traps Tab)
      MediaPlayerPanel.qml  Video surface, YouTube embed or audio placeholder, plus the transport bar. Decides which of the three by matching the page URL against a watch or youtu.be link. Everything but the embed plays locally through QtMultimedia; the embed is a `WebEngineView` loading `youtube.com/embed/<id>`, which is the application's only use of QtWebEngine and the only place the UI reaches a third party of its own accord. The transport is hidden for an embed, which brings its own, so hasTransport is what both focus neighbours ask rather than assuming the panel is a stop
      SortChipRow.qml       A row of sort chips where the active one is not a tab stop. Used by both the sidebar and the reader; the search past the active chip is two functions here rather than the twelve copies it was. Both return whether a chip took focus, because a single-option row has none to give and the caller has somewhere else to go
      SubscriptionManager.qml  Drawer, composition only: owns the selection the list header shows and the rows toggle, the list itself, plus the wiring from each panel's signals to the controller. focusUrlField() reaches into the add bar, which is what the drawer opens onto
      AddSubscriptionBar.qml   The URL field and Subscribe. The https:// test is one readonly property rather than the six copies it was; Subscribe is only a tab stop while the field passes it, so focusLast() asks rather than assumes
      SubscriptionRow.qml   One subscription in the manager list, used as its delegate. Five `required` properties named for FeedListModel's roles; which dialog a row action opens is the caller's business, because the caller owns them
      RowActionButton.qml   A small flat row action (Filter, Edit, Remove). Neighbours are Items, as on the header bar, because all three sit in one row
      FormDialog.qml        A modal dialog with Cancel and OK, taking arbitrary content. The message-only sibling of ConfirmDialog; kept apart because a message sizes to its text while a form sizes to its fields
      EditUrlDialog.qml     Re-point a subscription at a different URL. Reports through urlAccepted rather than calling the controller
      FilterDialog.qml      Set or clear a feed's filter. A filter is one string of terms joined by AND, unreadable to edit as text, so it splits into a togglable row per term with a field for adding one more, then rejoins whatever is still active
      FeedDiscovery.qml     Feed discovery drawer, composition only: holds the search state, the selection and the error text, wires the search bar to the results and both to the controller, then owns the bulk-subscribe confirmations. The two halves name nothing outside themselves, so every crossing (focus handover, search, cap, subscribe) passes through here as a signal
      DiscoverySearchBar.qml   Heading, query field, result cap and the Search/Cancel button, with the busy row underneath. Owns the first half of the panel's focus ring; focusFirst() and focusLast() are the entry points and focusForwardRequested is the exit, because the Search button is only a tab stop while there is something to search for
      DiscoveryQueryField.qml  The query field with its topic autocomplete: popup, debounce timer and the suggestion fetch as one unit. The suggestions are Wikipedia's OpenSearch endpoint, asked over XHR from two characters, debounced at 250ms and capped at ten, with the previous request aborted. This is one of the two outbound calls the UI layer makes for itself; the other is `MediaPlayerPanel`'s YouTube embed. Dismisses its own popup before emitting searchRequested, so no caller knows the popup exists. Escape closes the popup, then cancels a running search, then closes the panel
      DiscoveryResults.qml     The error, empty and idle placeholders plus the results list and its header. Owns the second half of the focus ring, handing back through focusForwardRequested and focusBackwardRequested; the bulk-subscribe button is a conditional stop, so entering asks rather than assumes
      CandidateRow.qml      One discovery search result, used as the results ListView delegate. Six `required` properties named for FeedCandidateModel's roles, so the view binds them by name; `theme` and `selected` come from the caller and the two actions are signals (toggleRequested, subscribeRequested). The candidate* properties stay on the root because the ListView's Space and Return handlers read them off currentItem
      ToastBar.qml          Transient confirmation strip: fades in, holds, fades out. One `show(message)` call; anchors nothing itself, so the caller places it
      UrlListDialog.qml     Modal dialog: heading over a scrollable list of feed URLs, with the caller's buttons reparented into the footer row. Carries the chrome the two bulk dialogs in FeedDiscovery.qml duplicated. Wears an AutoScroller, which does nothing until the list is longer than the dialog
      AutoScroller.qml      Attach one to any Flickable and long content reads itself: holds still, descends slowly, holds at the end, rewinds fast, repeats. The pace constants live here and no caller overrides one. Any hand on the surface suspends it and it resumes in place; `active` freezes it where it stands rather than stopping it
      StyledButton.qml      Shared Button: required `theme` property, transparent fill, amber border on hover and a 2px amber border on activeFocus, focusPolicy Qt.TabFocus
      AboutDialog.qml       About dialog (keyboard: Enter/Escape closes)
      LicenceDialog.qml     Licence dialog (keyboard: scroll text, Tab to Close, Enter/Escape closes). Wears an AutoScroller, since a licence always overflows and nobody should have to wheel through one

  main.py                   Composition root (excluded from coverage)
  version.py                Application identity; reads the root VERSION file with a 0.0.0-dev fallback

installer/                  The bespoke per-user Windows installer, shipped as MeridianSetup.exe. Decomposed the same way as the application, which is what let half of it join the coverage gate
  app.py, cli.py            Entry point and argument parsing
  constants.py              Install paths, the registry key and the application identity
  ops/                      Everything that touches the machine, free of Qt and inside the coverage gate: payload extraction, install, repair, uninstall, shortcut creation, running-app detection, whether to start the application once an operation has finished, the one progress reporter every operation shares, the typed error hierarchy
  state/                    The install state: the registry read and write, the model it produces and version comparison through `packaging`
  ui/                       The PySide6 installer window, its themes, licence dialogs, worker thread, the sequencing that starts the application then closes the installer and the operation dispatch (the one Qt-free part, gated with `ops`)
  shared/                   Logging setup and resource resolution under PyInstaller's `sys._MEIPASS`
  payload/                  Where `build_payload.py` stages the zipped application and its manifest

examples/
  feeds_sample.json         A neutral starter reading list, importable from the header's Import button

Root delivery scripts (exempt from the size cap, never from the formatters):
  buildexe.py, buildinstaller.py, builddmg.py, build_flatpak.sh, cleanup_flatpak.sh
  build_resources.py        The single list of resources every delivery script bundles, so a missing licence text cannot reach a build
  create_icons.py, create_splash.py, stamp_version.py

tests/
  structural/
    test_boundaries.py      AST-based layer boundary enforcement + module size limits + black and flake8
    test_delivery_resources.py  Every delivery script bundles the same licence texts, because `main.py` degrades to "Licence text unavailable." rather than raising, so an omission ships silently
  domain/                   Unit tests for domain services and entities
  application/              Unit tests for application services (fakes for infrastructure)
  infrastructure/
    parser/                 Parser tests for RSS, Atom, podcast, mfeed and the platform dispatcher
    test_repositories.py    SQLite repository integration tests
    test_http_fetcher.py    Conditional GET, redirects, backoff and the document cap, with `respx`
    test_feedsearch_fetcher.py  The discovery client against recorded Feedly responses
    test_scheduler.py       The poll loop, its tick and per-feed backoff
    test_mmsp_conformance.py    The Section 5.7 version rule, asserted against the published schema where MMSP-Spec is checked out beside this repository
  test_installer_*.py       The installer operations: install, deploy edges, repair, uninstall, shortcuts, running-app detection and the payload
  ui/
    conftest.py             The session QApplication; Qt is never mocked
    bridge_dtos.py          DTO builders and the service stand-ins the bridge tests share
    window_stub.py          A hand-written controller with exactly the surface main.qml reaches for, the feed and item builders that fill it, the palette a component under test takes as its theme, plus the loader that builds the real window against it
    test_bridge_models.py   The three QAbstractListModels, asserted by role number
    test_bridge_subscriptions.py  AppController: add, remove, re-point, filter
    test_bridge_import_export.py  AppController: the JSON round trip of the feed list
    test_bridge_items.py    AppController: read state and new-item arrival
    test_bridge_sorting.py  AppController: the feed and item sort settings
    test_bridge_discovery.py      AppController: search lifecycle on the background loop
    test_qml_compiles.py    Every QML file compiles
    test_installer_dispatch.py  The installer's Qt-free operation dispatch
    test_url_list_dialog.py, test_candidate_row.py, test_discovery_query_field.py
                            The extracted QML components, each built with no caller in scope
    test_discovery_focus_ring.py, test_main_window_focus_ring.py, test_subscription_manager.py, test_feed_reader.py
                            The keyboard rings and the panel joins, driven with real key events through a real window
    test_row_activation.py  Clicking a feed row and an item row with a real mouse press, which the keyboard tests cannot cover because they never enter the delegate
    test_auto_scroller.py   The self-reading cycle: its holds, its two paces, the manual suspend and the freeze, driven by calling the tick rather than waiting on the clock
    test_dialog_auto_scroll.py  That the licence dialog and the URL list actually wear it, since a component wired to nothing passes every test above
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
5. User selects item: `ItemListPanel` reports it through `itemSelected`; `FeedReader` loads the detail pane with it and calls `AppController.markRead(id)`
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

**HTML rendering**: `TextArea { textFormat: Text.RichText }` in QML. Plain-text descriptions (no HTML tags) are escaped and converted to `<br/>`-separated HTML before display. Raw HTML from `content:encoded` is passed through directly. **Nothing sanitises it, deliberately.** What protects the reader is Qt's rich-text engine, which accepts only a small HTML subset and executes no script, rather than a sanitising pass. `bleach` sat in the dependency set for that pass and was imported nowhere, so it was dropped; adding a sanitiser back is a decision to make on its own terms, not a dependency to leave lying about.

**Transport policy**: `Feed.__post_init__` accepts `http://` and `https://` and rejects every other scheme, so an imported or discovered plain-HTTP feed still loads. Everything downstream of that is stricter: the Add Subscription field in `SubscriptionManager.qml` only enables Subscribe for an `https://` URL, `HttpFetcher` discards a non-HTTPS redirect target; the parsers drop non-HTTPS media, enclosure and thumbnail URLs.

**QML component extraction**: the front end is decomposed the way QML itself offers, into sibling `.qml` files, with the composing file holding the shared state and every crossing between panels. Two things govern it, both learned the expensive way. An extracted component still resolves the ids of the file that created it, because the instance's context chains to its creation context, so an outer-scope read survives extraction silently and only fails once the component is used somewhere else: a new component declares every input it takes; its test builds it with no caller in scope. Separately, a `Repeater`'s delegates belong to its `QQmlDelegateModel` rather than to the item they are laid out in, so `findChild` cannot see them at all: a test that needs one walks the visual tree through `childItems()`, starting at the dialog's own `contentItem` where the content is in the overlay.

A third rule governs delegates specifically; it cost a working feature to learn. **Declaring any `required` property on a delegate stops the view injecting the model's context properties into it,** so `index`, `model` and `modelData` are then not stale but absent. Reading an absent `index` throws a `ReferenceError`, which aborts the handler at that line and silently skips everything after it: both row delegates set `currentIndex = index` before reporting outwards, so clicking a feed or an item did nothing at all while every test stayed green. A delegate that needs its position declares `required property int index` alongside its roles; the mouse path is asserted rather than assumed, because the keyboard path reports through the view and never enters the delegate.

**Self-reading surfaces**: content a reader has to get through rather than act on takes itself down the page, so a licence can be read without touching the wheel. `AutoScroller.qml` is that cycle and it carries the pace for the whole application: one surface with its own timing would make the application feel like two. Exactly two surfaces wear it; the boundary is what the surface is for. The licence dialog is text to be read and always overflows. The URL list is a list to be checked before confirming a bulk action; it only moves when sixty URLs do not fit. Everything else is declined on purpose: the reader's article pane is where the reader sets their own pace, the feed, item, discovery and subscription lists are surfaces to act on rather than read through; the About dialog has no scrollable surface at all. Two adaptations were forced by Qt Quick rather than chosen: a dialog that focuses something inside its own surface as it opens must not be read as a reader taking hold; a surface that is frozen takes no input at all, because a closing popup returns its view to the top and that would otherwise corrupt the phase the freeze exists to preserve.

**Keyboard navigation**: Qt Quick Controls `Button` handles Space natively but not Enter/Return. Every `StyledButton` instance and interactive `Rectangle` in the QML layer has an explicit `Keys.onReturnPressed` handler. Two bare `Button` instances do not, so Enter does nothing on them: `markAllReadBtn` in `ItemListPanel.qml` and `playPauseBtn` in `MediaPlayerPanel.qml`. Both are in the focus ring and both answer to Space. That is a defect rather than a decision, recorded here so it is not read as the pattern. Dialog footer buttons are given IDs and Left/Right key handlers to allow lateral navigation between Cancel and OK without leaving the keyboard. Qt6 TextField intercepts Tab internally; tab-chain control uses `activeFocusOnTab` on surrounding items rather than `KeyNavigation.tab` on the field itself.

Tab wrap-around uses explicit `forceActiveFocus()` with `event.accepted = true` on every boundary. `KeyNavigation.tab` and `setFocus()` both fail across QML `FocusScope` boundaries; only `forceActiveFocus()` works. Critical invariant: `ScrollView`'s `contentItem` is a `Flickable`, which is a `FocusScope`, so any focusable control inside a `ScrollView` is trapped and Tab can never escape it. Controls that must participate in the outer Tab chain must be placed outside the `ScrollView` in the component tree.

**Theme persistence**: dark/light mode stored via `Qt.labs.settings` with `category: "Theme"`, property `isDark: true`. Reads on startup; written on toggle. Uses same `QSettings` backend as volume (category `"Player"`); no conflict since categories are separate.

## Quality Enforcement

- `--cov-fail-under=100`: 100% branch coverage required, over `installer/ops` as well as the `meridian` package
- Structural AST tests enforce layer boundaries; the 400-line size limit is enforced over QML, the test tree and the installer as well as the Python package, with an explicit allowlist that can only shrink and is now empty; the danger band below the cap is enforced alongside it
- `black` and `flake8` run as in-suite assertions, so unformatted or lint-failing code is a test failure
- `POLL_FLOOR_SECONDS = 300` is the single source of truth for the polling floor; no magic numbers in logic

## Licence

Meridian is dual-licensed, split by component (see `LICENSE` for the map):

- Model (`domain`, `application`, `infrastructure`, `main.py`, `version.py`, build scripts, tests): Apache-2.0 (matches the MMSP specification ecosystem).
- User interface (`ui`) only: LGPL-3.0-or-later, to align with Qt's licensing.

Third-party runtime dependencies:

PySide6: LGPL-3.0 (dynamically linked; compliant by default install).
SQLAlchemy: MIT.
httpx: BSD-3-Clause.
defusedxml: PSF.
python-dateutil: Apache-2.0 / BSD-3-Clause.
