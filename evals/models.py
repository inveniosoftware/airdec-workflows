# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Pydantic models and LLM setup for metadata extraction."""

import os

from pydantic import BaseModel, Field
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.litellm import LiteLLMProvider
from pydantic_ai.providers.ollama import OllamaProvider


class Affiliation(BaseModel):
    """Affiliation model."""

    name: str
    ror: str | None = None


class Creator(BaseModel):
    """Creator model for structured output."""

    name: str
    affiliation: list[Affiliation] | None = None
    orcid: str | None = None


class MetadataResult(BaseModel):
    """Metadata result schema for evals."""

    title: str | None = None
    description: str | None = None
    creators: list[Creator] = Field(default_factory=list)
    doi: str | None = None
    publication_date: str | None = None


def parse_llm(llm: str) -> tuple[str, str]:
    """Parse LLM environment variable into provider and model name."""
    provider, sep, model_name = llm.partition("/")
    if not sep:
        raise ValueError("Invalid LLM; expected '<provider>/<model>'")
    provider = provider.strip().lower()
    model_name = model_name.strip()
    if provider not in {"litellm", "openai", "ollama"}:
        raise ValueError("Invalid LLM; provider must be 'litellm' or 'ollama'")
    if not model_name:
        raise ValueError("Invalid LLM; model name is missing")
    return provider, model_name


def create_model() -> OpenAIChatModel:
    """Create an OpenAI-compatible chat model from settings."""
    provider_name, model_name = parse_llm(os.getenv("LLM"))

    if provider_name == "ollama":
        provider = OllamaProvider(
            base_url=os.getenv("OLLAMA_API_BASE"),
            api_key=os.getenv("OLLAMA_API_KEY"),
        )
    else:
        provider = LiteLLMProvider(
            api_base=os.getenv("LITELLM_API_BASE"),
            api_key=os.getenv("LITELLM_API_KEY"),
        )

    return OpenAIChatModel(model_name=model_name, provider=provider)
