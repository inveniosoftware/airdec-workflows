"""Workflow registry — maps workflow type names to Temporal dispatch details."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict


class WorkflowContext(BaseModel):
    """Server-generated context attached to every workflow invocation."""

    workflow_id: str
    tenant_id: str


class WorkflowParams(BaseModel):
    """Base model for user-provided workflow params."""

    model_config = ConfigDict(extra="forbid")


@dataclass(frozen=True)
class WorkflowSpec:
    """Describes a Temporal workflow that the API can dispatch."""

    workflow_fn: Any
    """Entry-point method of the ``@workflow.defn`` class."""

    params_model: type[WorkflowParams]
    """Pydantic model used to validate workflow-specific input params."""

    task_queue: str
    """Temporal task queue that workers listen on for this workflow."""

    id_prefix: str
    """Prefix used when constructing the Temporal workflow ID."""


# Global registry — populated at import time by each workflow module.
WORKFLOW_REGISTRY: dict[str, WorkflowSpec] = {}


def register_workflow(name: str, spec: WorkflowSpec) -> None:
    """Register a workflow type.

    Raises:
        ValueError: If *name* is already registered.
    """
    if name in WORKFLOW_REGISTRY:
        raise ValueError(f"Workflow type {name!r} is already registered")
    WORKFLOW_REGISTRY[name] = spec


def get_workflow_spec(name: str) -> WorkflowSpec:
    """Look up a registered workflow by type name.

    Raises:
        KeyError: If *name* has not been registered.
    """
    try:
        return WORKFLOW_REGISTRY[name]
    except KeyError:
        registered = ", ".join(get_registered_types()) or "(none)"
        raise KeyError(
            f"Unknown workflow type {name!r}. Registered types: {registered}"
        ) from None


def get_registered_types() -> list[str]:
    """Return a sorted list of all registered workflow type names."""
    return sorted(WORKFLOW_REGISTRY)
