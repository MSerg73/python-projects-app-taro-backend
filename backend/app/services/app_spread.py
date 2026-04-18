from __future__ import annotations

from datetime import date, datetime, timezone, tzinfo
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.models.card import Card
from backend.app.models.spread import Spread, SpreadKind, SpreadStatus
from backend.app.models.user_daily_open import UserDailyOpen
from backend.app.services.app_settings import get_reversed_cards_setting


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


def _get_project_timezone_name() -> str:
    timezone_name = (settings.PROJECT_TIMEZONE or "").strip()
    return timezone_name or "UTC"


def _project_today(now: datetime) -> date:
    project_timezone = _get_project_timezone()
    return now.astimezone(project_timezone).date()


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None

    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _project_date_from_datetime(value: datetime | None) -> date | None:
    normalized_value = _normalize_datetime(value)
    if normalized_value is None:
        return None

    return normalized_value.astimezone(_get_project_timezone()).date()


def _resolve_spread_status(
    *,
    active_from: datetime | None,
    active_to: datetime | None,
    now: datetime,
) -> SpreadStatus:
    active_from_date = _project_date_from_datetime(active_from)
    active_to_date = _project_date_from_datetime(active_to)
    today = _project_today(now)

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


def _get_all_not_deleted_spreads(db: Session) -> list[Spread]:
    return list(
        db.scalars(
            select(Spread)
            .where(Spread.deleted_at.is_(None))
            .order_by(Spread.active_from.asc(), Spread.id.asc())
        ).all()
    )


def _get_active_spreads(db: Session, now: datetime) -> list[Spread]:
    spreads = _get_all_not_deleted_spreads(db)

    active_spreads: list[Spread] = []
    has_changes = False

    for spread in spreads:
        previous_status = spread.status
        _sync_spread_status(db, spread, now=now)

        if spread.status != previous_status:
            has_changes = True

        if spread.status == SpreadStatus.ACTIVE:
            active_spreads.append(spread)

    if has_changes:
        db.commit()
        for spread in active_spreads:
            db.refresh(spread)

    active_spreads.sort(
        key=lambda item: (
            0 if item.spread_kind == SpreadKind.MAIN_DAILY else 1,
            _normalize_datetime(item.active_from) or datetime.min.replace(tzinfo=timezone.utc),
            item.id,
        )
    )

    return active_spreads


def _get_active_main_daily_spread(db: Session, now: datetime) -> Spread | None:
    active_spreads = _get_active_spreads(db, now)

    for spread in active_spreads:
        if spread.spread_kind == SpreadKind.MAIN_DAILY:
            return spread

    return None


def _get_active_spread_by_id(
    db: Session,
    *,
    spread_id: int,
    now: datetime,
) -> Spread | None:
    active_spreads = _get_active_spreads(db, now)

    for spread in active_spreads:
        if spread.id == spread_id:
            return spread

    return None


def _get_card_by_number(db: Session, deck_id: int, number: int) -> Card | None:
    return db.scalar(
        select(Card).where(
            Card.deck_id == deck_id,
            Card.number == number,
            Card.deleted_at.is_(None),
        )
    )


def _get_open_for_spread_date(
    db: Session,
    *,
    vk_user_id: int,
    spread_id: int,
    open_date: date,
) -> UserDailyOpen | None:
    return db.scalar(
        select(UserDailyOpen).where(
            UserDailyOpen.vk_user_id == vk_user_id,
            UserDailyOpen.spread_id == spread_id,
            UserDailyOpen.open_date == open_date,
        )
    )


def _require_spread_card_number(spread: Spread, card_number: int) -> None:
    if card_number not in (spread.card_numbers or []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Эта карта не входит в активный расклад",
        )


def _reversed_cards_enabled(db: Session) -> bool:
    item = get_reversed_cards_setting(db)
    return bool(item.value_json)


def _is_reversed_card(
    spread: Spread | None,
    card: Card | None,
    *,
    reversed_cards_enabled: bool,
) -> bool:
    if not reversed_cards_enabled or spread is None or card is None:
        return False

    return card.number in (spread.reversed_card_numbers or [])


def _serialize_opened_card(
    card: Card | None,
    *,
    spread: Spread | None = None,
    reversed_cards_enabled: bool,
) -> dict | None:
    if card is None:
        return None

    is_reversed = _is_reversed_card(
        spread,
        card,
        reversed_cards_enabled=reversed_cards_enabled,
    )

    description = (
        card.reversed_description or card.description
        if is_reversed
        else card.description
    )

    return {
        "number": card.number,
        "name": card.name,
        "image_url": card.image_url,
        "description": description,
        "reversed_description": card.reversed_description if reversed_cards_enabled else None,
        "is_reversed": is_reversed,
    }


def _serialize_user_open(
    opened: UserDailyOpen | None,
    *,
    spread: Spread | None = None,
) -> dict | None:
    if opened is None:
        return None

    return {
        "id": opened.id,
        "vk_user_id": opened.vk_user_id,
        "spread_id": opened.spread_id,
        "opened_card_number": opened.opened_card_number,
        "opened_at": opened.opened_at.isoformat() if opened.opened_at else None,
        "open_date": opened.open_date.isoformat() if opened.open_date else None,
        "deck_id": spread.deck_id if spread is not None else None,
    }


def _serialize_app_active_spread_item(
    db: Session,
    *,
    spread: Spread,
    vk_user_id: int,
    today: date,
    reversed_cards_enabled: bool,
) -> dict:
    existing_open = _get_open_for_spread_date(
        db,
        vk_user_id=vk_user_id,
        spread_id=spread.id,
        open_date=today,
    )

    if existing_open is None:
        return {
            "spread": spread,
            "opened_card": None,
            "user_open": None,
            "message": None,
        }

    card = _get_card_by_number(
        db,
        deck_id=spread.deck_id,
        number=existing_open.opened_card_number,
    )

    return {
        "spread": spread,
        "opened_card": _serialize_opened_card(
            card,
            spread=spread,
            reversed_cards_enabled=reversed_cards_enabled,
        ),
        "user_open": _serialize_user_open(existing_open, spread=spread),
        "message": "Карта открыта",
    }


def _open_spread_card(
    db: Session,
    *,
    vk_user_id: int,
    spread: Spread,
    card_number: int,
    now: datetime,
) -> dict:
    today = _project_today(now)
    project_timezone = _get_project_timezone_name()
    reversed_cards_enabled = _reversed_cards_enabled(db)
    open_date = today.isoformat()

    existing_open = _get_open_for_spread_date(
        db,
        vk_user_id=vk_user_id,
        spread_id=spread.id,
        open_date=today,
    )

    if existing_open is not None:
        existing_card = _get_card_by_number(
            db,
            deck_id=spread.deck_id,
            number=existing_open.opened_card_number,
        )

        return {
            "ok": True,
            "opened_card": _serialize_opened_card(
                existing_card,
                spread=spread,
                reversed_cards_enabled=reversed_cards_enabled,
            ),
            "user_open": _serialize_user_open(existing_open, spread=spread),
            "message": "Карта открыта",
            "open_date": open_date,
            "project_timezone": project_timezone,
        }

    _require_spread_card_number(spread, card_number)

    card = _get_card_by_number(
        db,
        deck_id=spread.deck_id,
        number=card_number,
    )
    if card is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Карта не найдена",
        )

    opened = UserDailyOpen(
        vk_user_id=vk_user_id,
        spread_id=spread.id,
        opened_card_number=card.number,
        opened_at=now,
        open_date=today,
    )

    db.add(opened)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        concurrent_open = _get_open_for_spread_date(
            db,
            vk_user_id=vk_user_id,
            spread_id=spread.id,
            open_date=today,
        )
        if concurrent_open is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Не удалось сохранить открытие карты",
            )

        concurrent_card = _get_card_by_number(
            db,
            deck_id=spread.deck_id,
            number=concurrent_open.opened_card_number,
        )

        return {
            "ok": True,
            "opened_card": _serialize_opened_card(
                concurrent_card,
                spread=spread,
                reversed_cards_enabled=reversed_cards_enabled,
            ),
            "user_open": _serialize_user_open(concurrent_open, spread=spread),
            "message": "Карта открыта",
            "open_date": open_date,
            "project_timezone": project_timezone,
        }

    db.refresh(opened)

    return {
        "ok": True,
        "opened_card": _serialize_opened_card(
            card,
            spread=spread,
            reversed_cards_enabled=reversed_cards_enabled,
        ),
        "user_open": _serialize_user_open(opened, spread=spread),
        "message": "Карта открыта",
        "open_date": open_date,
        "project_timezone": project_timezone,
    }


def get_app_spread_state(db: Session, vk_user_id: int) -> dict:
    now = _utc_now()
    today = _project_today(now)
    project_timezone = _get_project_timezone_name()
    reversed_cards_enabled = _reversed_cards_enabled(db)

    spread = _get_active_main_daily_spread(db, now)
    if spread is None:
        return {
            "spread": None,
            "opened_card": None,
            "user_open": None,
            "message": "Расклад пока недоступен",
            "project_timezone": project_timezone,
        }

    item = _serialize_app_active_spread_item(
        db,
        spread=spread,
        vk_user_id=vk_user_id,
        today=today,
        reversed_cards_enabled=reversed_cards_enabled,
    )

    return {
        "spread": item["spread"],
        "opened_card": item["opened_card"],
        "user_open": item["user_open"],
        "message": item["message"],
        "project_timezone": project_timezone,
    }


def get_app_active_spreads_state(db: Session, vk_user_id: int) -> dict:
    now = _utc_now()
    today = _project_today(now)
    project_timezone = _get_project_timezone_name()
    reversed_cards_enabled = _reversed_cards_enabled(db)

    active_spreads = _get_active_spreads(db, now)

    items = [
        _serialize_app_active_spread_item(
            db,
            spread=spread,
            vk_user_id=vk_user_id,
            today=today,
            reversed_cards_enabled=reversed_cards_enabled,
        )
        for spread in active_spreads
    ]

    return {
        "items": items,
        "project_timezone": project_timezone,
    }


def open_app_spread_card(db: Session, *, vk_user_id: int, card_number: int) -> dict:
    now = _utc_now()

    spread = _get_active_main_daily_spread(db, now)
    if spread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Активный расклад не найден",
        )

    return _open_spread_card(
        db,
        vk_user_id=vk_user_id,
        spread=spread,
        card_number=card_number,
        now=now,
    )


def open_app_spread_card_by_id(
    db: Session,
    *,
    vk_user_id: int,
    spread_id: int,
    card_number: int,
) -> dict:
    now = _utc_now()

    spread = _get_active_spread_by_id(
        db,
        spread_id=spread_id,
        now=now,
    )
    if spread is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Активный расклад не найден",
        )

    return _open_spread_card(
        db,
        vk_user_id=vk_user_id,
        spread=spread,
        card_number=card_number,
        now=now,
    )