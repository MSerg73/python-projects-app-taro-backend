from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.admin_log import AdminLogItemSchema, AdminLogListResponseSchema
from backend.app.services.admin_logs import list_admin_logs

router = APIRouter()


@router.get("", response_model=AdminLogListResponseSchema)
async def list_admin_logs_route(
    admin_vk_user_id: int | None = Query(default=None, ge=1),
    entity_type: str | None = Query(default=None),
    entity_id: int | None = Query(default=None, ge=1),
    action: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> AdminLogListResponseSchema:
    items = list_admin_logs(
        db,
        admin_vk_user_id=admin_vk_user_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        limit=limit,
    )

    return AdminLogListResponseSchema(
        items=[AdminLogItemSchema.model_validate(item) for item in items]
    )