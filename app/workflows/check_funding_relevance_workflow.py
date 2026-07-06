# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

from datetime import timedelta

from temporalio import workflow

from app.activities.check_funding_relevance import (
    CheckFundingRelevanceRequest,
    CheckFundingRelevanceResponse,
    check_funding_relevance,
)
from app.activities.update_workflow import (
    UPDATE_WORKFLOW_RETRY_POLICY,
    WorkflowUpdateRequest,
    update_workflow,
)
from app.database.models import WorkflowStatus
from app.workflows.specs import WorkflowContext, WorkflowParams


class CheckFundingRelevanceParams(WorkflowParams):
    """User-provided params for the check_funding_relevance workflow."""

    metadata: dict[str, object]
    award_description: str
    rule: str


@workflow.defn
class CheckFundingRelevance:
    """Workflow that checks if a record's metadata matches an EU grant description."""

    @workflow.run
    async def run(
        self,
        context: WorkflowContext,
        params: CheckFundingRelevanceParams,
    ) -> CheckFundingRelevanceResponse:
        """Execute the funding relevance check."""
        try:
            await workflow.execute_activity(
                update_workflow,
                WorkflowUpdateRequest(
                    public_id=context.workflow_id,
                    tenant_id=context.tenant_id,
                    start_time=workflow.now(),
                ),
                start_to_close_timeout=timedelta(minutes=1),
                retry_policy=UPDATE_WORKFLOW_RETRY_POLICY,
            )

            result = await workflow.execute_activity(
                check_funding_relevance,
                CheckFundingRelevanceRequest(
                    metadata=params.metadata,
                    award_description=params.award_description,
                    rule=params.rule,
                ),
                start_to_close_timeout=timedelta(minutes=2),
            )
        except Exception:
            await workflow.execute_activity(
                update_workflow,
                WorkflowUpdateRequest(
                    workflow_id=context.workflow_id,
                    tenant_id=context.tenant_id,
                    status=WorkflowStatus.ERROR,
                    result=None,
                    end_time=workflow.now(),
                ),
                start_to_close_timeout=timedelta(minutes=1),
                retry_policy=UPDATE_WORKFLOW_RETRY_POLICY,
            )
            raise

        await workflow.execute_activity(
            update_workflow,
            WorkflowUpdateRequest(
                public_id=context.workflow_id,
                tenant_id=context.tenant_id,
                status=WorkflowStatus.SUCCESS,
                result=result.model_dump(),
                end_time=workflow.now(),
            ),
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=UPDATE_WORKFLOW_RETRY_POLICY,
        )

        return result
