from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.deck import DeckStatus


class DeckBaseSchema(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    cards_total_expected: int = Field(ge=1)


class DeckCreateSchema(DeckBaseSchema):
    pass


class DeckUpdateSchema(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    cards_total_expected: int | None = Field(default=None, ge=1)


class DeckSoftDeleteSchema(BaseModel):
    retention_days: int = Field(ge=1, le=3650)
    reminder_days_before: int = Field(ge=0, le=3650)
    confirm: bool = Field(default=False)


class DeckListItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    cards_total_expected: int
    cards_total_actual: int
    status: DeckStatus
    deleted_at: datetime | None
    pending_hard_delete_at: datetime | None
    hard_delete_reminder_at: datetime | None
    hard_delete_confirmed: bool
    created_at: datetime
    updated_at: datetime


class DeckDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    cards_total_expected: int
    cards_total_actual: int
    status: DeckStatus
    deleted_at: datetime | None
    pending_hard_delete_at: datetime | None
    hard_delete_reminder_at: datetime | None
    hard_delete_confirmed: bool
    created_at: datetime
    updated_at: datetime


class DeckMutationResponseSchema(BaseModel):
    ok: bool
    message: str | None = None
    item: DeckDetailSchema | None = None


class DeckListResponseSchema(BaseModel):
    items: list[DeckListItemSchema]