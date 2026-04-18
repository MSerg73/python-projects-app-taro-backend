from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.spread import (
    AppActiveSpreadsStateSchema,
    AppOpenSpreadCardByIdRequestSchema,
    AppOpenSpreadCardRequestSchema,
    AppOpenSpreadCardResponseSchema,
    AppSpreadStateSchema,
)
from backend.app.services.app_spread import (
    get_app_active_spreads_state,
    get_app_spread_state,
    open_app_spread_card,
    open_app_spread_card_by_id,
)

router = APIRouter()


@router.get("/spread", response_model=AppSpreadStateSchema)
async def get_active_spread(
    vk_user_id: int,
    db: Session = Depends(get_db),
) -> AppSpreadStateSchema:
    result = get_app_spread_state(db, vk_user_id)
    return AppSpreadStateSchema.model_validate(result)


@router.get("/spreads", response_model=AppActiveSpreadsStateSchema)
async def get_active_spreads(
    vk_user_id: int,
    db: Session = Depends(get_db),
) -> AppActiveSpreadsStateSchema:
    result = get_app_active_spreads_state(db, vk_user_id)
    return AppActiveSpreadsStateSchema.model_validate(result)


@router.post("/spread/open", response_model=AppOpenSpreadCardResponseSchema)
async def open_spread_card(
    payload: AppOpenSpreadCardRequestSchema,
    db: Session = Depends(get_db),
) -> AppOpenSpreadCardResponseSchema:
    result = open_app_spread_card(
        db,
        vk_user_id=payload.vk_user_id,
        card_number=payload.card_number,
    )
    return AppOpenSpreadCardResponseSchema.model_validate(result)


@router.post("/spreads/open", response_model=AppOpenSpreadCardResponseSchema)
async def open_spread_card_by_id_route(
    payload: AppOpenSpreadCardByIdRequestSchema,
    db: Session = Depends(get_db),
) -> AppOpenSpreadCardResponseSchema:
    result = open_app_spread_card_by_id(
        db,
        vk_user_id=payload.vk_user_id,
        spread_id=payload.spread_id,
        card_number=payload.card_number,
    )
    return AppOpenSpreadCardResponseSchema.model_validate(result)