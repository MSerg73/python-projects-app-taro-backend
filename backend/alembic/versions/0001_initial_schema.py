"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-04 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


deck_status_enum = postgresql.ENUM(
    "draft",
    "ready",
    name="deck_status",
    create_type=False,
)


def upgrade() -> None:
    deck_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "decks",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("cards_total_expected", sa.Integer(), nullable=False),
        sa.Column("cards_total_actual", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", deck_status_enum, nullable=False, server_default="draft"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_decks_id", "decks", ["id"], unique=False)

    op.create_table(
        "spreads",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("deck_id", sa.Integer(), nullable=False),
        sa.Column("cards_count", sa.Integer(), nullable=False),
        sa.Column("card_numbers", postgresql.ARRAY(sa.Integer()), nullable=False),
        sa.Column("active_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["deck_id"], ["decks.id"], ondelete="RESTRICT"),
    )
    op.create_index("ix_spreads_id", "spreads", ["id"], unique=False)
    op.create_index("ix_spreads_deck_id", "spreads", ["deck_id"], unique=False)

    op.create_table(
        "cards",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("deck_id", sa.Integer(), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["deck_id"], ["decks.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("deck_id", "number", name="uq_cards_deck_id_number"),
    )
    op.create_index("ix_cards_id", "cards", ["id"], unique=False)
    op.create_index("ix_cards_deck_id", "cards", ["deck_id"], unique=False)

    op.create_table(
        "user_daily_opens",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("vk_user_id", sa.BigInteger(), nullable=False),
        sa.Column("spread_id", sa.Integer(), nullable=False),
        sa.Column("opened_card_number", sa.Integer(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("open_date", sa.Date(), nullable=False),
        sa.ForeignKeyConstraint(["spread_id"], ["spreads.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint(
            "vk_user_id",
            "open_date",
            name="uq_user_daily_opens_vk_user_id_open_date",
        ),
    )
    op.create_index("ix_user_daily_opens_id", "user_daily_opens", ["id"], unique=False)
    op.create_index("ix_user_daily_opens_vk_user_id", "user_daily_opens", ["vk_user_id"], unique=False)
    op.create_index("ix_user_daily_opens_spread_id", "user_daily_opens", ["spread_id"], unique=False)
    op.create_index("ix_user_daily_opens_open_date", "user_daily_opens", ["open_date"], unique=False)

    op.create_table(
        "admin_logs",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("admin_vk_user_id", sa.BigInteger(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_admin_logs_id", "admin_logs", ["id"], unique=False)
    op.create_index("ix_admin_logs_admin_vk_user_id", "admin_logs", ["admin_vk_user_id"], unique=False)
    op.create_index("ix_admin_logs_entity_id", "admin_logs", ["entity_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_admin_logs_entity_id", table_name="admin_logs")
    op.drop_index("ix_admin_logs_admin_vk_user_id", table_name="admin_logs")
    op.drop_index("ix_admin_logs_id", table_name="admin_logs")
    op.drop_table("admin_logs")

    op.drop_index("ix_user_daily_opens_open_date", table_name="user_daily_opens")
    op.drop_index("ix_user_daily_opens_spread_id", table_name="user_daily_opens")
    op.drop_index("ix_user_daily_opens_vk_user_id", table_name="user_daily_opens")
    op.drop_index("ix_user_daily_opens_id", table_name="user_daily_opens")
    op.drop_table("user_daily_opens")

    op.drop_index("ix_cards_deck_id", table_name="cards")
    op.drop_index("ix_cards_id", table_name="cards")
    op.drop_table("cards")

    op.drop_index("ix_spreads_deck_id", table_name="spreads")
    op.drop_index("ix_spreads_id", table_name="spreads")
    op.drop_table("spreads")

    op.drop_index("ix_decks_id", table_name="decks")
    op.drop_table("decks")

    deck_status_enum.drop(op.get_bind(), checkfirst=True)