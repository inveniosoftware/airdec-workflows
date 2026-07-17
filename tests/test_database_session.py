# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Tests for engine initialization, focused on the SQLite pragma setup."""

import os

from app.config import get_settings
from app.database.session import dispose_engine, init_engine


def test_init_engine_sets_sqlite_pragmas(tmp_path):
    """SQLite connections get foreign keys, WAL journaling, and a busy timeout."""
    db_path = tmp_path / "pragma_test.db"
    os.environ["DB_DIALECT"] = "sqlite"
    os.environ["DB_PATH"] = str(db_path)
    get_settings.cache_clear()
    try:
        engine = init_engine()
        with engine.connect() as conn:
            foreign_keys = conn.exec_driver_sql("PRAGMA foreign_keys").scalar()
            journal_mode = conn.exec_driver_sql("PRAGMA journal_mode").scalar()
            busy_timeout = conn.exec_driver_sql("PRAGMA busy_timeout").scalar()
        assert foreign_keys == 1
        assert journal_mode == "wal"
        assert busy_timeout == 5000
    finally:
        dispose_engine()
        del os.environ["DB_DIALECT"]
        del os.environ["DB_PATH"]
        get_settings.cache_clear()
