from nanoid import generate
from enum import Enum
from sqlmodel import Field, SQLModel


def nanoid():
    return generate("0123456789abcdefghijklmnopqrstuvwxyz", size=21)


class WorkflowStatus(str, Enum):
    PROCESSING = "processing"
    SUCCESS = "success"
    ERROR = "error"


class Workflow(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    public_id: str = Field(default=nanoid())
    url: str
    status: WorkflowStatus
    user_id: str

    def to_dict(self):
        return {
            "public_id": self.public_id,
            "status": self.status,
            "url": self.url,
            "user_id": self.user_id,
        }
