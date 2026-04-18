from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class DeckStatus(StrEnum):
    DRAFT = "draft"
    READY = "ready"


class Deck(Base):
    __tablename__ = "decks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    cards_total_expected: Mapped[int] = mapped_column(Integer, nullable=False)
    cards_total_actual: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    status: Mapped[DeckStatus] = mapped_column(
        Enum(
            DeckStatus,
            name="deck_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=DeckStatus.DRAFT,
        server_default=DeckStatus.DRAFT.value,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pending_hard_delete_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hard_delete_reminder_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hard_delete_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )