# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Tests for workflow feedback service helpers."""

from datetime import datetime, timezone

from app.database.models import (
    FeedbackRating,
    Workflow,
    WorkflowFeedback,
    WorkflowStatus,
)
from app.services.workflow_feedback import WorkflowFeedbackService


def _workflow(tenant_id: str) -> Workflow:
    return Workflow(
        workflow_type="extract_metadata",
        status=WorkflowStatus.SUCCESS,
        params={"url": "https://example.com/test.pdf"},
        tenant_id=tenant_id,
    )


def test_get_for_workflow_returns_feedback_for_workflow(db_session):
    """Feedback lookup returns all tenant-owned workflow feedback."""
    workflow = _workflow("tenant-a")
    db_session.add(workflow)
    db_session.commit()
    db_session.refresh(workflow)
    assert workflow.id is not None

    first = WorkflowFeedback(
        workflow_id=workflow.id,
        tenant_id="tenant-a",
        field_path="suggestions.title",
        rating=FeedbackRating.NEGATIVE,
        comment="title is bad",
        created=datetime(2026, 7, 3, 8, 0, tzinfo=timezone.utc),
    )
    second = WorkflowFeedback(
        workflow_id=workflow.id,
        tenant_id="tenant-a",
        field_path="suggestions.description",
        rating=FeedbackRating.POSITIVE,
        created=datetime(2026, 7, 3, 9, 0, tzinfo=timezone.utc),
    )
    db_session.add_all([first, second])
    db_session.commit()

    feedback = WorkflowFeedbackService(db_session).get_for_workflow(
        workflow_id=workflow.id,
        tenant_id="tenant-a",
    )

    assert {item.field_path for item in feedback} == {
        "suggestions.description",
        "suggestions.title",
    }


def test_get_for_workflow_filters_optional_field_path(db_session):
    """Feedback lookup can be narrowed to a specific result field."""
    workflow = _workflow("tenant-a")
    db_session.add(workflow)
    db_session.commit()
    db_session.refresh(workflow)
    assert workflow.id is not None

    db_session.add_all(
        [
            WorkflowFeedback(
                workflow_id=workflow.id,
                tenant_id="tenant-a",
                field_path="suggestions.title",
                rating=FeedbackRating.NEGATIVE,
            ),
            WorkflowFeedback(
                workflow_id=workflow.id,
                tenant_id="tenant-a",
                field_path="suggestions.description",
                rating=FeedbackRating.POSITIVE,
            ),
        ]
    )
    db_session.commit()

    feedback = WorkflowFeedbackService(db_session).get_for_workflow(
        workflow_id=workflow.id,
        tenant_id="tenant-a",
        field_path="suggestions.title",
    )

    assert len(feedback) == 1
    assert feedback[0].field_path == "suggestions.title"


def test_get_for_workflow_is_tenant_scoped(db_session):
    """Feedback lookup only returns rows for the requested tenant."""
    workflow = _workflow("tenant-a")
    db_session.add(workflow)
    db_session.commit()
    db_session.refresh(workflow)
    assert workflow.id is not None

    db_session.add_all(
        [
            WorkflowFeedback(
                workflow_id=workflow.id,
                tenant_id="tenant-a",
                field_path="suggestions.title",
                rating=FeedbackRating.NEGATIVE,
            ),
            WorkflowFeedback(
                workflow_id=workflow.id,
                tenant_id="tenant-b",
                field_path="suggestions.title",
                rating=FeedbackRating.POSITIVE,
            ),
        ]
    )
    db_session.commit()

    feedback = WorkflowFeedbackService(db_session).get_for_workflow(
        workflow_id=workflow.id,
        tenant_id="tenant-a",
    )

    assert len(feedback) == 1
    assert feedback[0].tenant_id == "tenant-a"
