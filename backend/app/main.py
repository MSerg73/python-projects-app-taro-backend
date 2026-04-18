from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.app.api.app import router as app_router
from backend.app.api.admin.cards import router as admin_cards_router
from backend.app.api.admin.decks import router as admin_decks_router
from backend.app.api.admin.logs import router as admin_logs_router
from backend.app.api.admin.settings import router as admin_settings_router
from backend.app.api.admin.spreads import router as admin_spreads_router
from backend.app.api.admin.uploads import router as admin_uploads_router
from backend.app.core.config import settings
from backend.app.services.deck_cleanup import run_deck_cleanup_loop, run_deck_cleanup_once

BACKEND_ROOT = Path(__file__).resolve().parents[1]
UPLOADS_ROOT = BACKEND_ROOT / "uploads"

_cleanup_stop_event: asyncio.Event | None = None
_cleanup_task: asyncio.Task | None = None


def ensure_uploads_dirs() -> None:
    UPLOADS_ROOT.mkdir(parents=True, exist_ok=True)
    (UPLOADS_ROOT / "spread-backgrounds").mkdir(parents=True, exist_ok=True)
    (UPLOADS_ROOT / "card-images").mkdir(parents=True, exist_ok=True)
    (UPLOADS_ROOT / "card-backs").mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _cleanup_stop_event, _cleanup_task

    ensure_uploads_dirs()

    if settings.DECK_CLEANUP_ENABLED:
        if settings.DECK_CLEANUP_RUN_ON_STARTUP:
            run_deck_cleanup_once(batch_limit=settings.DECK_CLEANUP_BATCH_LIMIT)

        _cleanup_stop_event = asyncio.Event()
        _cleanup_task = asyncio.create_task(
            run_deck_cleanup_loop(
                interval_seconds=settings.DECK_CLEANUP_INTERVAL_SECONDS,
                batch_limit=settings.DECK_CLEANUP_BATCH_LIMIT,
                log_each_run=settings.DECK_CLEANUP_LOG_EACH_RUN,
                stop_event=_cleanup_stop_event,
            )
        )

    try:
        yield
    finally:
        if _cleanup_stop_event is not None:
            _cleanup_stop_event.set()

        if _cleanup_task is not None:
            try:
                await _cleanup_task
            except Exception:
                pass

        _cleanup_stop_event = None
        _cleanup_task = None


def create_app() -> FastAPI:
    ensure_uploads_dirs()

    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/uploads", StaticFiles(directory=str(UPLOADS_ROOT)), name="uploads")

    app.include_router(app_router, prefix=settings.API_PREFIX)
    app.include_router(admin_decks_router, prefix=f"{settings.API_PREFIX}/admin/decks")
    app.include_router(admin_cards_router, prefix=f"{settings.API_PREFIX}/admin/cards")
    app.include_router(admin_spreads_router, prefix=f"{settings.API_PREFIX}/admin/spreads")
    app.include_router(admin_logs_router, prefix=f"{settings.API_PREFIX}/admin/logs")
    app.include_router(admin_settings_router, prefix=f"{settings.API_PREFIX}/admin/settings")
    app.include_router(admin_uploads_router, prefix=f"{settings.API_PREFIX}/admin/uploads")

    return app


app = create_app()