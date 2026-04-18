from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class AdminLogItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    admin_vk_user_id: int
    entity_type: str
    entity_id: int
    action: str
    details: dict[str, Any] | None
    created_at: datetime


class AdminLogListResponseSchema(BaseModel):
    items: list[AdminLogItemSchema]