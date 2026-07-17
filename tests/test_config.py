# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Tests for database URL construction in application settings."""

import pytest

from app.config import Settings


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        pytest.param(
            {
                "db_url": "postgresql://custom:url@example.com/db",
                "db_dialect": "postgresql",
                "db_path": "ignored.db",
            },
            "postgresql://custom:url@example.com/db",
            id="db_url_overrides_everything",
        ),
        pytest.param({}, "sqlite:///orcha.db", id="sqlite_defaults"),
        pytest.param(
            {"db_path": "custom.db"}, "sqlite:///custom.db", id="sqlite_custom_path"
        ),
        pytest.param(
            {
                "db_dialect": "postgresql",
                "db_user": "orcha",
                "db_password": "secret",
                "db_host": "db.internal",
                "db_port": "5432",
                "db_name": "orcha",
            },
            "postgresql+psycopg://orcha:secret@db.internal:5432/orcha",
            id="postgresql_built_from_fields",
        ),
    ],
)
def test_database_url(kwargs, expected):
    """`database_url` resolves in the documented precedence order."""
    assert Settings(**kwargs).database_url == expected
