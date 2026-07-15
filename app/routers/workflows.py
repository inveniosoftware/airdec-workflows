# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Workflow API routes with tenant-scoped access control."""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.auth import AuthContext, decode_access_token
from app.database.models import Workflow
from app.database.session import get_db_session
from app.dependencies import get_current_user
from app.services.workflows import WorkflowService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/workflows",
    tags=["workflows"],
    responses={404: {"description": "Not found"}},
)

STREAM_DELAY = 1


class CreateWorkflowRequest(BaseModel):
    """Request body for creating a new workflow."""

    workflow_type: str
    params: dict[str, Any] = Field(default_factory=dict)
    user_id: str | None = None


@router.post(
    "/",
    response_model=Workflow,
    response_model_exclude={"id"},
)
async def create(
    body: CreateWorkflowRequest,
    auth: AuthContext = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """Create a new workflow and start the Temporal workflow."""
    return await WorkflowService(session).create(
        workflow_type=body.workflow_type,
        params=body.params,
        tenant_id=auth.tenant_id,
        user_id=body.user_id,
        start=True,
    )


@router.get(
    "/{workflow_id}",
    response_model=Workflow,
    response_model_exclude={"id"},
)
async def read(
    workflow_id: str,
    auth: AuthContext = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """Get a single workflow by its public ID."""
    return WorkflowService(session).get_authorized_workflow(auth, workflow_id)


async def workflow_event(request: Request, workflow_id: str):
    """Generate SSE events for workflow status updates."""
    while True:
        if await request.is_disconnected():
            break

        with Session(request.app.state.db_engine) as session:
            try:
                workflow = session.exec(
                    select(Workflow).where(Workflow.public_id == workflow_id)
                ).one()
                status = workflow.status.name

                yield f"data: {status}\n\n"

                if status == "ERROR" or status == "SUCCESS":
                    break
            except SQLAlchemyError:
                logger.exception("Error streaming workflow status")
                raise HTTPException(status_code=500)

        await asyncio.sleep(STREAM_DELAY)


@router.get("/{workflow_id}/stream")
async def stream(
    request: Request,
    workflow_id: str,
    token: str,
    session: Session = Depends(get_db_session),
):
    """Stream workflow status updates via SSE.

    Auth is via the `?token=` query parameter (required), since
    browser EventSource cannot set custom headers.
    """
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Missing token query parameter",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from app.dependencies import get_tenant_registry

    registry = get_tenant_registry(request)
    auth = decode_access_token(token, registry)

    WorkflowService(session).get_authorized_workflow(auth, workflow_id)

    return StreamingResponse(
        workflow_event(request, workflow_id), media_type="text/event-stream"
    )
