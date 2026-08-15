"""Add table layout fields and is_active

Revision ID: 20260815_0002
Revises: 20260815_0001
Create Date: 2026-08-15 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260815_0002"
down_revision: Union[str, None] = "20260815_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tables", sa.Column("position_x", sa.Integer(), server_default="0", nullable=False))
    op.add_column("tables", sa.Column("position_y", sa.Integer(), server_default="0", nullable=False))
    op.add_column("tables", sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False))


def downgrade() -> None:
    op.drop_column("tables", "is_active")
    op.drop_column("tables", "position_y")
    op.drop_column("tables", "position_x")
