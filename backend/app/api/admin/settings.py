from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.app_setting import (
    AppSettingItemSchema,
    AppSettingListResponseSchema,
    AppSettingMutationResponseSchema,
    UpdateReversedCardsSettingSchema,
)
from backend.app.services.app_settings import (
    get_card_back_image_setting,
    get_logo_image_setting,
    get_logo_position_x_setting,
    get_logo_position_y_setting,
    get_reversed_cards_setting,
    get_spread_background_image_setting,
    get_workspace_background_color_setting,
    list_app_settings,
    update_card_back_image_setting,
    update_logo_image_setting,
    update_logo_position_x_setting,
    update_logo_position_y_setting,
    update_reversed_cards_setting,
    update_spread_background_image_setting,
    update_workspace_background_color_setting,
)

router = APIRouter()


class UpdateStringSettingSchema(BaseModel):
    value: str | None = None


class UpdateLogoPositionSettingSchema(BaseModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class LogoPositionResponseSchema(BaseModel):
    x: AppSettingItemSchema
    y: AppSettingItemSchema


class LogoPositionMutationResponseSchema(BaseModel):
    ok: bool
    x: AppSettingItemSchema
    y: AppSettingItemSchema


@router.get("", response_model=AppSettingListResponseSchema)
async def list_app_settings_route(
    db: Session = Depends(get_db),
) -> AppSettingListResponseSchema:
    items = list_app_settings(db)
    return AppSettingListResponseSchema(
        items=[AppSettingItemSchema.model_validate(item) for item in items]
    )


@router.get("/reversed-cards", response_model=AppSettingItemSchema)
async def get_reversed_cards_setting_route(
    db: Session = Depends(get_db),
) -> AppSettingItemSchema:
    item = get_reversed_cards_setting(db)
    return AppSettingItemSchema.model_validate(item)


@router.put(
    "/reversed-cards",
    response_model=AppSettingMutationResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def update_reversed_cards_setting_route(
    payload: UpdateReversedCardsSettingSchema,
    db: Session = Depends(get_db),
) -> AppSettingMutationResponseSchema:
    item = update_reversed_cards_setting(db, payload.value)
    return AppSettingMutationResponseSchema(
        ok=True,
        item=AppSettingItemSchema.model_validate(item),
    )


@router.get("/workspace-background-color", response_model=AppSettingItemSchema)
async def get_workspace_background_color_setting_route(
    db: Session = Depends(get_db),
) -> AppSettingItemSchema:
    item = get_workspace_background_color_setting(db)
    return AppSettingItemSchema.model_validate(item)


@router.put(
    "/workspace-background-color",
    response_model=AppSettingMutationResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def update_workspace_background_color_setting_route(
    payload: UpdateStringSettingSchema,
    db: Session = Depends(get_db),
) -> AppSettingMutationResponseSchema:
    item = update_workspace_background_color_setting(db, payload.value)
    return AppSettingMutationResponseSchema(
        ok=True,
        item=AppSettingItemSchema.model_validate(item),
    )


@router.get("/spread-background-image", response_model=AppSettingItemSchema)
async def get_spread_background_image_setting_route(
    db: Session = Depends(get_db),
) -> AppSettingItemSchema:
    item = get_spread_background_image_setting(db)
    return AppSettingItemSchema.model_validate(item)


@router.put(
    "/spread-background-image",
    response_model=AppSettingMutationResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def update_spread_background_image_setting_route(
    payload: UpdateStringSettingSchema,
    db: Session = Depends(get_db),
) -> AppSettingMutationResponseSchema:
    item = update_spread_background_image_setting(db, payload.value)
    return AppSettingMutationResponseSchema(
        ok=True,
        item=AppSettingItemSchema.model_validate(item),
    )


@router.get("/card-back-image", response_model=AppSettingItemSchema)
async def get_card_back_image_setting_route(
    db: Session = Depends(get_db),
) -> AppSettingItemSchema:
    item = get_card_back_image_setting(db)
    return AppSettingItemSchema.model_validate(item)


@router.put(
    "/card-back-image",
    response_model=AppSettingMutationResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def update_card_back_image_setting_route(
    payload: UpdateStringSettingSchema,
    db: Session = Depends(get_db),
) -> AppSettingMutationResponseSchema:
    item = update_card_back_image_setting(db, payload.value)
    return AppSettingMutationResponseSchema(
        ok=True,
        item=AppSettingItemSchema.model_validate(item),
    )


@router.get("/logo-image", response_model=AppSettingItemSchema)
async def get_logo_image_setting_route(
    db: Session = Depends(get_db),
) -> AppSettingItemSchema:
    item = get_logo_image_setting(db)
    return AppSettingItemSchema.model_validate(item)


@router.put(
    "/logo-image",
    response_model=AppSettingMutationResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def update_logo_image_setting_route(
    payload: UpdateStringSettingSchema,
    db: Session = Depends(get_db),
) -> AppSettingMutationResponseSchema:
    item = update_logo_image_setting(db, payload.value)
    return AppSettingMutationResponseSchema(
        ok=True,
        item=AppSettingItemSchema.model_validate(item),
    )


@router.get("/logo-position", response_model=LogoPositionResponseSchema)
async def get_logo_position_setting_route(
    db: Session = Depends(get_db),
) -> LogoPositionResponseSchema:
    x_item = get_logo_position_x_setting(db)
    y_item = get_logo_position_y_setting(db)

    return LogoPositionResponseSchema(
        x=AppSettingItemSchema.model_validate(x_item),
        y=AppSettingItemSchema.model_validate(y_item),
    )


@router.put(
    "/logo-position",
    response_model=LogoPositionMutationResponseSchema,
    status_code=status.HTTP_200_OK,
)
async def update_logo_position_setting_route(
    payload: UpdateLogoPositionSettingSchema,
    db: Session = Depends(get_db),
) -> LogoPositionMutationResponseSchema:
    x_item = update_logo_position_x_setting(db, payload.x)
    y_item = update_logo_position_y_setting(db, payload.y)

    return LogoPositionMutationResponseSchema(
        ok=True,
        x=AppSettingItemSchema.model_validate(x_item),
        y=AppSettingItemSchema.model_validate(y_item),
    )