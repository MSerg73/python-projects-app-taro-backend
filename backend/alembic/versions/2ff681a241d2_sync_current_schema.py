"""sync current schema

Revision ID: 2ff681a241d2
Revises: 0001_initial_schema
Create Date: 2026-04-09 06:50:09.712160
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "2ff681a241d2"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def _bind():
    return op.get_bind()


def _is_postgresql() -> bool:
    return _bind().dialect.name == "postgresql"


def _is_sqlite() -> bool:
    return _bind().dialect.name == "sqlite"


def _inspector():
    return sa.inspect(_bind())


def _table_exists(table_name: str) -> bool:
    return table_name in _inspector().get_table_names()


def _column_map(table_name: str) -> dict[str, dict]:
    return {
        column["name"]: column
        for column in _inspector().get_columns(table_name)
    }


def _index_names(table_name: str) -> set[str]:
    return {
        index["name"]
        for index in _inspector().get_indexes(table_name)
        if index.get("name")
    }


def _is_json_type(column_type: object) -> bool:
    return "json" in column_type.__class__.__name__.lower()


def _spread_status_type():
    if _is_postgresql():
        from sqlalchemy.dialects import postgresql

        return postgresql.ENUM(
            "draft",
            "scheduled",
            "active",
            "completed",
            name="spread_status",
            create_type=False,
        )

    return sa.Enum(
        "draft",
        "scheduled",
        "active",
        "completed",
        name="spread_status",
        native_enum=False,
    )


def _create_spread_status_type_if_needed() -> None:
    if not _is_postgresql():
        return

    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                CREATE TYPE spread_status AS ENUM (
                    'draft',
                    'scheduled',
                    'active',
                    'completed'
                );
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END
            $$;
            """
        )
    )


def _sync_decks() -> None:
    if not _table_exists("decks"):
        return

    columns = _column_map("decks")
    additions: list[sa.Column] = []

    if "pending_hard_delete_at" not in columns:
        additions.append(sa.Column("pending_hard_delete_at", sa.DateTime(timezone=True), nullable=True))

    if "hard_delete_reminder_at" not in columns:
        additions.append(sa.Column("hard_delete_reminder_at", sa.DateTime(timezone=True), nullable=True))

    if "hard_delete_confirmed" not in columns:
        additions.append(
            sa.Column(
                "hard_delete_confirmed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )

    if not additions:
        return

    with op.batch_alter_table("decks") as batch_op:
        for column in additions:
            batch_op.add_column(column)


def _sync_spreads() -> None:
    if not _table_exists("spreads"):
        return

    columns = _column_map("spreads")

    needs_status = "status" not in columns
    needs_deleted_at = "deleted_at" not in columns

    if needs_status:
        _create_spread_status_type_if_needed()

    if needs_status or needs_deleted_at:
        with op.batch_alter_table("spreads") as batch_op:
            if needs_status:
                batch_op.add_column(
                    sa.Column(
                        "status",
                        _spread_status_type(),
                        nullable=False,
                        server_default="draft",
                    )
                )

            if needs_deleted_at:
                batch_op.add_column(
                    sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True)
                )

    columns = _column_map("spreads")

    if "card_numbers" in columns and not _is_json_type(columns["card_numbers"]["type"]):
        if _is_postgresql():
            op.execute(
                sa.text(
                    """
                    ALTER TABLE spreads
                    ALTER COLUMN card_numbers
                    TYPE JSON
                    USING to_json(card_numbers)
                    """
                )
            )
        elif _is_sqlite():
            with op.batch_alter_table("spreads") as batch_op:
                batch_op.alter_column(
                    "card_numbers",
                    existing_type=columns["card_numbers"]["type"],
                    type_=sa.JSON(),
                    existing_nullable=False,
                )
        else:
            op.alter_column(
                "spreads",
                "card_numbers",
                existing_type=columns["card_numbers"]["type"],
                type_=sa.JSON(),
                existing_nullable=False,
            )


def _sync_admin_logs() -> None:
    if not _table_exists("admin_logs"):
        return

    columns = _column_map("admin_logs")

    if "details" in columns and not _is_json_type(columns["details"]["type"]):
        if _is_postgresql():
            op.execute(
                sa.text(
                    """
                    ALTER TABLE admin_logs
                    ALTER COLUMN details
                    TYPE JSON
                    USING CASE
                        WHEN details IS NULL OR btrim(details) = '' THEN NULL
                        WHEN left(ltrim(details), 1) IN ('{', '[') THEN details::json
                        ELSE to_json(details)
                    END
                    """
                )
            )
        elif _is_sqlite():
            with op.batch_alter_table("admin_logs") as batch_op:
                batch_op.alter_column(
                    "details",
                    existing_type=columns["details"]["type"],
                    type_=sa.JSON(),
                    existing_nullable=True,
                )
        else:
            op.alter_column(
                "admin_logs",
                "details",
                existing_type=columns["details"]["type"],
                type_=sa.JSON(),
                existing_nullable=True,
            )

    indexes = _index_names("admin_logs")

    if "ix_admin_logs_action" not in indexes:
        op.create_index("ix_admin_logs_action", "admin_logs", ["action"], unique=False)

    if "ix_admin_logs_entity_type" not in indexes:
        op.create_index("ix_admin_logs_entity_type", "admin_logs", ["entity_type"], unique=False)


def upgrade() -> None:
    _sync_decks()
    _sync_spreads()
    _sync_admin_logs()


def downgrade() -> None:
    raise NotImplementedError(
        "Downgrade for 2ff681a241d2 is intentionally not supported."
    )