# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Workflow API routes with tenant-scoped access control."""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select
from temporalio.client import Client
from temporalio.common import RetryPolicy

from app.auth import AuthContext, decode_access_token
from app.database.models import Workflow, WorkflowStatus
from app.database.session import get_db_session
from app.dependencies import get_current_user
from app.services.workflows import WorkflowService
from app.workflows.registry import get_workflow_spec
from app.workflows.specs import WorkflowContext

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


def _get_temporal_client(request: Request) -> Client:
    return request.app.state.temporal_client


@router.get(
    "/",
    response_model=list[Workflow],
    response_model_exclude={"__all__": {"id"}},
)
async def read_all(
    auth: AuthContext = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """List all workflows for the authenticated tenant."""
    return WorkflowService(session).list_for_tenant(auth.tenant_id)


@router.post(
    "/",
    response_model=Workflow,
    response_model_exclude={"id"},
)
async def create(
    body: CreateWorkflowRequest,
    request: Request,
    auth: AuthContext = Depends(get_current_user),
    session: Session = Depends(get_db_session),
):
    """Create a new workflow and start the Temporal workflow."""
    try:
        spec = get_workflow_spec(body.workflow_type)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    try:
        params = spec.params_model.model_validate(body.params)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    workflow = Workflow(
        workflow_type=body.workflow_type,
        status=WorkflowStatus.PROCESSING,
        params=params.model_dump(mode="json"),
        tenant_id=auth.tenant_id,
        user_id=body.user_id,
    )

    try:
        session.add(workflow)
        session.commit()
        workflow_id = workflow.public_id
    except SQLAlchemyError:
        logger.exception("Error creating workflow")
        raise HTTPException(status_code=500, detail="Could not create workflow")

    try:
        client = _get_temporal_client(request)
        await client.start_workflow(
            spec.workflow_cls.run,
            args=[
                WorkflowContext(
                    workflow_id=workflow_id,
                    tenant_id=auth.tenant_id,
                    user_id=workflow.user_id,
                ),
                params,
            ],
            id=f"{spec.id_prefix}-{workflow_id}",
            task_queue=spec.task_queue,
            retry_policy=RetryPolicy(maximum_attempts=1),
        )
    except Exception:
        logger.exception("Error starting Temporal workflow")
        try:
            workflow.status = WorkflowStatus.ERROR
            workflow.end_time = datetime.now(UTC)
            session.commit()
        except SQLAlchemyError:
            pass
        raise HTTPException(status_code=500, detail="Could not start workflow")

    return workflow


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
