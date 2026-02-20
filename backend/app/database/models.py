from sqlalchemy import Column, Enum, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from nanoid import generate
import enum

Base = declarative_base()


def nanoid():
    return generate("0123456789abcdefghijklmnopqrstuvwxyz", size=21)


class Status(enum.Enum):
    PROCESSING = "processing"
    SUCCESS = "success"
    ERROR = "error"


class Workflow(Base):
    __tablename__ = "workflows"
    id = Column(Integer, primary_key=True)
    public_id = Column(String(21), nullable=False, unique=True, default=nanoid)
    status = Column(Enum(Status), nullable=False)
    url = Column(String(2048), nullable=True)
    user_id = Column(String(50), nullable=False)

    def to_dict(self):
        return {
            "public_id": self.public_id,
            "status": self.status,
            "url": self.url,
            "user_id": self.user_id,
        }
