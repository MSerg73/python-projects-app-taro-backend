from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, Enum, Integer, JSON, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class AppSettingKey(StrEnum):
    REVERSED_CARDS_ENABLED = "reversed_cards_enabled"
    WORKSPACE_BACKGROUND_COLOR = "workspace_background_color"
    SPREAD_BACKGROUND_IMAGE_URL = "spread_background_image_url"
    CARD_BACK_IMAGE_URL = "card_back_image_url"
    LOGO_IMAGE_URL = "logo_image_url"
    LOGO_POSITION_X = "logo_position_x"
    LOGO_POSITION_Y = "logo_position_y"


class AppSetting(Base):
    __tablename__ = "app_settings"
    __table_args__ = (
        UniqueConstraint("key", name="uq_app_settings_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    key: Mapped[AppSettingKey] = mapped_column(
        Enum(
            AppSettingKey,
            name="app_setting_key",
            values_callable=lambda enum_cls: [item.value for item in enum_cls],
        ),
        nullable=False,
        index=True,
    )

    value_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)

    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

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