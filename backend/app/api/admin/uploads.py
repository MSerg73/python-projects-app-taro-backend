from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

router = APIRouter()

BACKEND_ROOT = Path(__file__).resolve().parents[3]
UPLOADS_ROOT = BACKEND_ROOT / "uploads"
SPREAD_BACKGROUNDS_DIR = UPLOADS_ROOT / "spread-backgrounds"
CARD_IMAGES_DIR = UPLOADS_ROOT / "card-images"
CARD_BACKS_DIR = UPLOADS_ROOT / "card-backs"

MAX_FILE_SIZE_BYTES = 8 * 1024 * 1024

COMMON_ALLOWED_CONTENT_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}

COMMON_ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".svg"}

CARD_IMAGE_ALLOWED_CONTENT_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
}

CARD_IMAGE_ALLOWED_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}

CARD_IMAGE_WIDTH_PX = 700
CARD_IMAGE_HEIGHT_PX = 1210


class UploadImageResponseSchema(BaseModel):
    ok: bool
    file_url: str
    file_name: str
    content_type: str


def _resolve_extension(
    upload: UploadFile,
    *,
    allowed_content_types: dict[str, str],
    allowed_suffixes: set[str],
    invalid_type_message: str,
) -> str:
    content_type = (upload.content_type or "").strip().lower()
    filename_suffix = Path(upload.filename or "").suffix.strip().lower()

    if content_type in allowed_content_types:
        return allowed_content_types[content_type]

    if filename_suffix in allowed_suffixes:
        return ".jpg" if filename_suffix == ".jpeg" else filename_suffix

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=invalid_type_message,
    )


def _validate_payload_size(payload: bytes) -> None:
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл пустой",
        )

    if len(payload) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Файл слишком большой. Максимум 8 MB",
        )


def _validate_card_image_dimensions(payload: bytes) -> None:
    try:
        with Image.open(BytesIO(payload)) as image:
            width, height = image.size
    except (UnidentifiedImageError, OSError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Не удалось прочитать изображение карты",
        ) from exc

    if width != CARD_IMAGE_WIDTH_PX or height != CARD_IMAGE_HEIGHT_PX:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Изображение карты должно быть {CARD_IMAGE_WIDTH_PX}x{CARD_IMAGE_HEIGHT_PX} px",
        )


async def _save_uploaded_image(
    *,
    file: UploadFile,
    target_dir: Path,
    file_name_prefix: str,
    public_dir_name: str,
    allowed_content_types: dict[str, str],
    allowed_suffixes: set[str],
    invalid_type_message: str,
    payload_validator: callable | None = None,
) -> UploadImageResponseSchema:
    extension = _resolve_extension(
        file,
        allowed_content_types=allowed_content_types,
        allowed_suffixes=allowed_suffixes,
        invalid_type_message=invalid_type_message,
    )
    payload = await file.read()

    _validate_payload_size(payload)

    if payload_validator is not None:
        payload_validator(payload)

    target_dir.mkdir(parents=True, exist_ok=True)

    generated_name = f"{file_name_prefix}_{uuid4().hex}{extension}"
    target_path = target_dir / generated_name
    target_path.write_bytes(payload)

    return UploadImageResponseSchema(
        ok=True,
        file_url=f"/uploads/{public_dir_name}/{generated_name}",
        file_name=generated_name,
        content_type=(file.content_type or "").strip().lower(),
    )


@router.post(
    "/spread-background",
    response_model=UploadImageResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def upload_spread_background(
    file: UploadFile = File(...),
) -> UploadImageResponseSchema:
    return await _save_uploaded_image(
        file=file,
        target_dir=SPREAD_BACKGROUNDS_DIR,
        file_name_prefix="spread_bg",
        public_dir_name="spread-backgrounds",
        allowed_content_types=COMMON_ALLOWED_CONTENT_TYPES,
        allowed_suffixes=COMMON_ALLOWED_SUFFIXES,
        invalid_type_message="Поддерживаются только PNG, JPG, WEBP и SVG",
    )


@router.post(
    "/card-image",
    response_model=UploadImageResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def upload_card_image(
    file: UploadFile = File(...),
) -> UploadImageResponseSchema:
    return await _save_uploaded_image(
        file=file,
        target_dir=CARD_IMAGES_DIR,
        file_name_prefix="card_image",
        public_dir_name="card-images",
        allowed_content_types=CARD_IMAGE_ALLOWED_CONTENT_TYPES,
        allowed_suffixes=CARD_IMAGE_ALLOWED_SUFFIXES,
        invalid_type_message="Для изображений карт поддерживаются только PNG, JPG и WEBP",
        payload_validator=_validate_card_image_dimensions,
    )


@router.post(
    "/card-back",
    response_model=UploadImageResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def upload_card_back(
    file: UploadFile = File(...),
) -> UploadImageResponseSchema:
    return await _save_uploaded_image(
        file=file,
        target_dir=CARD_BACKS_DIR,
        file_name_prefix="card_back",
        public_dir_name="card-backs",
        allowed_content_types=COMMON_ALLOWED_CONTENT_TYPES,
        allowed_suffixes=COMMON_ALLOWED_SUFFIXES,
        invalid_type_message="Поддерживаются только PNG, JPG, WEBP и SVG",
    )