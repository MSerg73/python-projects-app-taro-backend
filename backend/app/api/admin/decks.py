from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.deck import (
    DeckCreateSchema,
    DeckDetailSchema,
    DeckListResponseSchema,
    DeckMutationResponseSchema,
    DeckSoftDeleteSchema,
    DeckUpdateSchema,
)
from backend.app.services.decks import (
    create_deck,
    get_deck,
    list_decks,
    restore_deck,
    soft_delete_deck,
    update_deck,
)

router = APIRouter()


@router.get("", response_model=DeckListResponseSchema)
async def list_decks_route(
    include_deleted: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> DeckListResponseSchema:
    items = list_decks(db, include_deleted=include_deleted)
    return DeckListResponseSchema(items=[DeckDetailSchema.model_validate(item) for item in items])


@router.post(
    "",
    response_model=DeckMutationResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_deck_route(
    payload: DeckCreateSchema,
    admin_vk_user_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> DeckMutationResponseSchema:
    item = create_deck(db, payload, admin_vk_user_id=admin_vk_user_id)
    return DeckMutationResponseSchema(
        ok=True,
        item=DeckDetailSchema.model_validate(item),
    )


@router.get("/{deck_id}", response_model=DeckDetailSchema)
async def get_deck_route(
    deck_id: int,
    include_deleted: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> DeckDetailSchema:
    item = get_deck(db, deck_id, include_deleted=include_deleted)
    return DeckDetailSchema.model_validate(item)


@router.put("/{deck_id}", response_model=DeckMutationResponseSchema)
async def update_deck_route(
    deck_id: int,
    payload: DeckUpdateSchema,
    admin_vk_user_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> DeckMutationResponseSchema:
    item = update_deck(db, deck_id, payload, admin_vk_user_id=admin_vk_user_id)
    return DeckMutationResponseSchema(
        ok=True,
        item=DeckDetailSchema.model_validate(item),
    )


@router.delete("/{deck_id}", response_model=DeckMutationResponseSchema)
async def delete_deck_route(
    deck_id: int,
    payload: DeckSoftDeleteSchema,
    admin_vk_user_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> DeckMutationResponseSchema:
    item = soft_delete_deck(
        db,
        deck_id,
        retention_days=payload.retention_days,
        reminder_days_before=payload.reminder_days_before,
        confirm=payload.confirm,
        admin_vk_user_id=admin_vk_user_id,
    )
    return DeckMutationResponseSchema(
        ok=True,
        item=DeckDetailSchema.model_validate(item),
    )


@router.post("/{deck_id}/restore", response_model=DeckMutationResponseSchema)
async def restore_deck_route(
    deck_id: int,
    admin_vk_user_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> DeckMutationResponseSchema:
    item = restore_deck(db, deck_id, admin_vk_user_id=admin_vk_user_id)
    return DeckMutationResponseSchema(
        ok=True,
        item=DeckDetailSchema.model_validate(item),
    )