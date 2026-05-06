"""Tests for shared route helpers."""

import binascii
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, UploadFile

from volunteer_call_api.routes.helpers import (
    apply_partial_update,
    decode_base64_or_400,
    get_one_or_404,
    validate_image_upload,
)


@pytest.mark.asyncio
async def test_get_one_or_404_found():
    mock_obj = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_obj
    db = AsyncMock()
    db.execute.return_value = mock_result
    query = MagicMock()
    result = await get_one_or_404(db, query, detail="Project not found")
    assert result is mock_obj


@pytest.mark.asyncio
async def test_get_one_or_404_not_found():
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db = AsyncMock()
    db.execute.return_value = mock_result
    with pytest.raises(HTTPException) as exc:
        await get_one_or_404(db, MagicMock(), detail="Project not found")
    assert exc.value.status_code == 404
    assert exc.value.detail == "Project not found"


@pytest.mark.asyncio
async def test_get_one_or_404_default_detail():
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    db = AsyncMock()
    db.execute.return_value = mock_result
    with pytest.raises(HTTPException) as exc:
        await get_one_or_404(db, MagicMock())
    assert exc.value.detail == "Not found"


@pytest.mark.asyncio
async def test_validate_image_upload_valid():
    file = AsyncMock(spec=UploadFile)
    file.content_type = "image/jpeg"
    file.read.return_value = b"\xff\xd8" + b"\x00" * 100
    content = await validate_image_upload(file)
    assert len(content) == 102


@pytest.mark.asyncio
async def test_validate_image_upload_bad_type():
    file = AsyncMock(spec=UploadFile)
    file.content_type = "text/plain"
    with pytest.raises(HTTPException) as exc:
        await validate_image_upload(file)
    assert exc.value.status_code == 400
    assert "Invalid file type" in exc.value.detail


@pytest.mark.asyncio
async def test_validate_image_upload_too_large():
    file = AsyncMock(spec=UploadFile)
    file.content_type = "image/png"
    file.read.return_value = b"\x00" * (11 * 1024 * 1024)
    with pytest.raises(HTTPException) as exc:
        await validate_image_upload(file)
    assert exc.value.status_code == 400
    assert "too large" in exc.value.detail


def test_apply_partial_update_applies_non_none():
    class FakeBody:
        name = "new_name"
        age = 25

    obj = MagicMock()
    obj.name = "old"
    obj.age = 30
    apply_partial_update(obj, FakeBody(), ["name", "age"])
    assert obj.name == "new_name"
    assert obj.age == 25


def test_apply_partial_update_skips_none():
    class FakeBody:
        name = "new_name"
        age = None

    obj = MagicMock()
    obj.name = "old"
    obj.age = 30
    apply_partial_update(obj, FakeBody(), ["name", "age"])
    assert obj.name == "new_name"
    assert obj.age == 30


def test_decode_base64_or_400_valid():
    result = decode_base64_or_400("aGVsbG8=", "signature")
    assert result == b"hello"


def test_decode_base64_or_400_invalid():
    with pytest.raises(HTTPException) as exc:
        decode_base64_or_400("not!valid!base64!!!", "signature")
    assert exc.value.status_code == 400
    assert "signature" in exc.value.detail
