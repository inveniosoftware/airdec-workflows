"""add workflow feedback.

Revision ID: d3f4b7a9c2e1
Revises: 9f42bf0a8e3d
Create Date: 2026-07-03 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
import sqlmodel
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3f4b7a9c2e1"
down_revision: str | Sequence[str] | None = "9f42bf0a8e3d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply this revision."""
    op.create_table(
        "workflow_feedback",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workflow_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sqlmodel.AutoString(), nullable=False),
        sa.Column("user_id", sqlmodel.AutoString(), nullable=True),
        sa.Column("field_path", sqlmodel.AutoString(), nullable=False),
        sa.Column(
            "rating",
            sa.Enum("POSITIVE", "NEGATIVE", name="feedbackrating"),
            nullable=False,
        ),
        sa.Column("comment", sqlmodel.AutoString(), nullable=True),
        sa.Column("created", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflow.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Revert this revision."""
    op.drop_table("workflow_feedback")
    sa.Enum(name="feedbackrating").drop(op.get_bind(), checkfirst=True)
