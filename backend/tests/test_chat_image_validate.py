"""Unit tests for chat image validation (no Supabase / FastAPI app import)."""

import pytest
from fastapi import HTTPException

from app.chat_image_upload import validate_chat_image_bytes

_VALID_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def test_validate_png_ok():
    ext, mime = validate_chat_image_bytes("a.png", _VALID_PNG, "image/png")
    assert ext == ".png"
    assert mime == "image/png"


def test_validate_rejects_bad_magic():
    with pytest.raises(HTTPException) as exc:
        validate_chat_image_bytes("a.png", b"xxxxxxxxxxxx", "image/png")
    assert exc.value.status_code == 400


def test_validate_rejects_empty():
    with pytest.raises(HTTPException) as exc:
        validate_chat_image_bytes("a.png", b"", "image/png")
    assert exc.value.status_code == 400
