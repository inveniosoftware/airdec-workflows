# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""LLM-based funding relevance check activity."""

from pydantic import BaseModel, Field
from temporalio import activity

from app.activities._llm import build_agent
from app.config import get_settings


class CheckFundingRelevanceRequest(BaseModel):
    """Request to check if record metadata matches an award description."""

    award_description: str = Field(description="Official EU grant description")
    metadata: dict[str, object] = Field(description="Record metadata")
    rule: str = Field(description="Instructions to decide if there is a match")


class CheckFundingRelevanceResponse(BaseModel):
    """Result of the funding relevance check."""

    match: bool = Field(description="Whether the record is relevant to the grant")
    message: str = Field(description="Explanation of the decision")


@activity.defn
async def check_funding_relevance(
    request: CheckFundingRelevanceRequest,
) -> CheckFundingRelevanceResponse:
    """Use an LLM to assess if a record's metadata matches a grant description."""
    agent = build_agent(get_settings().llm, CheckFundingRelevanceResponse, request.rule)

    prompt = (
        f"Grant description:\n{request.award_description}\n\n"
        f"Record title:\n{request.metadata.get('title')}\n\n"
        f"Record description:\n{request.metadata.get('description')}"
    )

    result = await agent.run(prompt)
    return result.output
