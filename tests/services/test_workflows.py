# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Tests for workflow service helpers."""

import pytest
from fastapi import HTTPException

from app.auth import AuthContext
from app.database.models import Workflow, WorkflowStatus
from app.services.workflows import WorkflowService


def _workflow(tenant_id: str, url: str = "https://example.com/test.pdf") -> Workflow:
    return Workflow(
        workflow_type="extract_metadata",
        status=WorkflowStatus.SUCCESS,
        params={"url": url},
        tenant_id=tenant_id,
    )


def test_get_by_public_id_returns_workflow(db_session):
    """Workflow lookup returns the public-id match."""
    workflow = _workflow("tenant-a")
    db_session.add(workflow)
    db_session.commit()
    db_session.refresh(workflow)

    found = WorkflowService(db_session).get_by_public_id(workflow.public_id)

    assert found.id == workflow.id


def test_get_by_public_id_raises_404_when_missing(db_session):
    """Missing workflow lookup raises the route-friendly 404."""
    with pytest.raises(HTTPException) as exc_info:
        WorkflowService(db_session).get_by_public_id("missing-workflow")

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Workflow not found"


def test_get_authorized_workflow_rejects_workflow_scope_mismatch(db_session):
    """Workflow-scoped access is enforced for workflow reads and streams."""
    workflow = _workflow("tenant-a")
    db_session.add(workflow)
    db_session.commit()
    db_session.refresh(workflow)

    auth = AuthContext(tenant_id="tenant-a", workflow_id="other-workflow")

    with pytest.raises(HTTPException) as exc_info:
        WorkflowService(db_session).get_authorized_workflow(
            auth,
            workflow.public_id,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Not authorized for this workflow"


def test_get_authorized_workflow_rejects_cross_tenant_access(db_session):
    """Tenant ownership is enforced after workflow lookup."""
    workflow = _workflow("tenant-a")
    db_session.add(workflow)
    db_session.commit()
    db_session.refresh(workflow)

    auth = AuthContext(tenant_id="tenant-b")

    with pytest.raises(HTTPException) as exc_info:
        WorkflowService(db_session).get_authorized_workflow(
            auth,
            workflow.public_id,
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Not authorized to access this workflow"


def test_get_tenant_workflow_ignores_workflow_scope(db_session):
    """Tenant-only lookups do not enforce workflow-scoped JWT claims."""
    workflow = _workflow("tenant-a")
    db_session.add(workflow)
    db_session.commit()
    db_session.refresh(workflow)

    auth = AuthContext(tenant_id="tenant-a", workflow_id="other-workflow")

    found = WorkflowService(db_session).get_tenant_workflow(auth, workflow.public_id)

    assert found.id == workflow.id
