# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, event
from sqlmodel import Session, create_engine

from ..config import get_settings

_engine: Engine | None = None


def _set_sqlite_pragmas(dbapi_connection, connection_record):
    """Enable foreign keys, WAL journaling, and a busy timeout on connect."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def init_engine() -> Engine:
    """Create and store the global SQLAlchemy engine."""
    global _engine
    settings = get_settings()
    engine = create_engine(settings.database_url)
    if engine.dialect.name == "sqlite":
        event.listen(engine, "connect", _set_sqlite_pragmas)
    _engine = engine
    return _engine


def dispose_engine() -> None:
    """Dispose the global engine and release connections."""
    global _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None


def get_engine() -> Engine:
    """Return the global engine, initializing it if needed."""
    if _engine is None:
        raise RuntimeError("Engine is not initialized!")
    return _engine


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Provide a database session context manager."""
    with Session(get_engine()) as session:
        yield session


def get_db_session() -> Generator[Session, None, None]:
    """Make a database session for FastAPI dependencies."""
    with get_session() as session:
        yield session
