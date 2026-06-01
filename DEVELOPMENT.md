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

`requirements-dev.txt` installs everything in `requirements.txt` plus the test and lint tooling.

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

## Running Tests

```bash
pytest
```

Coverage is enforced at 100% (`--cov-fail-under=100` in `pyproject.toml`). A failing test or missed branch is a build failure.

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
