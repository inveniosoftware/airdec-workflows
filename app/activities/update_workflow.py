# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Activity to update workflow metadata in the database."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel
from sqlmodel import Session, select
from temporalio import activity
from temporalio.common import RetryPolicy

from app.database.models import Workflow, WorkflowStatus
from app.database.session import get_session

WORKFLOW_IDENTITY_FIELDS = {"id", "public_id", "tenant_id"}
UPDATE_WORKFLOW_RETRY_POLICY = RetryPolicy(maximum_attempts=1)


class WorkflowUpdateRequest(BaseModel):
    """Request to update a workflow record."""

    id: int | None = None
    public_id: str
    workflow_type: str | None = None
    params: dict[str, Any] | None = None
    status: WorkflowStatus | None = None
    tenant_id: str
    result: dict[str, Any] | None = None
    created: datetime | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None


def _get_owned_workflow(
    session: Session,
    workflow_id: str,
    tenant_id: str,
) -> Workflow:
    workflow = session.exec(
        select(Workflow).where(Workflow.public_id == workflow_id)
    ).one()
    # This check might be redundant given the tenant_id is part of the request
    # and the workflow is created with the tenant_id, it's a good safeguard
    # in case of manual calls.
    if workflow.tenant_id != tenant_id:
        raise ValueError("Tenant does not own this workflow")
    return workflow


@activity.defn
async def update_workflow(request: WorkflowUpdateRequest) -> None:
    """Persist workflow metadata updates to the database."""
    with get_session() as session:
        workflow = _get_owned_workflow(
            session,
            workflow_id=request.public_id,
            tenant_id=request.tenant_id,
        )

        updates = request.model_dump(exclude_none=True)
        for field_name, value in updates.items():
            if field_name not in WORKFLOW_IDENTITY_FIELDS:
                setattr(workflow, field_name, value)

        session.add(workflow)
        session.commit()
