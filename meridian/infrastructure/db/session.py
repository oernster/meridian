from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from meridian.infrastructure.db.orm_models import Base
from meridian.version import data_folder

_DEFAULT_DB_PATH = data_folder() / "meridian.db"


def build_engine(db_path: Path = _DEFAULT_DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{db_path}"
    engine = create_engine(url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return engine


def build_session_factory(db_path: Path = _DEFAULT_DB_PATH) -> sessionmaker[Session]:
    engine = build_engine(db_path)
    return sessionmaker(engine, expire_on_commit=False)
