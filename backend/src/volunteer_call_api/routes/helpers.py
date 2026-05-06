"""Shared route helper functions."""

import binascii
from typing import TypeVar

from fastapi import HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy import Select
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar("T")

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}


async def get_one_or_404(db: AsyncSession, query: Select[tuple[T]], detail: str = "Not found") -> T:
    """Execute query expecting one result; raise 404 if not found."""
    result = await db.execute(query)
    obj = result.scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=404, detail=detail)
    return obj


async def validate_image_upload(file: UploadFile) -> bytes:
    """Validate and read an uploaded image file. Returns file bytes."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_IMAGE_TYPES)}",
        )
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )
    return content


def apply_partial_update(obj: object, body: BaseModel, fields: list[str]) -> None:
    """Apply non-None fields from a Pydantic model to a SQLAlchemy object."""
    for field in fields:
        value = getattr(body, field)
        if value is not None:
            setattr(obj, field, value)


def decode_base64_or_400(data: str, label: str = "data") -> bytes:
    """Decode base64 string, raising 400 on invalid input."""
    try:
        return binascii.a2b_base64(data)
    except (binascii.Error, ValueError):
        raise HTTPException(status_code=400, detail=f"Invalid base64 {label}")
