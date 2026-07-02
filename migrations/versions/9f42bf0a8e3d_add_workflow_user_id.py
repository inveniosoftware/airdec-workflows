"""add workflow user id.

Revision ID: 9f42bf0a8e3d
Revises: 465d6f3db028
Create Date: 2026-07-02 11:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f42bf0a8e3d"
down_revision: str | Sequence[str] | None = "465d6f3db028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply this revision."""
    op.add_column("workflow", sa.Column("user_id", sa.String(), nullable=True))


def downgrade() -> None:
    """Revert this revision."""
    op.drop_column("workflow", "user_id")
