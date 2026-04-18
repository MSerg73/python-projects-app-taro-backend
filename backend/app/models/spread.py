from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class SpreadStatus(StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"


class SpreadKind(StrEnum):
    MAIN_DAILY = "main_daily"
    EXTRA_DAILY = "extra_daily"


class Spread(Base):
    __tablename__ = "spreads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    deck_id: Mapped[int] = mapped_column(
        ForeignKey("decks.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Карта дня",
        server_default="Карта дня",
    )

    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    spread_kind: Mapped[SpreadKind] = mapped_column(
        Enum(
            SpreadKind,
            name="spread_kind",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=SpreadKind.MAIN_DAILY,
        server_default=SpreadKind.MAIN_DAILY.value,
    )

    cards_count: Mapped[int] = mapped_column(Integer, nullable=False)

    card_numbers: Mapped[list[int]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    reversed_card_numbers: Mapped[list[int]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        server_default="[]",
    )

    active_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    active_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    status: Mapped[SpreadStatus] = mapped_column(
        Enum(
            SpreadStatus,
            name="spread_status",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        default=SpreadStatus.DRAFT,
        server_default=SpreadStatus.DRAFT.value,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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