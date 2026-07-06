# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""LLM-based metadata suggestions activity."""

import re
from datetime import timedelta
from difflib import SequenceMatcher

from idutils.normalizers import normalize_doi
from idutils.validators import is_doi
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
    "leave anything you cannot determine empty. "
    "If a piece of information is not present in the document text, leave that "
    "field null or empty. Never guess, invent, or use placeholder values."
)

# Below this many non-whitespace-stripped chars the extraction is effectively empty
# (broken/image-only PDFs). Models fabricate whole records, output schema
# placeholders/examples, loop in reasoning, or crash tool-call parsers on empty input.
MIN_TEXT_CHARS = 50

# Values the model returns for these fields must (fuzzily) be present in the source
# text, else they're skipped.
_PRESENCE_THRESHOLDS = {
    "title": 0.85,
    "description": 0.80,
}


def _coverage(value: str, text: str) -> float:
    """Fraction of `value` found in `text` (ordered matching blocks)."""
    sm = SequenceMatcher(None, value, text, autojunk=False)
    matched = sum(b.size for b in sm.get_matching_blocks())
    return matched / len(value) if value else 1.0


def _normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", str(s or "").casefold()).strip()


def _clear_absent_fields(output: ExtractedMetadata, text: str) -> None:
    """Null title/description/doi whose values aren't present in the source text."""
    normalized_text = _normalize_text(text)
    for field, threshold in _PRESENCE_THRESHOLDS.items():
        value = getattr(output, field)
        if not value:
            continue

        normalized_value = _normalize_text(value)
        if (
            normalized_value in normalized_text
            or _coverage(normalized_value, normalized_text) >= threshold
        ):
            continue
        setattr(output, field, None)

    # DOIs wrap across lines and may carry a URL or 'doi:' prefix: normalize to
    # the bare identifier and match it whitespace-insensitively in the source.
    # A non-DOI is fabricated by construction (and would crash normalize_doi).
    if output.doi:
        if not is_doi(output.doi):
            output.doi = None
        else:
            squashed = re.sub(r"\s+", "", text).casefold()
            if normalize_doi(output.doi).casefold() not in squashed:
                output.doi = None


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
    if len(request.text.strip()) < MIN_TEXT_CHARS:
        # No usable text: skip the LLM entirely rather than let it fabricate.
        return MetadataSuggestions(suggestions=[])

    agent = _build_agent(get_settings().llm)
    with propagate_langfuse_context(context, trace_name="extract_metadata"):
        result = await agent.run(request.text)

    _clear_absent_fields(result.output, request.text)
    return result.output.to_suggestions()
