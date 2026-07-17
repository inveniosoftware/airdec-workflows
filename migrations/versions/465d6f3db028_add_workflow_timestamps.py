"""add workflow timestamps.

Revision ID: 465d6f3db028
Revises: b2783184ce1a
Create Date: 2026-06-26 10:38:45.582533

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "465d6f3db028"
down_revision: str | Sequence[str] | None = "b2783184ce1a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply this revision."""
    # Batch mode so alter_column/create_unique_constraint work on SQLite,
    # which requires a table rebuild for those operations.
    with op.batch_alter_table("workflow") as batch_op:
        batch_op.add_column(
            sa.Column("created", sa.DateTime(timezone=True), nullable=True)
        )
    op.execute("UPDATE workflow SET created = CURRENT_TIMESTAMP WHERE created IS NULL")
    with op.batch_alter_table("workflow") as batch_op:
        batch_op.alter_column("created", nullable=False)
        batch_op.add_column(
            sa.Column("start_time", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.add_column(
            sa.Column("end_time", sa.DateTime(timezone=True), nullable=True)
        )
        batch_op.create_unique_constraint(
            "uq_workflow_public_id",
            ["public_id"],
        )


def downgrade() -> None:
    """Revert this revision."""
    with op.batch_alter_table("workflow") as batch_op:
        batch_op.drop_constraint("uq_workflow_public_id", type_="unique")
        batch_op.drop_column("end_time")
        batch_op.drop_column("start_time")
        batch_op.drop_column("created")
