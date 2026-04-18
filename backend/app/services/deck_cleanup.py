from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal
from backend.app.models.card import Card
from backend.app.models.deck import Deck
from backend.app.models.spread import Spread
from backend.app.models.user_daily_open import UserDailyOpen

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def run_deck_cleanup_once(batch_limit: int = 100) -> dict[str, int]:
    now = utc_now()
    deleted_count = 0
    safe_batch_limit = max(1, int(batch_limit))

    with SessionLocal() as db:  # type: Session
        stmt = (
            select(Deck)
            .where(
                Deck.deleted_at.is_not(None),
                Deck.hard_delete_confirmed.is_(True),
                Deck.pending_hard_delete_at.is_not(None),
                Deck.pending_hard_delete_at <= now,
            )
            .order_by(Deck.pending_hard_delete_at.asc(), Deck.id.asc())
            .limit(safe_batch_limit)
        )

        decks = list(db.scalars(stmt).all())

        for deck in decks:
            spread_ids_subquery = select(Spread.id).where(Spread.deck_id == deck.id)

            db.execute(
                delete(UserDailyOpen).where(
                    UserDailyOpen.spread_id.in_(spread_ids_subquery)
                )
            )
            db.execute(delete(Spread).where(Spread.deck_id == deck.id))
            db.execute(delete(Card).where(Card.deck_id == deck.id))
            db.delete(deck)

            deleted_count += 1

        if deleted_count > 0:
            db.commit()

    return {
        "deleted_count": deleted_count,
    }


async def run_deck_cleanup_loop(
    *,
    interval_seconds: int = 300,
    batch_limit: int = 100,
    log_each_run: bool = False,
    stop_event: asyncio.Event | None = None,
) -> None:
    safe_interval = max(1, int(interval_seconds))
    safe_batch_limit = max(1, int(batch_limit))

    while True:
        try:
            result = run_deck_cleanup_once(batch_limit=safe_batch_limit)

            if log_each_run:
                logger.info("Deck cleanup run finished: %s", result)
        except Exception:
            logger.exception("Deck cleanup run failed")

        if stop_event is None:
            await asyncio.sleep(safe_interval)
            continue

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=safe_interval)
            break
        except asyncio.TimeoutError:
            continue