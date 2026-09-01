# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""LLM-based funding relevance check activity."""

from datetime import timedelta

from pydantic import BaseModel, Field
from temporalio import activity
from temporalio.common import RetryPolicy

from app.activities._llm import build_agent
from app.config import get_settings
from app.observability import propagate_langfuse_context
from app.workflows.specs import WorkflowContext

FUNDING_WORKFLOW_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=2,
    maximum_interval=timedelta(seconds=20),
    maximum_attempts=3,
)


class CheckFundingRelevanceRequest(BaseModel):
    """Request to check if record metadata matches an award description."""

    award_description: str = Field(description="Official EU grant description")
    metadata: dict[str, object] = Field(description="Record metadata")
    rule: str = Field(description="Instructions to decide if there is a match")


class CheckFundingRelevanceResponse(BaseModel):
    """Result of the funding relevance check."""

    match: bool = Field(description="Whether the record is relevant to the grant")
    message: str = Field(description="Explanation of the decision")


# Below this many non-whitespace-stripped chars, there is insufficient data
# for performing a relevance check.
MIN_METADATA_CHARS = 30


@activity.defn
async def check_funding_relevance(
    request: CheckFundingRelevanceRequest,
    context: WorkflowContext,
) -> CheckFundingRelevanceResponse:
    """Use an LLM to assess if a record's metadata matches a grant description."""
    agent = build_agent(get_settings().llm, CheckFundingRelevanceResponse, request.rule)

    title = str(request.metadata.get("title", ""))
    description = str(request.metadata.get("description", ""))
    if len(title.strip()) + len(description.strip()) < MIN_METADATA_CHARS:
        return CheckFundingRelevanceResponse(
            match=False,
            message="Insufficient metadata to check funding relevance.",
        )
    prompt = (
        f"Grant description:\n{request.award_description}\n\n"
        f"Record title:\n{title}\n\n"
        f"Record description:\n{description}"
    )

    with propagate_langfuse_context(context, trace_name="check_funding_relevance"):
        result = await agent.run(prompt)
    return result.output
