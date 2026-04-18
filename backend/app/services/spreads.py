from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.admin_log import AdminLog
from backend.app.models.deck import Deck, DeckStatus
from backend.app.models.spread import Spread, SpreadKind, SpreadStatus
from backend.app.models.user_daily_open import UserDailyOpen
from backend.app.schemas.spread import SpreadCreateSchema, SpreadUpdateSchema


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _get_project_timezone() -> tzinfo:
    timezone_name = (settings.PROJECT_TIMEZONE or "").strip()

    if timezone_name:
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError:
            pass

    return timezone.utc


def _project_today(now: datetime) -> datetime.date:
    project_timezone = _get_project_timezone()
    return now.astimezone(project_timezone).date()


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None

    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _project_date_from_datetime(value: datetime | None) -> datetime.date | None:
    normalized_value = _normalize_datetime(value)
    if normalized_value is None:
        return None

    return normalized_value.astimezone(_get_project_timezone()).date()


def _resolve_spread_status(
    *,
    active_from: datetime | None,
    active_to: datetime | None,
    now: datetime | None = None,
) -> SpreadStatus:
    current_time = now or _utc_now()
    today = _project_today(current_time)

    active_from_date = _project_date_from_datetime(active_from)
    active_to_date = _project_date_from_datetime(active_to)

    if active_from_date is None or active_to_date is None:
        return SpreadStatus.DRAFT

    if today < active_from_date:
        return SpreadStatus.SCHEDULED

    if active_from_date <= today < active_to_date:
        return SpreadStatus.ACTIVE

    return SpreadStatus.COMPLETED


def _sync_spread_status(db: Session, spread: Spread, *, now: datetime) -> None:
    next_status = _resolve_spread_status(
        active_from=spread.active_from,
        active_to=spread.active_to,
        now=now,
    )

    if spread.status == next_status:
        return

    spread.status = next_status
    db.add(spread)
    db.flush()


def _get_spread_or_404(db: Session, spread_id: int) -> Spread:
    spread = db.scalar(
        select(Spread).where(
            Spread.id == spread_id,
            Spread.deleted_at.is_(None),
        )
    )

    if spread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Расклад не найден",
        )

    return spread


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


def _validate_spread_title(raw_title: str | None, *, spread_kind: SpreadKind) -> str:
    if spread_kind == SpreadKind.MAIN_DAILY:
        return "Карта дня"

    title = (raw_title or "").strip()
    if not title:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Укажите название расклада",
        )

    if len(title) > 255:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Название расклада слишком длинное",
        )

    return title


def _normalize_spread_description(raw_description: str | None) -> str | None:
    if raw_description is None:
        return None

    normalized = raw_description.strip()
    return normalized or None


def _normalize_spread_kind(value: SpreadKind | str | None) -> SpreadKind:
    if isinstance(value, SpreadKind):
        return value

    if isinstance(value, str):
        try:
            return SpreadKind(value)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Некорректный тип расклада",
            ) from exc

    return SpreadKind.MAIN_DAILY


def _validate_spread_period(
    *,
    active_from: datetime | None,
    active_to: datetime | None,
) -> tuple[datetime | None, datetime | None]:
    normalized_active_from = _normalize_datetime(active_from)
    normalized_active_to = _normalize_datetime(active_to)

    if normalized_active_from is None and normalized_active_to is None:
        return None, None

    if normalized_active_from is None or normalized_active_to is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Для периода расклада нужно указать и active_from, и active_to",
        )

    if normalized_active_to <= normalized_active_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Дата окончания расклада должна быть позже даты начала",
        )

    return normalized_active_from, normalized_active_to


def _normalize_card_numbers(
    *,
    deck: Deck,
    cards_count: int,
    card_numbers: list[int],
) -> list[int]:
    normalized_numbers: list[int] = []
    seen_numbers: set[int] = set()

    for raw_number in card_numbers:
        try:
            number = int(raw_number)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Номера карт должны быть целыми числами",
            ) from exc

        if number <= 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Номер карты должен быть больше нуля",
            )

        if number in seen_numbers:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Номера карт не должны повторяться",
            )

        if number > deck.cards_total_expected:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Номер карты {number} выходит за пределы колоды",
            )

        seen_numbers.add(number)
        normalized_numbers.append(number)

    if len(normalized_numbers) != cards_count:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Количество номеров карт не совпадает с cards_count",
        )

    return normalized_numbers


def _normalize_reversed_card_numbers(
    reversed_card_numbers: list[int] | None,
    card_numbers: list[int],
) -> list[int]:
    allowed_numbers = set(card_numbers)
    normalized_numbers: list[int] = []
    seen_numbers: set[int] = set()

    for raw_number in reversed_card_numbers or []:
        try:
            number = int(raw_number)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Номера перевёрнутых карт должны быть целыми числами",
            ) from exc

        if number in seen_numbers:
            continue

        if number not in allowed_numbers:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Перевёрнутые карты должны входить в состав расклада",
            )

        seen_numbers.add(number)
        normalized_numbers.append(number)

    return normalized_numbers


def _ensure_deck_ready(deck: Deck) -> None:
    if deck.status != DeckStatus.READY:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Для расклада можно использовать только готовую колоду",
        )


def _periods_overlap(
    existing_from: datetime | None,
    existing_to: datetime | None,
    new_from: datetime | None,
    new_to: datetime | None,
) -> bool:
    existing_from_date = _project_date_from_datetime(existing_from)
    existing_to_date = _project_date_from_datetime(existing_to)
    new_from_date = _project_date_from_datetime(new_from)
    new_to_date = _project_date_from_datetime(new_to)

    if (
        existing_from_date is None
        or existing_to_date is None
        or new_from_date is None
        or new_to_date is None
    ):
        return False

    return existing_from_date < new_to_date and new_from_date < existing_to_date


def _spread_blocks_period_conflict(
    spread: Spread,
    *,
    now: datetime,
) -> bool:
    if spread.deleted_at is not None:
        return False

    active_from_date = _project_date_from_datetime(spread.active_from)
    active_to_date = _project_date_from_datetime(spread.active_to)

    if active_from_date is None or active_to_date is None:
        return False

    today = _project_today(now)

    return active_to_date > today


def _spreads_conflict_by_kind(
    *,
    existing_spread_kind: SpreadKind,
    target_spread_kind: SpreadKind,
) -> bool:
    return (
        existing_spread_kind == SpreadKind.MAIN_DAILY
        and target_spread_kind == SpreadKind.MAIN_DAILY
    )


def _spread_has_period_conflict(
    db: Session,
    *,
    spread_kind: SpreadKind,
    active_from: datetime | None,
    active_to: datetime | None,
    now: datetime,
    exclude_spread_id: int | None = None,
) -> bool:
    normalized_active_from = _normalize_datetime(active_from)
    normalized_active_to = _normalize_datetime(active_to)

    if normalized_active_from is None or normalized_active_to is None:
        return False

    stmt = select(Spread).where(Spread.deleted_at.is_(None))

    if exclude_spread_id is not None:
        stmt = stmt.where(Spread.id != exclude_spread_id)

    spreads = list(db.scalars(stmt).all())

    return any(
        _spread_blocks_period_conflict(existing, now=now)
        and _spreads_conflict_by_kind(
            existing_spread_kind=existing.spread_kind,
            target_spread_kind=spread_kind,
        )
        and _periods_overlap(
            existing.active_from,
            existing.active_to,
            normalized_active_from,
            normalized_active_to,
        )
        for existing in spreads
    )


def _get_latest_main_daily_blocking_end(
    db: Session,
    *,
    now: datetime,
    exclude_spread_id: int | None = None,
) -> datetime | None:
    stmt = select(Spread).where(
        Spread.deleted_at.is_(None),
        Spread.spread_kind == SpreadKind.MAIN_DAILY,
    )

    if exclude_spread_id is not None:
        stmt = stmt.where(Spread.id != exclude_spread_id)

    spreads = list(db.scalars(stmt).all())

    blocking_ends: list[datetime] = []

    for spread in spreads:
        if not _spread_blocks_period_conflict(spread, now=now):
            continue

        normalized_active_to = _normalize_datetime(spread.active_to)
        if normalized_active_to is not None:
            blocking_ends.append(normalized_active_to)

    if not blocking_ends:
        return None

    return max(blocking_ends)


def _resolve_main_daily_create_period(
    db: Session,
    *,
    spread_kind: SpreadKind,
    active_from: datetime | None,
    active_to: datetime | None,
    now: datetime,
) -> tuple[datetime | None, datetime | None]:
    normalized_active_from, normalized_active_to = _validate_spread_period(
        active_from=active_from,
        active_to=active_to,
    )

    if spread_kind != SpreadKind.MAIN_DAILY:
        return normalized_active_from, normalized_active_to

    if normalized_active_from is None or normalized_active_to is None:
        return normalized_active_from, normalized_active_to

    blocking_end = _get_latest_main_daily_blocking_end(
        db,
        now=now,
    )
    if blocking_end is None:
        return normalized_active_from, normalized_active_to

    if normalized_active_from >= blocking_end:
        return normalized_active_from, normalized_active_to

    duration = normalized_active_to - normalized_active_from
    if duration <= timedelta(0):
        duration = timedelta(days=1)

    shifted_active_from = blocking_end
    shifted_active_to = shifted_active_from + duration

    return shifted_active_from, shifted_active_to


def _serialize_spread_for_log(spread: Spread) -> dict[str, Any]:
    active_from = _normalize_datetime(spread.active_from)
    active_to = _normalize_datetime(spread.active_to)

    return {
        "id": spread.id,
        "deck_id": spread.deck_id,
        "title": spread.title,
        "description": spread.description,
        "spread_kind": spread.spread_kind.value
        if isinstance(spread.spread_kind, SpreadKind)
        else str(spread.spread_kind),
        "cards_count": spread.cards_count,
        "card_numbers": list(spread.card_numbers or []),
        "reversed_card_numbers": list(spread.reversed_card_numbers or []),
        "active_from": active_from.isoformat() if active_from else None,
        "active_to": active_to.isoformat() if active_to else None,
        "status": spread.status.value
        if isinstance(spread.status, SpreadStatus)
        else str(spread.status),
        "deleted_at": spread.deleted_at.isoformat() if spread.deleted_at else None,
        "created_at": spread.created_at.isoformat() if spread.created_at else None,
        "updated_at": spread.updated_at.isoformat() if spread.updated_at else None,
    }


def _write_spread_log(
    db: Session,
    *,
    admin_vk_user_id: int | None,
    action: str,
    spread: Spread,
    details: dict[str, Any],
) -> None:
    if admin_vk_user_id is None:
        return

    log_item = AdminLog(
        admin_vk_user_id=admin_vk_user_id,
        entity_type="spread",
        entity_id=spread.id,
        action=action,
        details=details,
    )
    db.add(log_item)
    db.flush()


def list_spreads(db: Session) -> list[Spread]:
    now = _utc_now()

    items = list(
        db.scalars(
            select(Spread)
            .where(Spread.deleted_at.is_(None))
            .order_by(Spread.active_from.desc(), Spread.id.desc())
        ).all()
    )

    for item in items:
        _sync_spread_status(db, item, now=now)

    db.commit()

    for item in items:
        db.refresh(item)

    return items


def get_spread(db: Session, spread_id: int) -> Spread:
    now = _utc_now()
    item = _get_spread_or_404(db, spread_id)

    _sync_spread_status(db, item, now=now)
    db.commit()
    db.refresh(item)

    return item


def create_spread(
    db: Session,
    payload: SpreadCreateSchema,
    *,
    admin_vk_user_id: int | None = None,
) -> Spread:
    now = _utc_now()

    deck = _get_deck_or_404(db, payload.deck_id)
    _ensure_deck_ready(deck)

    spread_kind = _normalize_spread_kind(payload.spread_kind)
    title = _validate_spread_title(payload.title, spread_kind=spread_kind)
    description = _normalize_spread_description(payload.description)

    active_from, active_to = _resolve_main_daily_create_period(
        db,
        spread_kind=spread_kind,
        active_from=payload.active_from,
        active_to=payload.active_to,
        now=now,
    )

    if _spread_has_period_conflict(
        db,
        spread_kind=spread_kind,
        active_from=active_from,
        active_to=active_to,
        now=now,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Период расклада пересекается с уже активным или запланированным основным раскладом",
        )

    card_numbers = _normalize_card_numbers(
        deck=deck,
        cards_count=payload.cards_count,
        card_numbers=payload.card_numbers,
    )
    reversed_card_numbers = _normalize_reversed_card_numbers(
        payload.reversed_card_numbers,
        card_numbers,
    )

    item = Spread(
        deck_id=deck.id,
        title=title,
        description=description,
        spread_kind=spread_kind,
        cards_count=payload.cards_count,
        card_numbers=card_numbers,
        reversed_card_numbers=reversed_card_numbers,
        active_from=active_from,
        active_to=active_to,
        status=_resolve_spread_status(
            active_from=active_from,
            active_to=active_to,
            now=now,
        ),
    )

    db.add(item)
    db.flush()

    _write_spread_log(
        db,
        admin_vk_user_id=admin_vk_user_id,
        action="create",
        spread=item,
        details={
            "before": None,
            "after": _serialize_spread_for_log(item),
        },
    )

    db.commit()
    db.refresh(item)

    return item


def update_spread(
    db: Session,
    spread_id: int,
    payload: SpreadUpdateSchema,
    *,
    admin_vk_user_id: int | None = None,
) -> Spread:
    now = _utc_now()

    item = _get_spread_or_404(db, spread_id)
    before = _serialize_spread_for_log(item)

    update_data = payload.model_dump(exclude_unset=True)

    next_deck_id = update_data.get("deck_id", item.deck_id)
    next_cards_count = update_data.get("cards_count", item.cards_count)
    next_card_numbers_input = update_data.get("card_numbers", list(item.card_numbers or []))
    next_reversed_input = update_data.get(
        "reversed_card_numbers",
        list(item.reversed_card_numbers or []),
    )
    next_spread_kind = _normalize_spread_kind(
        update_data.get("spread_kind", item.spread_kind),
    )
    next_title = _validate_spread_title(
        update_data.get("title", item.title),
        spread_kind=next_spread_kind,
    )
    next_description = _normalize_spread_description(
        update_data.get("description", item.description),
    )

    deck = _get_deck_or_404(db, next_deck_id)
    _ensure_deck_ready(deck)

    next_card_numbers = _normalize_card_numbers(
        deck=deck,
        cards_count=next_cards_count,
        card_numbers=next_card_numbers_input,
    )
    next_reversed_card_numbers = _normalize_reversed_card_numbers(
        next_reversed_input,
        next_card_numbers,
    )

    next_active_from, next_active_to = _validate_spread_period(
        active_from=update_data.get("active_from", item.active_from),
        active_to=update_data.get("active_to", item.active_to),
    )

    if _spread_has_period_conflict(
        db,
        spread_kind=next_spread_kind,
        active_from=next_active_from,
        active_to=next_active_to,
        now=now,
        exclude_spread_id=item.id,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Период расклада пересекается с уже активным или запланированным основным раскладом",
        )

    item.deck_id = deck.id
    item.title = next_title
    item.description = next_description
    item.spread_kind = next_spread_kind
    item.cards_count = next_cards_count
    item.card_numbers = next_card_numbers
    item.reversed_card_numbers = next_reversed_card_numbers
    item.active_from = next_active_from
    item.active_to = next_active_to
    item.status = _resolve_spread_status(
        active_from=next_active_from,
        active_to=next_active_to,
        now=now,
    )

    db.add(item)
    db.flush()

    _write_spread_log(
        db,
        admin_vk_user_id=admin_vk_user_id,
        action="update",
        spread=item,
        details={
            "before": before,
            "after": _serialize_spread_for_log(item),
        },
    )

    db.commit()
    db.refresh(item)

    return item


def delete_spread(
    db: Session,
    spread_id: int,
    *,
    admin_vk_user_id: int | None = None,
) -> Spread:
    item = _get_spread_or_404(db, spread_id)
    before = _serialize_spread_for_log(item)

    item.deleted_at = _utc_now()
    item.status = SpreadStatus.COMPLETED

    db.add(item)
    db.flush()

    _write_spread_log(
        db,
        admin_vk_user_id=admin_vk_user_id,
        action="delete",
        spread=item,
        details={
            "before": before,
            "after": _serialize_spread_for_log(item),
        },
    )

    db.commit()
    db.refresh(item)

    return item


def reset_test_spreads(
    db: Session,
    *,
    admin_vk_user_id: int | None = None,
) -> dict[str, int]:
    deleted_user_opens_count = db.execute(delete(UserDailyOpen)).rowcount or 0
    deleted_spreads_count = db.execute(delete(Spread)).rowcount or 0

    db.commit()

    return {
        "deleted_spreads_count": int(deleted_spreads_count),
        "deleted_user_opens_count": int(deleted_user_opens_count),
    }