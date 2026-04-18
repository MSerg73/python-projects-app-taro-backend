from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CardCreateSchema(BaseModel):
    deck_id: int = Field(ge=1)
    number: int = Field(ge=1)
    name: str | None = Field(default=None, max_length=255)
    image_url: str | None = None
    description: str | None = None
    reversed_description: str | None = None


class CardUpdateSchema(BaseModel):
    number: int | None = Field(default=None, ge=1)
    name: str | None = Field(default=None, max_length=255)
    image_url: str | None = None
    description: str | None = None
    reversed_description: str | None = None


class CardListItemSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    deck_id: int
    number: int
    name: str
    image_url: str | None
    description: str | None
    reversed_description: str | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CardDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    deck_id: int
    number: int
    name: str
    image_url: str | None
    description: str | None
    reversed_description: str | None
    deleted_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CardMutationResponseSchema(BaseModel):
    ok: bool
    message: str | None = None
    item: CardDetailSchema | None = None


class CardListResponseSchema(BaseModel):
    items: list[CardListItemSchema]