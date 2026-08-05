# Development Guide

## Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| Python | 3.11 | `match` statements, `tomllib`, `slots=True` on dataclasses |
| pip | 23+ | |
| Qt | 6.7 (via PySide6) | installed automatically by pip |

Python 3.12+ is recommended. Python 3.10 and below are not supported.

## Setup

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux

pip install -r requirements-dev.txt
```

`requirements-dev.txt` installs everything in `requirements.txt` plus the test, lint and packaging tooling.

## Runtime Dependencies (`requirements.txt`)

| Package | Version | Purpose |
|---------|---------|---------|
| PySide6 | >=6.7 | Qt Quick UI, QML engine, media playback |
| sqlalchemy | >=2.0 | ORM and SQLite persistence |
| httpx | >=0.27 | Async HTTP client for feed polling |
| defusedxml | >=0.7 | Safe XML parsing (feed content) |
| python-dateutil | >=2.9 | RSS / Atom date parsing |
| bleach | >=6.1 | HTML sanitisation before rendering |

## Dev Dependencies (additional in `requirements-dev.txt`)

| Package | Purpose |
|---------|---------|
| pytest >=8.0 | Test runner |
| pytest-asyncio >=0.23 | Async test support |
| pytest-cov >=5.0 | Coverage enforcement |
| pytest-qt >=4.4 | Qt/QML test fixtures (`qapp`) |
| respx >=0.21 | httpx request mocking |
| black >=24.0 | Code formatter |
| flake8 >=7.0 | Linter |
| pyinstaller >=6.10 | Frozen application builds |
| pyinstaller-hooks-contrib >=2024.0 | Third-party PyInstaller hooks |
| psutil >=5.9 | Running-app detection in the installer |
| platformdirs >=4.0 | Per-user install and data paths |
| packaging >=24.0 | Version comparison for installer upgrade and repair |
| pywin32 >=311 (Windows only) | Shortcut creation and registry writes |

## Running Tests

```bash
pytest
```

Coverage is enforced at 100% (`--cov-fail-under=100` in `pyproject.toml`). A failing test or a missed branch is a build failure. `black` and `flake8` also run as in-suite assertions, so unformatted or lint-failing code fails the suite too.

The gated run prints the coverage table last and emits no "N passed" line, so read the exit code rather than grepping the output: `0` means the suite passed and the gate was met.

```bash
# Run a specific test file
pytest tests/ui/test_bridge.py -v

# Run with coverage report
pytest --cov-report=html
```

## Formatting and Linting

```bash
black meridian tests
flake8 meridian tests
```

## Running the App

```bash
python -m meridian.main
```

The database is created automatically at first launch in the platform user-data directory.

## Project Entry Point

`meridian/main.py` is the composition root. It wires all dependencies (session factory, repositories, services, scheduler, QML engine) and is excluded from coverage measurement since it contains only wiring code with no testable logic.

## Versioning

The root `VERSION` file holds the only copy of the version string. Nothing else in the repository writes it:

- `meridian/version.py` reads `VERSION` (looking beside the package and then inside it) and exposes `__version__`, falling back to `0.0.0-dev` when neither location resolves.
- `pyproject.toml` takes its dynamic version from the same file.
- `builddmg.py` and `build_flatpak.sh` read it directly; every other consumer imports `__version__` from `meridian.version`.
- `buildexe.py`, `buildinstaller.py`, `builddmg.py` and `build_flatpak.sh` all ship `VERSION` alongside the application so the frozen build resolves it at runtime.
- `stamp_version.py` rewrites the `<!--VERSION-->` tokens in the `docs/` site, which cannot read the file at render time. It is idempotent and prints only the files it changed.

Bumping a release is therefore one edit to `VERSION` followed by `python stamp_version.py`.

## Building

```bash
python buildexe.py           # Windows: standalone application directory
python buildinstaller.py     # Windows: MeridianSetup.exe (per-user installer)
python builddmg.py           # macOS: signed .app and DMG (needs Xcode command-line tools)
./build_flatpak.sh           # Linux: meridian.flatpak (needs flatpak and flatpak-builder)
./cleanup_flatpak.sh         # Linux: uninstall and remove all build artefacts
```

`create_icons.py` regenerates the full icon set from the single master image and `create_splash.py` regenerates the splash screen; `buildexe.py` calls the latter for you.
