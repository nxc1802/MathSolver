"""Tests for POST /api/v1/sessions/{session_id}/ocr_preview (auth + owner + merge)."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("ALLOW_TEST_BYPASS", "true")

from app.main import app  # noqa: E402

_VALID_SESSION_ID = "00000000-0000-0000-0000-000000000099"


@pytest.fixture
def auth_headers():
    return {"Authorization": "Test test-user-ocr-preview"}


@pytest.mark.asyncio
async def test_ocr_preview_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            f"/api/v1/sessions/{_VALID_SESSION_ID}/ocr_preview",
            files={"file": ("t.png", b"\x89PNG\r\n\x1a\n", "image/png")},
            data={"user_message": "hello"},
        )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_ocr_preview_forbidden_when_not_owner(auth_headers):
    with patch("app.routers.solve.session_owned_by_user", return_value=False):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.post(
                f"/api/v1/sessions/{_VALID_SESSION_ID}/ocr_preview",
                headers=auth_headers,
                files={"file": ("t.png", b"\x89PNG\r\n\x1a\n", "image/png")},
                data={"user_message": "note"},
            )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_ocr_preview_success_merges_draft(auth_headers):
    mock_orch = MagicMock()
    mock_orch.ocr_agent.process_image = AsyncMock(return_value="OCR_LINE")

    with (
        patch("app.routers.solve.session_owned_by_user", return_value=True),
        patch("app.routers.solve.get_orchestrator", return_value=mock_orch),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.post(
                f"/api/v1/sessions/{_VALID_SESSION_ID}/ocr_preview",
                headers=auth_headers,
                files={"file": ("t.png", b"\x89PNG\r\n\x1a\n", "image/png")},
                data={"user_message": "  my note  "},
            )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["ocr_text"] == "OCR_LINE"
    assert data["user_message"] == "my note"
    assert data["combined_draft"] == "my note\n\nOCR_LINE"
    mock_orch.ocr_agent.process_image.assert_called_once()


@pytest.mark.asyncio
async def test_ocr_preview_rejects_oversized_file(auth_headers):
    mock_orch = MagicMock()
    mock_orch.ocr_agent.process_image = AsyncMock(return_value="")

    big = b"x" * (11 * 1024 * 1024)
    with (
        patch("app.routers.solve.session_owned_by_user", return_value=True),
        patch("app.routers.solve.get_orchestrator", return_value=mock_orch),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.post(
                f"/api/v1/sessions/{_VALID_SESSION_ID}/ocr_preview",
                headers=auth_headers,
                files={"file": ("huge.png", big, "image/png")},
            )
    assert res.status_code == 413
    mock_orch.ocr_agent.process_image.assert_not_called()


@pytest.mark.asyncio
async def test_ocr_preview_rejects_empty_file(auth_headers):
    with patch("app.routers.solve.session_owned_by_user", return_value=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.post(
                f"/api/v1/sessions/{_VALID_SESSION_ID}/ocr_preview",
                headers=auth_headers,
                files={"file": ("empty.png", b"", "image/png")},
            )
    assert res.status_code == 400
