from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Select, exists, select
from sqlalchemy.orm import Session

from backend.app.models.card import Card
from backend.app.models.deck import Deck
from backend.app.models.spread import Spread
from backend.app.schemas.card import CardCreateSchema, CardUpdateSchema
from backend.app.services.admin_logs import create_admin_log
from backend.app.services.decks import recalculate_deck_stats


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None

    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _active_cards_stmt(deck_id: int) -> Select[tuple[Card]]:
    return (
        select(Card)
        .where(
            Card.deck_id == deck_id,
            Card.deleted_at.is_(None),
        )
        .order_by(Card.number.asc(), Card.id.asc())
    )


def _get_deck_or_404(db: Session, deck_id: int) -> Deck:
    deck = db.scalar(
        select(Deck).where(
            Deck.id == deck_id,
            Deck.deleted_at.is_(None),
        )
    )
    if deck is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Колода не найдена",
        )
    return deck


def _get_card_or_404(db: Session, card_id: int, *, include_deleted: bool = False) -> Card:
    stmt = select(Card).where(Card.id == card_id)

    if not include_deleted:
        stmt = stmt.where(Card.deleted_at.is_(None))

    card = db.scalar(stmt)

    if card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Карта не найдена",
        )

    return card


def _normalize_card_name(value: str | None) -> str:
    if value is None:
        return ""

    normalized = value.strip()

    if len(normalized) > 255:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Название карты слишком длинное",
        )

    return normalized


def _validate_card_number(number: int, *, expected_total: int) -> int:
    if number < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Номер карты должен быть не меньше 1",
        )

    if number > expected_total:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Номер карты выходит за диапазон колоды 1..{expected_total}",
        )

    return number


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = value.strip()
    return normalized or None


def _ensure_card_has_any_content(
    *,
    name: str,
    image_url: str | None,
    description: str | None,
    reversed_description: str | None,
) -> None:
    if name or image_url or description or reversed_description:
        return

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Нельзя сохранить полностью пустую карту",
    )


def _card_number_exists(
    db: Session,
    *,
    deck_id: int,
    number: int,
    exclude_card_id: int | None = None,
) -> bool:
    stmt = select(
        exists().where(
            Card.deck_id == deck_id,
            Card.number == number,
            Card.deleted_at.is_(None),
        )
    )

    if exclude_card_id is not None:
        stmt = select(
            exists().where(
                Card.deck_id == deck_id,
                Card.number == number,
                Card.deleted_at.is_(None),
                Card.id != exclude_card_id,
            )
        )

    return bool(db.scalar(stmt))


def _get_deleted_card_by_deck_and_number(
    db: Session,
    *,
    deck_id: int,
    number: int,
) -> Card | None:
    return db.scalar(
        select(Card)
        .where(
            Card.deck_id == deck_id,
            Card.number == number,
            Card.deleted_at.is_not(None),
        )
        .order_by(Card.updated_at.desc(), Card.id.desc())
    )


def _spread_is_active_or_planned(spread: Spread, *, now: datetime) -> bool:
    if spread.deleted_at is not None:
        return False

    active_from = _normalize_datetime(spread.active_from)
    active_to = _normalize_datetime(spread.active_to)

    if active_from is None or active_to is None:
        return False

    return active_to > now


def _card_used_in_active_or_planned_spread(db: Session, card: Card) -> bool:
    now = _utc_now()

    spreads = list(
        db.scalars(
            select(Spread).where(
                Spread.deck_id == card.deck_id,
                Spread.deleted_at.is_(None),
            )
        ).all()
    )

    return any(
        _spread_is_active_or_planned(spread, now=now)
        and card.number in (spread.card_numbers or [])
        for spread in spreads
    )


def _serialize_card_for_log(card: Card) -> dict[str, Any]:
    return {
        "id": card.id,
        "deck_id": card.deck_id,
        "number": card.number,
        "name": card.name,
        "image_url": card.image_url,
        "description": card.description,
        "reversed_description": card.reversed_description,
        "deleted_at": card.deleted_at.isoformat() if card.deleted_at else None,
    }


def _write_card_log(
    db: Session,
    *,
    admin_vk_user_id: int | None,
    action: str,
    card: Card,
    details: dict[str, Any] | None = None,
) -> None:
    if admin_vk_user_id is None:
        return

    create_admin_log(
        db,
        admin_vk_user_id=admin_vk_user_id,
        entity_type="card",
        entity_id=card.id,
        action=action,
        details=details,
    )


def list_cards(db: Session, deck_id: int) -> list[Card]:
    _get_deck_or_404(db, deck_id)

    return list(db.scalars(_active_cards_stmt(deck_id)).all())


def get_card(db: Session, card_id: int, *, include_deleted: bool = False) -> Card:
    return _get_card_or_404(db, card_id, include_deleted=include_deleted)


def create_card(
    db: Session,
    payload: CardCreateSchema,
    *,
    admin_vk_user_id: int | None = None,
) -> Card:
    deck = _get_deck_or_404(db, payload.deck_id)

    number = _validate_card_number(
        payload.number,
        expected_total=deck.cards_total_expected,
    )

    if _card_number_exists(db, deck_id=deck.id, number=number):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Карта с номером {number} уже существует в этой колоде",
        )

    normalized_name = _normalize_card_name(payload.name)
    normalized_image_url = _normalize_optional_text(payload.image_url)
    normalized_description = _normalize_optional_text(payload.description)
    normalized_reversed_description = _normalize_optional_text(payload.reversed_description)

    _ensure_card_has_any_content(
        name=normalized_name,
        image_url=normalized_image_url,
        description=normalized_description,
        reversed_description=normalized_reversed_description,
    )

    deleted_card_with_same_number = _get_deleted_card_by_deck_and_number(
        db,
        deck_id=deck.id,
        number=number,
    )

    if deleted_card_with_same_number is not None:
        before = _serialize_card_for_log(deleted_card_with_same_number)

        deleted_card_with_same_number.name = normalized_name
        deleted_card_with_same_number.image_url = normalized_image_url
        deleted_card_with_same_number.description = normalized_description
        deleted_card_with_same_number.reversed_description = normalized_reversed_description
        deleted_card_with_same_number.deleted_at = None

        db.add(deleted_card_with_same_number)
        db.flush()

        recalculate_deck_stats(db, deck)

        _write_card_log(
            db,
            admin_vk_user_id=admin_vk_user_id,
            action="restore",
            card=deleted_card_with_same_number,
            details={
                "before": before,
                "after": _serialize_card_for_log(deleted_card_with_same_number),
                "restored_by_create": True,
            },
        )

        db.commit()
        db.refresh(deleted_card_with_same_number)
        db.refresh(deck)

        return deleted_card_with_same_number

    card = Card(
        deck_id=deck.id,
        number=number,
        name=normalized_name,
        image_url=normalized_image_url,
        description=normalized_description,
        reversed_description=normalized_reversed_description,
    )

    db.add(card)
    db.flush()

    recalculate_deck_stats(db, deck)

    _write_card_log(
        db,
        admin_vk_user_id=admin_vk_user_id,
        action="create",
        card=card,
        details={
            "before": None,
            "after": _serialize_card_for_log(card),
        },
    )

    db.commit()
    db.refresh(card)
    db.refresh(deck)

    return card


def update_card(
    db: Session,
    card_id: int,
    payload: CardUpdateSchema,
    *,
    admin_vk_user_id: int | None = None,
) -> Card:
    card = _get_card_or_404(db, card_id)
    deck = _get_deck_or_404(db, card.deck_id)
    before = _serialize_card_for_log(card)

    update_data = payload.model_dump(exclude_unset=True)

    number_changed = (
        "number" in update_data
        and update_data["number"] is not None
        and update_data["number"] != card.number
    )
    content_changed = any(
        field in update_data
        for field in ("name", "image_url", "description", "reversed_description")
    )

    if (number_changed or content_changed) and _card_used_in_active_or_planned_spread(db, card):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Нельзя редактировать карту, которая участвует в активном или запланированном раскладе",
        )

    if "number" in update_data and update_data["number"] is not None:
        new_number = _validate_card_number(
            int(update_data["number"]),
            expected_total=deck.cards_total_expected,
        )

        if _card_number_exists(
            db,
            deck_id=deck.id,
            number=new_number,
            exclude_card_id=card.id,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Карта с номером {new_number} уже существует в этой колоде",
            )

        card.number = new_number

    next_name = card.name
    next_image_url = card.image_url
    next_description = card.description
    next_reversed_description = card.reversed_description

    if "name" in update_data:
        next_name = _normalize_card_name(update_data["name"])

    if "image_url" in update_data:
        next_image_url = _normalize_optional_text(update_data["image_url"])

    if "description" in update_data:
        next_description = _normalize_optional_text(update_data["description"])

    if "reversed_description" in update_data:
        next_reversed_description = _normalize_optional_text(update_data["reversed_description"])

    _ensure_card_has_any_content(
        name=next_name,
        image_url=next_image_url,
        description=next_description,
        reversed_description=next_reversed_description,
    )

    if "name" in update_data:
        card.name = next_name

    if "image_url" in update_data:
        card.image_url = next_image_url

    if "description" in update_data:
        card.description = next_description

    if "reversed_description" in update_data:
        card.reversed_description = next_reversed_description

    db.add(card)
    db.flush()

    recalculate_deck_stats(db, deck)

    after = _serialize_card_for_log(card)

    if before != after:
        _write_card_log(
            db,
            admin_vk_user_id=admin_vk_user_id,
            action="update",
            card=card,
            details={
                "before": before,
                "after": after,
            },
        )

    db.commit()
    db.refresh(card)
    db.refresh(deck)

    return card


def soft_delete_card(
    db: Session,
    card_id: int,
    *,
    admin_vk_user_id: int | None = None,
) -> Card:
    card = _get_card_or_404(db, card_id)
    deck = _get_deck_or_404(db, card.deck_id)
    before = _serialize_card_for_log(card)

    if _card_used_in_active_or_planned_spread(db, card):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Нельзя удалить карту, которая участвует в активном или запланированном раскладе",
        )

    card.deleted_at = _utc_now()

    db.add(card)
    db.flush()

    recalculate_deck_stats(db, deck)

    _write_card_log(
        db,
        admin_vk_user_id=admin_vk_user_id,
        action="soft_delete",
        card=card,
        details={
            "before": before,
            "after": _serialize_card_for_log(card),
        },
    )

    db.commit()
    db.refresh(card)
    db.refresh(deck)

    return card


def restore_card(
    db: Session,
    card_id: int,
    *,
    admin_vk_user_id: int | None = None,
) -> Card:
    card = _get_card_or_404(db, card_id, include_deleted=True)
    deck = _get_deck_or_404(db, card.deck_id)
    before = _serialize_card_for_log(card)

    if card.deleted_at is None:
        return card

    _validate_card_number(card.number, expected_total=deck.cards_total_expected)

    if _card_number_exists(
        db,
        deck_id=deck.id,
        number=card.number,
        exclude_card_id=card.id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Нельзя восстановить карту: номер {card.number} уже занят",
        )

    card.deleted_at = None

    _ensure_card_has_any_content(
        name=card.name or "",
        image_url=card.image_url,
        description=card.description,
        reversed_description=card.reversed_description,
    )

    db.add(card)
    db.flush()

    recalculate_deck_stats(db, deck)

    _write_card_log(
        db,
        admin_vk_user_id=admin_vk_user_id,
        action="restore",
        card=card,
        details={
            "before": before,
            "after": _serialize_card_for_log(card),
        },
    )

    db.commit()
    db.refresh(card)
    db.refresh(deck)

    return card