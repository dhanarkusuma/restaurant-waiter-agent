"""Add order item name snapshot

Revision ID: 20260815_0003
Revises: 20260815_0002
Create Date: 2026-08-15 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260815_0003"
down_revision: Union[str, None] = "20260815_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add column as nullable initially
    op.add_column("order_items", sa.Column("name", sa.String(length=100), nullable=True))

    # 2. Backfill existing order_items.name from menu_items.name
    op.execute(
        """
        UPDATE order_items
        SET name = menu_items.name
        FROM menu_items
        WHERE order_items.menu_item_id = menu_items.id
        """
    )
    # Fallback for any orphaned rows (if any)
    op.execute(
        """
        UPDATE order_items
        SET name = 'Unknown Item'
        WHERE name IS NULL
        """
    )

    # 3. Alter column to NOT NULL
    op.alter_column("order_items", "name", nullable=False)


def downgrade() -> None:
    op.drop_column("order_items", "name")
