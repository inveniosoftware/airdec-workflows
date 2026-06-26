# SPDX-FileCopyrightText: 2026 CERN.
# SPDX-License-Identifier: MIT

"""Database models for the Orcha workflow system."""

from datetime import UTC, datetime
from enum import Enum

from nanoid import generate
from sqlalchemy import JSON, Column, DateTime
from sqlmodel import Field, SQLModel


def nanoid():
    """Generate a 21-character nanoid."""
    return generate("0123456789abcdefghijklmnopqrstuvwxyz", size=21)


class WorkflowStatus(str, Enum):
    """Status of a workflow execution."""

    PROCESSING = "processing"
    SUCCESS = "success"
    ERROR = "error"


class Workflow(SQLModel, table=True):
    """Database model for a workflow execution."""

    id: int | None = Field(default=None, primary_key=True)
    public_id: str = Field(default_factory=nanoid)
    workflow_type: str
    params: dict = Field(default_factory=dict, sa_column=Column(JSON))
    status: WorkflowStatus
    tenant_id: str
    result: dict | None = Field(default=None, sa_column=Column(JSON))
    created: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    start_time: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    end_time: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
