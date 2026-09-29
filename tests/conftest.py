"""Session fixtures shared by every suite, plus the platform the suite runs on.

The offscreen platform is forced here, before any test module can import Qt,
so a bare `pytest` never puts a window on the desktop. It is forced rather than
defaulted: a `QT_QPA_PLATFORM` left in the shell from running the application
would otherwise win and every UI test would open a real window.
"""

import os
from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from meridian.infrastructure.db.session import build_session_factory

# None of the imports above reaches Qt, so this still runs before any does.
os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def tmp_db_path(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("db") / "test.db"


@pytest.fixture(scope="session")
def session_factory(tmp_db_path) -> sessionmaker:
    factory = build_session_factory(tmp_db_path)
    yield factory
    factory.kw["bind"].dispose()
