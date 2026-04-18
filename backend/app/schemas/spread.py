from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.models.spread import SpreadKind, SpreadStatus


class SpreadBaseSchema(BaseModel):
    deck_id: int = Field(ge=1)
    title: str = Field(default="Карта дня", min_length=1, max_length=255)
    description: str | None = None
    spread_kind: SpreadKind = SpreadKind.MAIN_DAILY
    cards_count: int = Field(ge=3, le=7)
    card_numbers: list[int] = Field(min_length=3, max_length=7)
    reversed_card_numbers: list[int] = Field(default_factory=list, max_length=7)
    active_from: datetime | None = None
    active_to: datetime | None = None


class SpreadCreateSchema(SpreadBaseSchema):
    pass


class SpreadUpdateSchema(BaseModel):
    deck_id: int | None = Field(default=None, ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    spread_kind: SpreadKind | None = None
    cards_count: int | None = Field(default=None, ge=3, le=7)
    card_numbers: list[int] | None = Field(default=None, min_length=3, max_length=7)
    reversed_card_numbers: list[int] | None = Field(default=None, max_length=7)
    active_from: datetime | None = None
    active_to: datetime | None = None


class SpreadListItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    deck_id: int
    title: str
    description: str | None = None
    spread_kind: SpreadKind
    cards_count: int
    card_numbers: list[int]
    reversed_card_numbers: list[int] = Field(default_factory=list)
    active_from: datetime | None
    active_to: datetime | None
    status: SpreadStatus
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SpreadDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    deck_id: int
    title: str
    description: str | None = None
    spread_kind: SpreadKind
    cards_count: int
    card_numbers: list[int]
    reversed_card_numbers: list[int] = Field(default_factory=list)
    active_from: datetime | None
    active_to: datetime | None
    status: SpreadStatus
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SpreadMutationResponseSchema(BaseModel):
    ok: bool
    message: str | None = None
    item: SpreadDetailSchema | None = None


class SpreadListResponseSchema(BaseModel):
    items: list[SpreadListItemSchema]


class OpenedCardSchema(BaseModel):
    number: int
    name: str | None = None
    image_url: str | None = None
    description: str | None = None
    reversed_description: str | None = None
    is_reversed: bool = False


class UserOpenSchema(BaseModel):
    id: int
    vk_user_id: int
    spread_id: int
    opened_card_number: int
    opened_at: str | None = None
    open_date: str | None = None
    deck_id: int | None = None


class AppSpreadStateSchema(BaseModel):
    spread: SpreadDetailSchema | None = None
    opened_card: OpenedCardSchema | None = None
    user_open: UserOpenSchema | None = None
    message: str | None = None
    project_timezone: str | None = None


class AppActiveSpreadItemSchema(BaseModel):
    spread: SpreadDetailSchema
    opened_card: OpenedCardSchema | None = None
    user_open: UserOpenSchema | None = None
    message: str | None = None


class AppActiveSpreadsStateSchema(BaseModel):
    items: list[AppActiveSpreadItemSchema] = Field(default_factory=list)
    project_timezone: str | None = None


class AppOpenSpreadCardRequestSchema(BaseModel):
    vk_user_id: int = Field(ge=1)
    card_number: int = Field(ge=1)


class AppOpenSpreadCardByIdRequestSchema(BaseModel):
    vk_user_id: int = Field(ge=1)
    spread_id: int = Field(ge=1)
    card_number: int = Field(ge=1)


class AppOpenSpreadCardResponseSchema(BaseModel):
    ok: bool
    opened_card: OpenedCardSchema | None = None
    user_open: UserOpenSchema | None = None
    message: str | None = None
    open_date: str | None = None
    project_timezone: str | None = None