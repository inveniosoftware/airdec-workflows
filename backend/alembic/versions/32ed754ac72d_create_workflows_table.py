"""create workflows table

Revision ID: 32ed754ac72d
Revises:
Create Date: 2026-02-18 11:40:14.155820

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "32ed754ac72d"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

status_enum = postgresql.ENUM(
    "PROCESSING",
    "SUCCESS",
    "ERROR",
    name="status",
)


def upgrade() -> None:

    op.create_table(
        "workflows",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column(
            "public_id",
            sa.String(length=21),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("status", status_enum, nullable=False),
        sa.Column("user_id", sa.String(50), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("workflows")
