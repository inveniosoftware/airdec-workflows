# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""LLM-based metadata suggestions activity."""

from datetime import timedelta

from pydantic import BaseModel, Field
from pydantic_ai import Agent, PromptedOutput
from pydantic_ai.models.openai import OpenAIChatModel, OpenAIChatModelSettings
from pydantic_ai.providers.litellm import LiteLLMProvider
from pydantic_ai.providers.ollama import OllamaProvider
from temporalio import activity
from temporalio.common import RetryPolicy

from app.config import get_settings
from app.observability import propagate_langfuse_context
from app.schemas.metadata_suggestions import ExtractedMetadata, MetadataSuggestions
from app.workflows.specs import WorkflowContext

EXTRACT_METADATA_RETRY_POLICY = RetryPolicy(
    initial_interval=timedelta(seconds=5),
    backoff_coefficient=2,
    maximum_interval=timedelta(seconds=20),
    maximum_attempts=3,
)


def _parse_llm(llm: str) -> tuple[str, str]:
    provider, sep, model_name = llm.partition("/")
    if not sep:
        raise ValueError("Invalid LLM; expected '<provider>/<model>'")
    provider = provider.strip().lower()
    model_name = model_name.strip()
    if provider not in {"litellm", "ollama"}:
        raise ValueError("Invalid LLM; provider must be 'litellm' or 'ollama'")
    if not model_name:
        raise ValueError("Invalid LLM; model name is missing")
    return provider, model_name


class ExtractMetadataRequest(BaseModel):
    """Request to generate metadata suggestions from document text."""

    text: str = Field(description="Document text to analyze")


INSTRUCTIONS = (
    "You extract bibliographic metadata from the document text. "
    "Only include information clearly stated in the text; "
    "leave anything you cannot determine empty."
)


# Extra instruction pieces for prompted output (no native tool calls): cap
# reasoning, then force a single JSON object.
_REASONING_LOW = "Reasoning: low"
_JSON_ONLY = (
    "Respond immediately; do not deliberate. "
    "Reply with exactly one JSON object matching the schema and nothing else."
)


def _build_agent(llm: str) -> Agent[None, ExtractedMetadata]:
    """Build the extraction agent for `llm` from the configured settings."""
    settings = get_settings()
    cfg = settings.llm_settings
    provider_name, model_name = _parse_llm(llm)

    if provider_name == "ollama":
        provider = OllamaProvider(
            base_url=settings.ollama_base_url, api_key=settings.ollama_api_key
        )
    else:
        provider = LiteLLMProvider(
            api_base=settings.litellm_api_base, api_key=settings.litellm_api_key
        )

    model = OpenAIChatModel(
        model_name=model_name,
        provider=provider,
        settings=OpenAIChatModelSettings(**cfg.model),
    )
    if cfg.output == "prompted":
        return Agent[None, ExtractedMetadata](
            model,
            instructions=[_REASONING_LOW, INSTRUCTIONS, _JSON_ONLY],
            output_type=PromptedOutput(ExtractedMetadata),
        )
    return Agent[None, ExtractedMetadata](
        model, instructions=INSTRUCTIONS, output_type=ExtractedMetadata
    )


@activity.defn
async def extract_metadata_with_llm(
    request: ExtractMetadataRequest,
    context: WorkflowContext,
) -> MetadataSuggestions:
    """Generate typed metadata suggestions using an LLM."""
    agent = _build_agent(get_settings().llm)
    with propagate_langfuse_context(context, trace_name="extract_metadata"):
        result = await agent.run(request.text)

    return result.output.to_suggestions()
