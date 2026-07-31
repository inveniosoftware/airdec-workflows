# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Tests for the tenant requests run as when authentication is off."""

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database.models import Workflow, WorkflowStatus
from app.main import app
from app.tenants import DEV_TENANT_ID, TenantRegistry


@pytest.fixture
def client(monkeypatch, mocker):
    """Serve the API in dev mode with mocked Temporal."""
    monkeypatch.setenv("DEV_MODE", "true")
    get_settings.cache_clear()
    mocker.patch("app.main.Client.connect", return_value=mocker.AsyncMock())
    mocker.patch("app.main.TenantRegistry.from_file", return_value=TenantRegistry())

    with TestClient(app) as test_client:
        yield test_client

    get_settings.cache_clear()


def test_requests_need_no_token(client):
    """A request without an Authorization header is served."""
    response = client.get("/")

    assert response.status_code == 200


def test_workflows_are_owned_by_the_dev_tenant(client, db_session):
    """The dev tenant reaches its own rows, so tenant scoping still applies."""
    mine = Workflow(
        workflow_type="extract_metadata",
        status=WorkflowStatus.SUCCESS,
        params={"url": "https://example.org/a.pdf"},
        tenant_id=DEV_TENANT_ID,
    )
    theirs = Workflow(
        workflow_type="extract_metadata",
        status=WorkflowStatus.SUCCESS,
        params={"url": "https://example.org/b.pdf"},
        tenant_id="zenodo",
    )
    db_session.add(mine)
    db_session.add(theirs)
    db_session.commit()
    db_session.refresh(mine)
    db_session.refresh(theirs)

    assert client.get(f"/workflows/{mine.public_id}").status_code == 200
    assert client.get(f"/workflows/{theirs.public_id}").status_code == 403


def test_created_workflows_record_the_dev_tenant(client, db_session, mocker):
    """A created workflow carries a real tenant id, never a null one."""
    mocker.patch(
        "app.routers.workflows._get_temporal_client",
        return_value=mocker.AsyncMock(),
    )

    response = client.post(
        "/workflows/",
        json={
            "workflow_type": "extract_metadata",
            "params": {"url": "https://example.org/a.pdf"},
        },
    )

    assert response.status_code == 200
    assert response.json()["tenant_id"] == DEV_TENANT_ID


@pytest.mark.parametrize(
    "env",
    [
        {"DEV_MODE": "false"},
        # An explicit AUTH_DISABLED wins over DEV_MODE, which is how the local
        # stack exercises real tenant tokens.
        {"DEV_MODE": "true", "AUTH_DISABLED": "false"},
    ],
)
def test_a_token_is_required_when_auth_is_on(monkeypatch, mocker, env):
    """Requests need a token unless authentication is off."""
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    get_settings.cache_clear()
    mocker.patch("app.main.Client.connect", return_value=mocker.AsyncMock())
    mocker.patch("app.main.TenantRegistry.from_file", return_value=TenantRegistry())

    with TestClient(app) as test_client:
        response = test_client.get("/")

    get_settings.cache_clear()
    assert response.status_code == 401
