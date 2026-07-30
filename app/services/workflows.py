# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Workflow database operations and access checks."""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select
from temporalio.common import RetryPolicy

from app.auth import AuthContext
from app.database.models import Workflow, WorkflowStatus
from app.temporal import get_temporal_client
from app.workflows.registry import get_workflow_spec
from app.workflows.specs import WorkflowContext

logger = logging.getLogger(__name__)


class WorkflowService:
    """Service for workflows."""

    def __init__(self, session: Session):
        """Create a workflow service for one database session."""
        self.session = session

    def get_by_public_id(self, workflow_id: str) -> Workflow:
        """Get a workflow by public ID."""
        try:
            return self.session.exec(
                select(Workflow).where(Workflow.public_id == workflow_id)
            ).one()
        except SQLAlchemyError:
            logger.exception("Error reading workflow")
            raise HTTPException(status_code=404, detail="Workflow not found")

    def verify_workflow_access(self, auth: AuthContext, workflow_id: str) -> None:
        """Verify that the JWT payload allows access to the requested workflow."""
        if (
            auth.workflow_id
            and auth.workflow_id != "*"
            and auth.workflow_id != workflow_id
        ):
            raise HTTPException(
                status_code=403,
                detail="Not authorized for this workflow",
            )

    def verify_tenant_owns_workflow(
        self,
        auth: AuthContext,
        workflow: Workflow,
    ) -> None:
        """Verify the authenticated tenant owns the workflow."""
        if workflow.tenant_id != auth.tenant_id:
            raise HTTPException(
                status_code=403,
                detail="Not authorized to access this workflow",
            )

    def get_authorized_workflow(
        self,
        auth: AuthContext,
        workflow_id: str,
    ) -> Workflow:
        """Get a workflow after enforcing workflow-scoped and tenant access."""
        self.verify_workflow_access(auth, workflow_id)
        workflow = self.get_by_public_id(workflow_id)
        self.verify_tenant_owns_workflow(auth, workflow)
        return workflow

    def get_tenant_workflow(
        self,
        auth: AuthContext,
        workflow_id: str,
    ) -> Workflow:
        """Get a workflow after enforcing tenant access only."""
        workflow = self.get_by_public_id(workflow_id)
        self.verify_tenant_owns_workflow(auth, workflow)
        return workflow

    async def create(
        self,
        *,
        workflow_type: str,
        params: dict[str, Any],
        tenant_id: str,
        user_id: str | None = None,
        start: bool = True,
    ) -> Workflow:
        """Create a workflow record and optionally start its Temporal workflow.

        The insert commits before the Temporal call so no database transaction
        stays open while the external request is in flight.
        """
        try:
            spec = get_workflow_spec(workflow_type)
        except KeyError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

        try:
            workflow_params = spec.params_model.model_validate(params)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=exc.errors()) from exc

        workflow = Workflow(
            workflow_type=workflow_type,
            status=WorkflowStatus.PROCESSING,
            params=workflow_params.model_dump(mode="json"),
            tenant_id=tenant_id,
            user_id=user_id,
        )
        workflow_id = workflow.public_id

        try:
            self.session.add(workflow)
            self.session.commit()
        except SQLAlchemyError:
            logger.exception("Error creating workflow")
            raise HTTPException(status_code=500, detail="Could not create workflow")

        if start:
            try:
                await get_temporal_client().start_workflow(
                    spec.workflow_cls.run,
                    args=[
                        WorkflowContext(
                            workflow_id=workflow_id,
                            tenant_id=tenant_id,
                            user_id=user_id,
                        ),
                        workflow_params,
                    ],
                    id=f"{spec.id_prefix}-{workflow_id}",
                    task_queue=spec.task_queue,
                    retry_policy=RetryPolicy(maximum_attempts=1),
                )
            except Exception:
                logger.exception("Error starting Temporal workflow")
                self._mark_workflow_error(workflow)
                raise HTTPException(status_code=500, detail="Could not start workflow")

        return workflow

    def _mark_workflow_error(self, workflow: Workflow) -> None:
        """Record a failed Temporal start on the workflow row."""
        try:
            workflow.status = WorkflowStatus.ERROR
            workflow.end_time = datetime.now(UTC)
            self.session.add(workflow)
            self.session.commit()
        except SQLAlchemyError:
            logger.exception("Could not mark workflow as errored")
