from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.spread import (
    SpreadCreateSchema,
    SpreadDetailSchema,
    SpreadListResponseSchema,
    SpreadMutationResponseSchema,
    SpreadUpdateSchema,
)
from backend.app.services.spreads import (
    create_spread,
    delete_spread,
    get_spread,
    list_spreads,
    reset_test_spreads,
    update_spread,
)

router = APIRouter()


@router.get("", response_model=SpreadListResponseSchema)
async def list_spreads_route(
    db: Session = Depends(get_db),
) -> SpreadListResponseSchema:
    items = list_spreads(db)
    return SpreadListResponseSchema.model_validate({"items": items})


@router.post(
    "",
    response_model=SpreadMutationResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_spread_route(
    payload: SpreadCreateSchema,
    admin_vk_user_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> SpreadMutationResponseSchema:
    item = create_spread(
        db,
        payload,
        admin_vk_user_id=admin_vk_user_id,
    )

    return SpreadMutationResponseSchema.model_validate(
        {
            "ok": True,
            "message": "Расклад создан",
            "item": item,
        }
    )


@router.post("/reset")
async def reset_test_spreads_route(
    admin_vk_user_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    return reset_test_spreads(
        db,
        admin_vk_user_id=admin_vk_user_id,
    )


@router.post("/reset-test-data")
async def reset_test_spreads_legacy_route(
    admin_vk_user_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> dict[str, int]:
    return reset_test_spreads(
        db,
        admin_vk_user_id=admin_vk_user_id,
    )


@router.get("/{spread_id}", response_model=SpreadDetailSchema)
async def get_spread_route(
    spread_id: int,
    db: Session = Depends(get_db),
) -> SpreadDetailSchema:
    item = get_spread(db, spread_id)
    return SpreadDetailSchema.model_validate(item)


@router.put("/{spread_id}", response_model=SpreadMutationResponseSchema)
async def update_spread_route(
    spread_id: int,
    payload: SpreadUpdateSchema,
    admin_vk_user_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> SpreadMutationResponseSchema:
    item = update_spread(
        db,
        spread_id,
        payload,
        admin_vk_user_id=admin_vk_user_id,
    )

    return SpreadMutationResponseSchema.model_validate(
        {
            "ok": True,
            "message": "Расклад обновлён",
            "item": item,
        }
    )


@router.delete("/{spread_id}", response_model=SpreadMutationResponseSchema)
async def delete_spread_route(
    spread_id: int,
    admin_vk_user_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> SpreadMutationResponseSchema:
    item = delete_spread(
        db,
        spread_id,
        admin_vk_user_id=admin_vk_user_id,
    )

    return SpreadMutationResponseSchema.model_validate(
        {
            "ok": True,
            "message": "Расклад удалён",
            "item": item,
        }
    )