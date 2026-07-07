# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Workflow feedback API routes."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.auth import AuthContext
from app.database.models import FeedbackRating, WorkflowFeedback
from app.database.session import get_db_session
from app.dependencies import get_current_user
from app.services.workflow_feedback import WorkflowFeedbackService
from app.services.workflows import WorkflowService

router = APIRouter(
    prefix="/workflows",
    tags=["workflow-feedback"],
    responses={404: {"description": "Not found"}},
)


class CreateWorkflowFeedbackRequest(BaseModel):
    """Request body for appending workflow feedback."""

    field_path: str = Field(min_length=1)
    rating: FeedbackRating
    comment: str | None = None
    user_id: str | None = None


@router.post(
    "/{workflow_id}/feedback",
    response_model=WorkflowFeedback,
    response_model_exclude={"id", "workflow_id"},
)
async def create_feedback(
    workflow_id: str,
    body: CreateWorkflowFeedbackRequest,
    auth: AuthContext = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """Append tenant-scoped feedback for a workflow result field."""
    workflow = WorkflowService(session).get_tenant_workflow(auth, workflow_id)
    if workflow.id is None:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return WorkflowFeedbackService(session).create(
        workflow_id=workflow.id,
        tenant_id=auth.tenant_id,
        user_id=body.user_id,
        field_path=body.field_path,
        rating=body.rating,
        comment=body.comment,
    )
