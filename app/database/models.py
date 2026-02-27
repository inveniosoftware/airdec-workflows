from enum import Enum

from nanoid import generate
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
    public_id: str = Field(default=nanoid())
    url: str
    status: WorkflowStatus
    user_id: str

    def to_dict(self):
        """Convert workflow to a dictionary representation."""
        return {
            "public_id": self.public_id,
            "status": self.status,
            "url": self.url,
            "user_id": self.user_id,
        }
