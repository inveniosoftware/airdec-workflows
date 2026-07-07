# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Workflow database operations and access checks."""

import logging

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.auth import AuthContext
from app.database.models import Workflow

logger = logging.getLogger(__name__)


class WorkflowService:
    """Service for workflow lookup and tenant-scoped access checks."""

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
