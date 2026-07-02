# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Shared workflow dispatch types."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict


class WorkflowContext(BaseModel):
    """Server-generated context attached to every workflow invocation."""

    workflow_id: str
    tenant_id: str
    user_id: str | None = None


class WorkflowParams(BaseModel):
    """Base model for user-provided workflow params."""

    model_config = ConfigDict(extra="forbid")


@dataclass(frozen=True)
class WorkflowSpec:
    """Describes a Temporal workflow that the API can dispatch."""

    workflow_cls: Any
    """Class decorated with ``@workflow.defn``."""

    params_model: type[WorkflowParams]
    """Pydantic model used to validate workflow-specific input params."""

    task_queue: str
    """Temporal task queue that workers listen on for this workflow."""

    id_prefix: str
    """Prefix used when constructing the Temporal workflow ID."""
