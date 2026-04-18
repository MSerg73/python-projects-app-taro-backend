from __future__ import annotations

from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from backend.app.models.admin_log import AdminLog


def _normalize_limit(value: int | None) -> int:
    if value is None:
        return 100

    return max(1, min(int(value), 500))


def create_admin_log(
    db: Session,
    *,
    admin_vk_user_id: int,
    entity_type: str,
    entity_id: int,
    action: str,
    details: dict[str, Any] | None = None,
) -> AdminLog:
    item = AdminLog(
        admin_vk_user_id=admin_vk_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        details=details,
    )

    db.add(item)
    db.flush()

    return item


def list_admin_logs(
    db: Session,
    *,
    admin_vk_user_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    action: str | None = None,
    limit: int | None = 100,
) -> list[AdminLog]:
    stmt: Select[tuple[AdminLog]] = select(AdminLog)

    if admin_vk_user_id is not None:
        stmt = stmt.where(AdminLog.admin_vk_user_id == admin_vk_user_id)

    if entity_type:
        stmt = stmt.where(AdminLog.entity_type == entity_type)

    if entity_id is not None:
        stmt = stmt.where(AdminLog.entity_id == entity_id)

    if action:
        stmt = stmt.where(AdminLog.action == action)

    stmt = stmt.order_by(AdminLog.created_at.desc(), AdminLog.id.desc())
    stmt = stmt.limit(_normalize_limit(limit))

    return list(db.scalars(stmt).all())