# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Workflow feedback database operations."""

import logging

from fastapi import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlmodel import Session, select

from app.database.models import FeedbackRating, WorkflowFeedback

logger = logging.getLogger(__name__)


class WorkflowFeedbackService:
    """Service for append-only workflow feedback."""

    def __init__(self, session: Session):
        """Create a workflow feedback service for one database session."""
        self.session = session

    def create(
        self,
        *,
        workflow_id: int,
        tenant_id: str,
        field_path: str,
        rating: FeedbackRating,
        user_id: str | None = None,
        comment: str | None = None,
    ) -> WorkflowFeedback:
        """Append feedback for a workflow result field."""
        feedback = WorkflowFeedback(
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            user_id=user_id,
            field_path=field_path,
            rating=rating,
            comment=comment,
        )

        try:
            self.session.add(feedback)
            self.session.commit()
            self.session.refresh(feedback)
        except SQLAlchemyError:
            logger.exception("Error creating workflow feedback")
            raise HTTPException(status_code=500, detail="Could not create feedback")

        return feedback

    def get_for_workflow(
        self,
        *,
        workflow_id: int,
        tenant_id: str,
        field_path: str | None = None,
    ) -> list[WorkflowFeedback]:
        """Get feedback for a workflow, optionally narrowed to one field."""
        statement = (
            select(WorkflowFeedback)
            .where(WorkflowFeedback.workflow_id == workflow_id)
            .where(WorkflowFeedback.tenant_id == tenant_id)
        )
        if field_path is not None:
            statement = statement.where(WorkflowFeedback.field_path == field_path)

        return list(self.session.exec(statement).all())
