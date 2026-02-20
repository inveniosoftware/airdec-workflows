import os
from collections.abc import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session


DRIVER = "psycopg"

PGUSER = os.getenv("PGUSER", "postgres")
PGPASSWORD = os.getenv("PGPASSWORD", "postgres")
PGHOST = os.getenv("PGHOST", "localhost")
PGPORT = os.getenv("PGPORT", "5433")
PGDATABASE = os.getenv("PGDATABASE", "airdec")

CONN_STRING = (
    f"postgresql+{DRIVER}://{PGUSER}:{PGPASSWORD}@{PGHOST}:{PGPORT}/{PGDATABASE}"
)

_engine: Engine | None = None


def init_engine() -> Engine:
    global _engine
    _engine = create_engine(CONN_STRING)
    return _engine


def dispose_engine() -> None:
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


def get_engine() -> Engine:
    if _engine is None:
        return init_engine()
    return _engine


def get_session() -> Generator[Session, None, None]:
    with Session(get_engine()) as session:
        yield session
