from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.app_setting import AppSetting, AppSettingKey


BOOLEAN_SETTING_DESCRIPTIONS: dict[str, str] = {
    "REVERSED_CARDS_ENABLED": "Включает или отключает использование перевёрнутых карт в приложении",
}

STRING_SETTING_DESCRIPTIONS: dict[str, str] = {
    "WORKSPACE_BACKGROUND_COLOR": "Цвет фона рабочего пространства приложения",
    "SPREAD_BACKGROUND_IMAGE_URL": "URL фонового изображения пользовательского расклада",
    "CARD_BACK_IMAGE_URL": "URL изображения рубашки карты",
    "LOGO_IMAGE_URL": "URL изображения логотипа приложения",
}

NUMBER_SETTING_DESCRIPTIONS: dict[str, str] = {
    "LOGO_POSITION_X": "Нормализованная горизонтальная позиция логотипа в диапазоне от 0 до 1",
    "LOGO_POSITION_Y": "Нормализованная вертикальная позиция логотипа в диапазоне от 0 до 1",
}

DEFAULT_WORKSPACE_BACKGROUND_COLOR = "#F3F4F7"
DEFAULT_LOGO_POSITION_X = 0.08
DEFAULT_LOGO_POSITION_Y = 0.08


def _get_setting(db: Session, key: AppSettingKey) -> AppSetting | None:
    return db.scalar(select(AppSetting).where(AppSetting.key == key))


def _resolve_setting_key(attr_name: str) -> AppSettingKey | None:
    candidate = getattr(AppSettingKey, attr_name, None)
    return candidate if isinstance(candidate, AppSettingKey) else None


def _require_setting_key(attr_name: str) -> AppSettingKey:
    key = _resolve_setting_key(attr_name)
    if key is None:
        raise ValueError(f"Ключ настройки {attr_name} отсутствует в AppSettingKey")
    return key


def _normalize_string_value(value: Any, *, default: str | None = None) -> str | None:
    if value is None:
        return default

    normalized = str(value).strip()
    if not normalized:
        return default

    return normalized


def _normalize_boolean_value(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value

    return default


def _normalize_fraction_value(value: Any, *, default: float) -> float:
    try:
        normalized = float(value)
    except (TypeError, ValueError):
        return default

    if normalized < 0:
        return 0.0

    if normalized > 1:
        return 1.0

    return normalized


def _save_setting(db: Session, item: AppSetting) -> AppSetting:
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _serialize_boolean_setting(
    item: AppSetting | None,
    *,
    key: AppSettingKey,
    default: bool,
    description: str,
) -> AppSetting:
    if item is not None:
        item.value_json = _normalize_boolean_value(item.value_json, default=default)
        if not item.description:
            item.description = description
        return item

    return AppSetting(
        key=key,
        value_json=default,
        description=description,
    )


def _serialize_string_setting(
    item: AppSetting | None,
    *,
    key: AppSettingKey,
    default: str | None,
    description: str,
) -> AppSetting:
    normalized_value = _normalize_string_value(
        item.value_json if item is not None else default,
        default=default,
    )

    if item is not None:
        item.value_json = normalized_value
        if not item.description:
            item.description = description
        return item

    return AppSetting(
        key=key,
        value_json=normalized_value,
        description=description,
    )


def _serialize_fraction_setting(
    item: AppSetting | None,
    *,
    key: AppSettingKey,
    default: float,
    description: str,
) -> AppSetting:
    normalized_value = _normalize_fraction_value(
        item.value_json if item is not None else default,
        default=default,
    )

    if item is not None:
        item.value_json = normalized_value
        if not item.description:
            item.description = description
        return item

    return AppSetting(
        key=key,
        value_json=normalized_value,
        description=description,
    )


def _get_or_create_boolean_setting(
    db: Session,
    *,
    attr_name: str,
    default: bool,
    description: str,
) -> AppSetting:
    key = _require_setting_key(attr_name)
    item = _get_setting(db, key)

    normalized = _serialize_boolean_setting(
        item,
        key=key,
        default=default,
        description=description,
    )

    return _save_setting(db, normalized)


def _get_or_create_string_setting(
    db: Session,
    *,
    attr_name: str,
    default: str | None,
    description: str,
) -> AppSetting:
    key = _require_setting_key(attr_name)
    item = _get_setting(db, key)

    normalized = _serialize_string_setting(
        item,
        key=key,
        default=default,
        description=description,
    )

    return _save_setting(db, normalized)


def _get_or_create_fraction_setting(
    db: Session,
    *,
    attr_name: str,
    default: float,
    description: str,
) -> AppSetting:
    key = _require_setting_key(attr_name)
    item = _get_setting(db, key)

    normalized = _serialize_fraction_setting(
        item,
        key=key,
        default=default,
        description=description,
    )

    return _save_setting(db, normalized)


def _update_boolean_setting(
    db: Session,
    *,
    attr_name: str,
    value: bool,
    description: str,
) -> AppSetting:
    key = _require_setting_key(attr_name)
    item = _get_setting(db, key)

    if item is None:
        item = AppSetting(
            key=key,
            value_json=bool(value),
            description=description,
        )
        return _save_setting(db, item)

    item.value_json = bool(value)

    if not item.description:
        item.description = description

    return _save_setting(db, item)


def _update_string_setting(
    db: Session,
    *,
    attr_name: str,
    value: str | None,
    description: str,
    default: str | None = None,
) -> AppSetting:
    key = _require_setting_key(attr_name)
    item = _get_setting(db, key)
    normalized_value = _normalize_string_value(value, default=default)

    if item is None:
        item = AppSetting(
            key=key,
            value_json=normalized_value,
            description=description,
        )
        return _save_setting(db, item)

    item.value_json = normalized_value

    if not item.description:
        item.description = description

    return _save_setting(db, item)


def _update_fraction_setting(
    db: Session,
    *,
    attr_name: str,
    value: float,
    description: str,
    default: float,
) -> AppSetting:
    key = _require_setting_key(attr_name)
    item = _get_setting(db, key)
    normalized_value = _normalize_fraction_value(value, default=default)

    if item is None:
        item = AppSetting(
            key=key,
            value_json=normalized_value,
            description=description,
        )
        return _save_setting(db, item)

    item.value_json = normalized_value

    if not item.description:
        item.description = description

    return _save_setting(db, item)


def get_reversed_cards_setting(db: Session) -> AppSetting:
    return _get_or_create_boolean_setting(
        db,
        attr_name="REVERSED_CARDS_ENABLED",
        default=False,
        description=BOOLEAN_SETTING_DESCRIPTIONS["REVERSED_CARDS_ENABLED"],
    )


def get_workspace_background_color_setting(db: Session) -> AppSetting:
    return _get_or_create_string_setting(
        db,
        attr_name="WORKSPACE_BACKGROUND_COLOR",
        default=DEFAULT_WORKSPACE_BACKGROUND_COLOR,
        description=STRING_SETTING_DESCRIPTIONS["WORKSPACE_BACKGROUND_COLOR"],
    )


def get_spread_background_image_setting(db: Session) -> AppSetting:
    return _get_or_create_string_setting(
        db,
        attr_name="SPREAD_BACKGROUND_IMAGE_URL",
        default=None,
        description=STRING_SETTING_DESCRIPTIONS["SPREAD_BACKGROUND_IMAGE_URL"],
    )


def get_card_back_image_setting(db: Session) -> AppSetting:
    return _get_or_create_string_setting(
        db,
        attr_name="CARD_BACK_IMAGE_URL",
        default=None,
        description=STRING_SETTING_DESCRIPTIONS["CARD_BACK_IMAGE_URL"],
    )


def get_logo_image_setting(db: Session) -> AppSetting:
    return _get_or_create_string_setting(
        db,
        attr_name="LOGO_IMAGE_URL",
        default=None,
        description=STRING_SETTING_DESCRIPTIONS["LOGO_IMAGE_URL"],
    )


def get_logo_position_x_setting(db: Session) -> AppSetting:
    return _get_or_create_fraction_setting(
        db,
        attr_name="LOGO_POSITION_X",
        default=DEFAULT_LOGO_POSITION_X,
        description=NUMBER_SETTING_DESCRIPTIONS["LOGO_POSITION_X"],
    )


def get_logo_position_y_setting(db: Session) -> AppSetting:
    return _get_or_create_fraction_setting(
        db,
        attr_name="LOGO_POSITION_Y",
        default=DEFAULT_LOGO_POSITION_Y,
        description=NUMBER_SETTING_DESCRIPTIONS["LOGO_POSITION_Y"],
    )


def list_app_settings(db: Session) -> list[AppSetting]:
    items: list[AppSetting] = []

    items.append(get_reversed_cards_setting(db))

    if _resolve_setting_key("WORKSPACE_BACKGROUND_COLOR") is not None:
        items.append(get_workspace_background_color_setting(db))

    if _resolve_setting_key("SPREAD_BACKGROUND_IMAGE_URL") is not None:
        items.append(get_spread_background_image_setting(db))

    if _resolve_setting_key("CARD_BACK_IMAGE_URL") is not None:
        items.append(get_card_back_image_setting(db))

    if _resolve_setting_key("LOGO_IMAGE_URL") is not None:
        items.append(get_logo_image_setting(db))

    if _resolve_setting_key("LOGO_POSITION_X") is not None:
        items.append(get_logo_position_x_setting(db))

    if _resolve_setting_key("LOGO_POSITION_Y") is not None:
        items.append(get_logo_position_y_setting(db))

    return items


def update_reversed_cards_setting(db: Session, value: bool) -> AppSetting:
    return _update_boolean_setting(
        db,
        attr_name="REVERSED_CARDS_ENABLED",
        value=value,
        description=BOOLEAN_SETTING_DESCRIPTIONS["REVERSED_CARDS_ENABLED"],
    )


def update_workspace_background_color_setting(
    db: Session,
    value: str | None,
) -> AppSetting:
    return _update_string_setting(
        db,
        attr_name="WORKSPACE_BACKGROUND_COLOR",
        value=value,
        description=STRING_SETTING_DESCRIPTIONS["WORKSPACE_BACKGROUND_COLOR"],
        default=DEFAULT_WORKSPACE_BACKGROUND_COLOR,
    )


def update_spread_background_image_setting(
    db: Session,
    value: str | None,
) -> AppSetting:
    return _update_string_setting(
        db,
        attr_name="SPREAD_BACKGROUND_IMAGE_URL",
        value=value,
        description=STRING_SETTING_DESCRIPTIONS["SPREAD_BACKGROUND_IMAGE_URL"],
    )


def update_card_back_image_setting(
    db: Session,
    value: str | None,
) -> AppSetting:
    return _update_string_setting(
        db,
        attr_name="CARD_BACK_IMAGE_URL",
        value=value,
        description=STRING_SETTING_DESCRIPTIONS["CARD_BACK_IMAGE_URL"],
    )


def update_logo_image_setting(
    db: Session,
    value: str | None,
) -> AppSetting:
    return _update_string_setting(
        db,
        attr_name="LOGO_IMAGE_URL",
        value=value,
        description=STRING_SETTING_DESCRIPTIONS["LOGO_IMAGE_URL"],
    )


def update_logo_position_x_setting(
    db: Session,
    value: float,
) -> AppSetting:
    return _update_fraction_setting(
        db,
        attr_name="LOGO_POSITION_X",
        value=value,
        default=DEFAULT_LOGO_POSITION_X,
        description=NUMBER_SETTING_DESCRIPTIONS["LOGO_POSITION_X"],
    )


def update_logo_position_y_setting(
    db: Session,
    value: float,
) -> AppSetting:
    return _update_fraction_setting(
        db,
        attr_name="LOGO_POSITION_Y",
        value=value,
        default=DEFAULT_LOGO_POSITION_Y,
        description=NUMBER_SETTING_DESCRIPTIONS["LOGO_POSITION_Y"],
    )