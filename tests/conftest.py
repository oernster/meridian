from pathlib import Path

import pytest
from sqlalchemy.orm import sessionmaker

from meridian.infrastructure.db.session import build_session_factory


@pytest.fixture(scope="session")
def tmp_db_path(tmp_path_factory) -> Path:
    return tmp_path_factory.mktemp("db") / "test.db"


@pytest.fixture(scope="session")
def session_factory(tmp_db_path) -> sessionmaker:
    return build_session_factory(tmp_db_path)
