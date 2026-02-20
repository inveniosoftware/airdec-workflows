"""add url to workflows

Revision ID: b2c3d4e5f6a7
Revises: 32ed754ac72d
Create Date: 2026-02-20 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "32ed754ac72d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("workflows", sa.Column("url", sa.String(2048), nullable=True))


def downgrade() -> None:
    op.drop_column("workflows", "url")
