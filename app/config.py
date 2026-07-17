# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Centralized application settings using Pydantic Settings."""

from functools import lru_cache
from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LlmSettings(BaseModel):
    """Extra LLM config, parsed from the JSON ``LLM_SETTINGS`` env var.

    ``model`` is forwarded verbatim to the chat model's request settings
    (``max_tokens``, ``extra_body``, ``temperature`` ...). The rest are Orcha
    signals that decide how the agent is assembled.
    """

    # Orcha signal: structured-output strategy.
    output: Literal["tool", "prompted"] = "tool"
    # Passed straight to OpenAIChatModelSettings.
    model: dict[str, Any] = Field(default_factory=dict)


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )

    # Database
    # DB_URL overrides everything else. Without it, DB_DIALECT chooses between
    # sqlite for local development and postgresql built from the DB_USER fields.
    db_url: str | None = None
    db_dialect: Literal["sqlite", "postgresql"] = "sqlite"
    db_path: str = "orcha.db"
    db_user: str = "postgres"
    db_password: str = "postgres"
    db_host: str = "localhost"
    db_port: str = "5433"
    db_name: str = "orcha"

    # Temporal
    temporal_host: str = "localhost:7233"

    # Authentication
    jwt_algorithm: str = "RS256"
    auth_disabled: bool = False
    tenants_config_path: str = "tenants.json"

    # Security
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # LLM
    # TODO Currently we have only a single workflow, so single LLM configuration
    # is fine. We can parameterize it or make it configurable per workflow later.
    llm: str = "ollama/qwen3:4b"
    llm_settings: LlmSettings = Field(default_factory=LlmSettings)
    litellm_api_base: str = "<litellm-endpoint>"
    litellm_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_api_key: str | None = None

    # Langfuse
    langfuse_enabled: bool = False
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_base_url: str | None = None

    # PDF downloads
    pdf_http_allowlist: str | None = None

    @property
    def database_url(self) -> str:
        """Build the database connection string."""
        if self.db_url:
            return self.db_url
        if self.db_dialect == "sqlite":
            return f"sqlite:///{self.db_path}"
        return (
            f"postgresql+psycopg://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
