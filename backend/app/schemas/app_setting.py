from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.app_setting import AppSettingKey


class AppSettingItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: AppSettingKey
    value_json: Any | None = None
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class AppSettingBooleanValueSchema(BaseModel):
    value: bool


class AppSettingMutationResponseSchema(BaseModel):
    ok: bool
    item: AppSettingItemSchema


class AppSettingListResponseSchema(BaseModel):
    items: list[AppSettingItemSchema]


class UpdateReversedCardsSettingSchema(BaseModel):
    value: bool = Field(...)