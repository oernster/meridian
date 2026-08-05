# <img width="128" height="128" alt="meridian" src="https://github.com/user-attachments/assets/e2ef5ef9-1ed9-4faf-9a8f-4af483072e59" /> Meridian

Meridian is a desktop feed reader and subscription manager: the reference client for the [MMSP](https://ernster.dev/MMSP-Spec/) protocol and its MFEED JSON feed format. It also reads RSS, Atom, podcast and YouTube channel feeds, so one application covers everything you already subscribe to while MFEED adoption grows.

Everything stays on the machine it runs on. Subscriptions and read state live in a local SQLite database; there is no account, no cloud and no server component.

<img width="1273" height="824" alt="Meridian main window" src="https://github.com/user-attachments/assets/c6565996-d66f-4df7-a26b-5691c2ee32f4" />

## Who it is for

- People who want a calm three-pane reader on Windows, macOS or Linux, with no engagement ranking and no telemetry.
- Keyboard-first users. Every control is reachable and operable without a mouse, including inside every drawer and dialog.
- MMSP publishers and implementers who need a working client to read an MFEED against.
- Anyone who wants their reading list to be a file they own, exportable and importable as plain JSON.

## Who it is not for

- People who want their subscriptions and read state synchronised between machines or to a phone. Meridian is single-device by design; JSON export and import is the migration path, not live sync.
- People who want a hosted or web-based reader. There is no server component and none is planned.
- People who expect to type a plain-HTTP feed URL into the app. The Add Subscription field only accepts `https://`; redirect targets have to be HTTPS; parsers drop non-HTTPS media and thumbnail URLs.
- People who want push notifications on new items. MMSP is pull-only, so the scheduler is silent and new items appear on the next poll tick or view.

## Capabilities

- Subscribe to MFEED, RSS 2.0 and 1.0, Atom 1.0, podcast RSS and YouTube channel feeds.
- Feed discovery by topic through feedsearch.dev: search, preview candidates and subscribe individually or in bulk, with category autocomplete and a result-cap selector.
- Per-feed filter expressions using the MMSP Appendix A ABNF grammar. The filter dialog shows existing terms as toggleable rows, so common cases need no syntax knowledge.
- Background polling with conditional GET (ETag and Last-Modified), rate-limit backoff and a 300 second poll floor.
- Bulk feed management with select-all checkboxes; in-place list removal preserves scroll position.
- Import and export subscriptions as JSON.
- Catppuccin Mocha and Latte themes with a single toggle; the preference persists across restarts.
- Full-text `content:encoded` rendering for article feeds, plus a built-in media player for podcast and video items.
- Full keyboard navigation: Tab and Shift+Tab wrap cleanly end to end, Enter and Space activate the focused control, Left and Right move between buttons and dialog footer actions, Escape closes drawers and dialogs; an amber focus ring marks the focused control everywhere.

## Stack

| Layer | Technology | Purpose |
|---|---|---|
| Language | Python 3.11+ | 3.12 or later recommended |
| UI | PySide6 (Qt Quick / QML) | Native desktop front end and media playback |
| Persistence | SQLAlchemy over SQLite | Subscriptions, items and polling state |
| Networking | httpx | Async feed polling and discovery |
| Parsing | defusedxml, python-dateutil | Safe XML parsing and RSS / Atom date handling |
| Rendering | bleach | HTML sanitisation before display |
| Tests | pytest, pytest-qt, pytest-cov, respx | Suite, Qt fixtures, coverage gate and HTTP mocking |
| Packaging | PyInstaller, Flatpak | Windows installer, macOS DMG, Linux Flatpak |

## Install and run

### Pre-built releases

Download the installer for your platform from the [Releases page](https://github.com/oernster/meridian/releases).

### Run from source

```bash
# 1. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # macOS / Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python -m meridian.main
```

As an installed package:

```bash
pip install -e .
meridian
```

The database is created automatically at first launch in the platform user-data directory.

## Sample feeds

`examples/feeds_sample.json` holds a small neutral set of RSS, Atom and MFEED subscriptions ready to import. To load them, launch Meridian, open **File > Import Feeds...** and select `feeds_sample.json` from the `examples/` directory. All feeds are added and begin polling immediately.

## Tests

```bash
pip install -r requirements-dev.txt
pytest
```

Branch coverage is gated at 100%; `black` and `flake8` run as in-suite assertions, so a formatting or lint failure is a test failure. The gated run prints the coverage table last and emits no "N passed" line, so read the exit code: `0` means the suite passed and the gate was met.

## Build

```bash
python buildexe.py           # Windows: standalone application directory
python buildinstaller.py     # Windows: MeridianSetup.exe (per-user installer)
python builddmg.py           # macOS: signed .app and DMG (needs Xcode command-line tools)
./build_flatpak.sh           # Linux: meridian.flatpak (needs flatpak and flatpak-builder)
./cleanup_flatpak.sh         # Linux: uninstall and remove all build artefacts
```

Installing and running the Flatpak bundle:

```bash
flatpak install --user meridian.flatpak
flatpak run uk.codecrafter.Meridian
```

The root `VERSION` file is the single source of truth for the version. `meridian/version.py` reads it, every other module and build script imports `__version__` from there; `stamp_version.py` refreshes the copies in the `docs/` site.

## Further reading

- [DEVELOPMENT.md](DEVELOPMENT.md): Python version policy, dev tooling and how to run the suite.
- [ARCHITECTURE.md](ARCHITECTURE.md): the invariants, the tests that enforce them and the full project structure.
- [CONTRIBUTING.md](CONTRIBUTING.md): the standards and design boundaries a change has to meet.
- [TECH_DEBT.md](TECH_DEBT.md): what is still open, what is deliberately left and what only looks like debt.

<p align="center">
  <img src="docs/architecture.svg" alt="Meridian clean architecture: UI, Application, Domain, Infrastructure, with dependencies pointing inward to a pure Domain" width="860">
</p>

## Licence

Meridian is dual-licensed, split by component:

- **Model** (`meridian/domain`, `meridian/application`, `meridian/infrastructure`, `main.py`, `version.py`, build scripts and tests): Apache-2.0, aligning with the MMSP specification ecosystem. See [LICENSE-APACHE-2.0.txt](LICENSE-APACHE-2.0.txt).
- **User interface** (`meridian/ui`) only: LGPL-3.0-or-later, to align with Qt's licensing. See [LICENSE-LGPL-3.0.txt](LICENSE-LGPL-3.0.txt).

See [LICENSE](LICENSE) for the component map and [ARCHITECTURE.md](ARCHITECTURE.md) for third-party licence notes.
