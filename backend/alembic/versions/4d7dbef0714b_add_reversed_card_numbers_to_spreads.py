"""add reversed_card_numbers to spreads

Revision ID: 4d7dbef0714b
Revises: 2ff681a241d2
Create Date: 2026-04-14 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4d7dbef0714b"
down_revision = "2ff681a241d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("spreads") as batch_op:
        batch_op.add_column(
            sa.Column(
                "reversed_card_numbers",
                sa.JSON(),
                nullable=False,
                server_default="[]",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("spreads") as batch_op:
        batch_op.drop_column("reversed_card_numbers")