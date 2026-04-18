from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class UserDailyOpen(Base):
    __tablename__ = "user_daily_opens"
    __table_args__ = (
        UniqueConstraint(
            "vk_user_id",
            "spread_id",
            "open_date",
            name="uq_user_daily_opens_vk_user_id_spread_id_open_date",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    vk_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    spread_id: Mapped[int] = mapped_column(
        ForeignKey("spreads.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    opened_card_number: Mapped[int] = mapped_column(Integer, nullable=False)

    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    open_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)