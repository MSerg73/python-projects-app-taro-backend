from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, exists, func, select
from sqlalchemy.orm import Session

from backend.app.models.card import Card
from backend.app.models.deck import Deck, DeckStatus
from backend.app.models.spread import Spread
from backend.app.schemas.deck import DeckCreateSchema, DeckUpdateSchema
from backend.app.services.admin_logs import create_admin_log


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None

    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _active_cards_stmt(deck_id: int) -> Select[tuple[Card]]:
    return select(Card).where(
        Card.deck_id == deck_id,
        Card.deleted_at.is_(None),
    )


def _spread_is_active_or_planned(spread: Spread, *, now: datetime) -> bool:
    if spread.deleted_at is not None:
        return False

    active_from = _normalize_datetime(spread.active_from)
    active_to = _normalize_datetime(spread.active_to)

    if active_from is None or active_to is None:
        return False

    return active_to > now


def _deck_has_active_or_planned_spreads(db: Session, deck_id: int) -> bool:
    now = _utc_now()

    spreads = list(
        db.scalars(
            select(Spread).where(
                Spread.deck_id == deck_id,
                Spread.deleted_at.is_(None),
            )
        ).all()
    )

    return any(_spread_is_active_or_planned(spread, now=now) for spread in spreads)


def _validate_expected_cards_total(value: int) -> None:
    if value < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Общее количество карт должно быть не меньше 1",
        )


def _validate_deck_name(value: str) -> str:
    normalized = value.strip()

    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Название колоды обязательно",
        )

    if len(normalized) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Название колоды слишком длинное",
        )

    return normalized


def _validate_soft_delete_periods(
    retention_days: int,
    reminder_days_before: int,
) -> tuple[int, int]:
    if retention_days < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Срок хранения удалённой колоды должен быть не меньше 1 дня",
        )

    if reminder_days_before < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Срок напоминания не может быть отрицательным",
        )

    if reminder_days_before >= retention_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Напоминание должно наступать раньше окончательного удаления",
        )

    return retention_days, reminder_days_before


def _get_deck_or_404(db: Session, deck_id: int, *, include_deleted: bool = False) -> Deck:
    stmt = select(Deck).where(Deck.id == deck_id)

    if not include_deleted:
        stmt = stmt.where(Deck.deleted_at.is_(None))

    deck = db.scalar(stmt)

    if deck is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Колода не найдена",
        )

    return deck


def _serialize_deck_for_log(deck: Deck) -> dict[str, Any]:
    return {
        "id": deck.id,
        "name": deck.name,
        "cards_total_expected": deck.cards_total_expected,
        "cards_total_actual": deck.cards_total_actual,
        "status": deck.status.value if isinstance(deck.status, DeckStatus) else str(deck.status),
        "deleted_at": deck.deleted_at.isoformat() if deck.deleted_at else None,
        "pending_hard_delete_at": (
            deck.pending_hard_delete_at.isoformat() if deck.pending_hard_delete_at else None
        ),
        "hard_delete_reminder_at": (
            deck.hard_delete_reminder_at.isoformat() if deck.hard_delete_reminder_at else None
        ),
        "hard_delete_confirmed": deck.hard_delete_confirmed,
    }


def _write_deck_log(
    db: Session,
    *,
    admin_vk_user_id: int | None,
    action: str,
    deck: Deck,
    details: dict[str, Any] | None = None,
) -> None:
    if admin_vk_user_id is None:
        return

    create_admin_log(
        db,
        admin_vk_user_id=admin_vk_user_id,
        entity_type="deck",
        entity_id=deck.id,
        action=action,
        details=details,
    )


def recalculate_deck_stats(db: Session, deck: Deck) -> Deck:
    cards = list(db.scalars(_active_cards_stmt(deck.id)).all())

    unique_numbers = {card.number for card in cards}
    expected_numbers = set(range(1, deck.cards_total_expected + 1))

    all_numbers_in_range = all(1 <= number <= deck.cards_total_expected for number in unique_numbers)
    numbers_match_expected = unique_numbers == expected_numbers
    count_matches_expected = len(unique_numbers) == deck.cards_total_expected

    all_cards_complete = (
        len(cards) == deck.cards_total_expected
        and all(card.name.strip() for card in cards)
        and all((card.image_url or "").strip() for card in cards)
        and all((card.description or "").strip() for card in cards)
    )

    deck.cards_total_actual = len(unique_numbers)
    deck.status = (
        DeckStatus.READY
        if count_matches_expected and all_numbers_in_range and numbers_match_expected and all_cards_complete
        else DeckStatus.DRAFT
    )

    db.add(deck)
    db.flush()

    return deck


def list_decks(db: Session, *, include_deleted: bool = False) -> list[Deck]:
    stmt = select(Deck).order_by(Deck.created_at.desc(), Deck.id.desc())

    if not include_deleted:
        stmt = stmt.where(Deck.deleted_at.is_(None))

    items = list(db.scalars(stmt).all())

    for item in items:
        if item.deleted_at is None:
            recalculate_deck_stats(db, item)

    db.commit()

    for item in items:
        db.refresh(item)

    return items


def get_deck(db: Session, deck_id: int, *, include_deleted: bool = False) -> Deck:
    deck = _get_deck_or_404(db, deck_id, include_deleted=include_deleted)

    if deck.deleted_at is None:
        recalculate_deck_stats(db, deck)
        db.commit()
        db.refresh(deck)

    return deck


def create_deck(
    db: Session,
    payload: DeckCreateSchema,
    *,
    admin_vk_user_id: int | None = None,
) -> Deck:
    _validate_expected_cards_total(payload.cards_total_expected)
    name = _validate_deck_name(payload.name)

    deck = Deck(
        name=name,
        cards_total_expected=payload.cards_total_expected,
        cards_total_actual=0,
        status=DeckStatus.DRAFT,
        hard_delete_confirmed=False,
    )

    db.add(deck)
    db.flush()

    recalculate_deck_stats(db, deck)

    _write_deck_log(
        db,
        admin_vk_user_id=admin_vk_user_id,
        action="create",
        deck=deck,
        details={
            "before": None,
            "after": _serialize_deck_for_log(deck),
        },
    )

    db.commit()
    db.refresh(deck)

    return deck


def update_deck(
    db: Session,
    deck_id: int,
    payload: DeckUpdateSchema,
    *,
    admin_vk_user_id: int | None = None,
) -> Deck:
    deck = _get_deck_or_404(db, deck_id)
    before = _serialize_deck_for_log(deck)

    update_data = payload.model_dump(exclude_unset=True)

    if "name" in update_data and update_data["name"] is not None:
        deck.name = _validate_deck_name(update_data["name"])

    if "cards_total_expected" in update_data and update_data["cards_total_expected"] is not None:
        new_total = int(update_data["cards_total_expected"])
        _validate_expected_cards_total(new_total)

        if new_total != deck.cards_total_expected and _deck_has_active_or_planned_spreads(db, deck.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Нельзя менять общее количество карт у колоды, которая участвует в активном или запланированном раскладе",
            )

        deck.cards_total_expected = new_total

    db.add(deck)
    db.flush()

    recalculate_deck_stats(db, deck)

    after = _serialize_deck_for_log(deck)

    if before != after:
        _write_deck_log(
            db,
            admin_vk_user_id=admin_vk_user_id,
            action="update",
            deck=deck,
            details={
                "before": before,
                "after": after,
            },
        )

    db.commit()
    db.refresh(deck)

    return deck


def soft_delete_deck(
    db: Session,
    deck_id: int,
    *,
    retention_days: int,
    reminder_days_before: int,
    confirm: bool,
    admin_vk_user_id: int | None = None,
) -> Deck:
    deck = _get_deck_or_404(db, deck_id)
    before = _serialize_deck_for_log(deck)

    if not confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Удаление колоды требует явного подтверждения",
        )

    _validate_soft_delete_periods(retention_days, reminder_days_before)

    if _deck_has_active_or_planned_spreads(db, deck.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Нельзя удалить колоду, которая участвует в активном или запланированном раскладе",
        )

    now = _utc_now()
    pending_hard_delete_at = now + timedelta(days=retention_days)
    hard_delete_reminder_at = pending_hard_delete_at - timedelta(days=reminder_days_before)

    deck.deleted_at = now
    deck.pending_hard_delete_at = pending_hard_delete_at
    deck.hard_delete_reminder_at = hard_delete_reminder_at
    deck.hard_delete_confirmed = True

    db.add(deck)
    db.flush()

    _write_deck_log(
        db,
        admin_vk_user_id=admin_vk_user_id,
        action="soft_delete",
        deck=deck,
        details={
            "before": before,
            "after": _serialize_deck_for_log(deck),
            "retention_days": retention_days,
            "reminder_days_before": reminder_days_before,
        },
    )

    db.commit()
    db.refresh(deck)

    return deck


def restore_deck(
    db: Session,
    deck_id: int,
    *,
    admin_vk_user_id: int | None = None,
) -> Deck:
    deck = _get_deck_or_404(db, deck_id, include_deleted=True)
    before = _serialize_deck_for_log(deck)

    if deck.deleted_at is None:
        recalculate_deck_stats(db, deck)
        db.commit()
        db.refresh(deck)
        return deck

    deck.deleted_at = None
    deck.pending_hard_delete_at = None
    deck.hard_delete_reminder_at = None
    deck.hard_delete_confirmed = False

    db.add(deck)
    db.flush()

    recalculate_deck_stats(db, deck)

    _write_deck_log(
        db,
        admin_vk_user_id=admin_vk_user_id,
        action="restore",
        deck=deck,
        details={
            "before": before,
            "after": _serialize_deck_for_log(deck),
        },
    )

    db.commit()
    db.refresh(deck)

    return deck


def count_active_cards(db: Session, deck_id: int) -> int:
    stmt = select(func.count()).select_from(
        select(Card.id)
        .where(
            Card.deck_id == deck_id,
            Card.deleted_at.is_(None),
        )
        .subquery()
    )
    return int(db.scalar(stmt) or 0)