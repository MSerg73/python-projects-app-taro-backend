from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.schemas.card import (
    CardCreateSchema,
    CardDetailSchema,
    CardListResponseSchema,
    CardMutationResponseSchema,
    CardUpdateSchema,
)
from backend.app.services.cards import (
    create_card,
    get_card,
    list_cards,
    restore_card,
    soft_delete_card,
    update_card,
)
from backend.app.services.decks import get_deck

router = APIRouter()


@router.get("", response_model=CardListResponseSchema)
async def list_cards_route(
    deck_id: int = Query(..., ge=1),
    db: Session = Depends(get_db),
) -> CardListResponseSchema:
    get_deck(db, deck_id, include_deleted=True)

    try:
        items = list_cards(db, deck_id)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND:
            items = []
        else:
            raise

    return CardListResponseSchema(
        items=[CardDetailSchema.model_validate(item) for item in items]
    )


@router.post(
    "",
    response_model=CardMutationResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_card_route(
    payload: CardCreateSchema,
    admin_vk_user_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> CardMutationResponseSchema:
    item = create_card(db, payload, admin_vk_user_id=admin_vk_user_id)
    return CardMutationResponseSchema(
        ok=True,
        item=CardDetailSchema.model_validate(item),
    )


@router.get("/{card_id}", response_model=CardDetailSchema)
async def get_card_route(
    card_id: int,
    include_deleted: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> CardDetailSchema:
    item = get_card(db, card_id, include_deleted=include_deleted)
    return CardDetailSchema.model_validate(item)


@router.put("/{card_id}", response_model=CardMutationResponseSchema)
async def update_card_route(
    card_id: int,
    payload: CardUpdateSchema,
    admin_vk_user_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> CardMutationResponseSchema:
    item = update_card(db, card_id, payload, admin_vk_user_id=admin_vk_user_id)
    return CardMutationResponseSchema(
        ok=True,
        item=CardDetailSchema.model_validate(item),
    )


@router.delete("/{card_id}", response_model=CardMutationResponseSchema)
async def delete_card_route(
    card_id: int,
    admin_vk_user_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> CardMutationResponseSchema:
    item = soft_delete_card(db, card_id, admin_vk_user_id=admin_vk_user_id)
    return CardMutationResponseSchema(
        ok=True,
        item=CardDetailSchema.model_validate(item),
    )


@router.post("/{card_id}/restore", response_model=CardMutationResponseSchema)
async def restore_card_route(
    card_id: int,
    admin_vk_user_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
) -> CardMutationResponseSchema:
    item = restore_card(db, card_id, admin_vk_user_id=admin_vk_user_id)
    return CardMutationResponseSchema(
        ok=True,
        item=CardDetailSchema.model_validate(item),
    )