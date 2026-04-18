from __future__ import annotations

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    PROJECT_NAME: str = "VK Mini App Карта Дня API"
    APP_NAME: str = "VK Mini App Карта Дня API"
    APP_VERSION: str = "0.1.0"

    API_PREFIX: str = "/api"
    API_V1_STR: str = "/api"

    DATABASE_URL: str | None = None
    SQLALCHEMY_DATABASE_URL: str | None = None

    PROJECT_TIMEZONE: str = "Europe/Moscow"

    DECK_CLEANUP_ENABLED: bool = False
    DECK_CLEANUP_RUN_ON_STARTUP: bool = True
    DECK_CLEANUP_INTERVAL_SECONDS: int = Field(default=300, ge=1)
    DECK_CLEANUP_BATCH_LIMIT: int = Field(default=100, ge=1, le=1000)
    DECK_CLEANUP_LOG_EACH_RUN: bool = False

    @model_validator(mode="after")
    def normalize_database_urls(self) -> "Settings":
        normalized = (
            (self.SQLALCHEMY_DATABASE_URL or self.DATABASE_URL or "sqlite:///./app.db")
            .strip()
        )

        self.DATABASE_URL = normalized
        self.SQLALCHEMY_DATABASE_URL = normalized
        self.PROJECT_TIMEZONE = (self.PROJECT_TIMEZONE or "Europe/Moscow").strip() or "Europe/Moscow"
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()