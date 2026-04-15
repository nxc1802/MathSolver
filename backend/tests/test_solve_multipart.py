"""Tests for POST /api/v1/sessions/{session_id}/solve_multipart."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("ALLOW_TEST_BYPASS", "true")

from app.main import app  # noqa: E402
from app.models.schemas import SolveResponse  # noqa: E402

# PNG signature + padding (>= 12 bytes) for magic check in validate_chat_image_bytes
_VALID_PNG_BODY = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


@pytest.fixture
def auth_headers():
    return {"Authorization": "Test test-user-solve-mp"}


@pytest.mark.asyncio
async def test_solve_multipart_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        res = await client.post(
            "/api/v1/sessions/sess-1/solve_multipart",
            files={"file": ("t.png", _VALID_PNG_BODY, "image/png")},
            data={"text": "hi"},
        )
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_solve_multipart_forbidden(auth_headers):
    with patch("app.routers.solve.session_owned_by_user", return_value=False):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.post(
                "/api/v1/sessions/sess-1/solve_multipart",
                headers=auth_headers,
                files={"file": ("t.png", _VALID_PNG_BODY, "image/png")},
                data={"text": "hi"},
            )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_solve_multipart_empty_text(auth_headers):
    with patch("app.routers.solve.session_owned_by_user", return_value=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.post(
                "/api/v1/sessions/sess-1/solve_multipart",
                headers=auth_headers,
                files={"file": ("t.png", _VALID_PNG_BODY, "image/png")},
                data={"text": "   "},
            )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_solve_multipart_bad_magic(auth_headers):
    with patch("app.routers.solve.session_owned_by_user", return_value=True):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.post(
                "/api/v1/sessions/sess-1/solve_multipart",
                headers=auth_headers,
                files={"file": ("t.png", b"not-a-real-png!!", "image/png")},
                data={"text": "problem text"},
            )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_solve_multipart_upload_then_enqueue(auth_headers):
    up = {
        "public_url": "https://example.test/bucket/sessions/s1/image_v1_j.png",
        "storage_path": "sessions/sess-1/image_v1_job.png",
        "version": 1,
        "session_asset_id": "00000000-0000-0000-0000-000000000099",
    }
    captured = {}

    def fake_enqueue(supabase, background_tasks, session_id, user_id, uid, request, message_metadata, job_id):
        captured["metadata"] = message_metadata
        captured["job_id"] = job_id
        captured["request"] = request
        return SolveResponse(job_id=job_id, status="processing")

    with (
        patch("app.routers.solve.session_owned_by_user", return_value=True),
        patch("app.routers.solve.upload_session_chat_image", return_value=up) as up_mock,
        patch("app.routers.solve._enqueue_solve_common", side_effect=fake_enqueue),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            res = await client.post(
                "/api/v1/sessions/sess-1/solve_multipart",
                headers=auth_headers,
                files={"file": ("t.png", _VALID_PNG_BODY, "image/png")},
                data={"text": "  my problem  "},
            )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["status"] == "processing"
    jid = data["job_id"]
    assert jid
    up_mock.assert_called_once()
    call_args = up_mock.call_args[0]
    assert call_args[0] == "sess-1"
    assert call_args[1] == jid
    assert len(call_args[2]) == len(_VALID_PNG_BODY)
    att = captured["metadata"].get("attachment", {})
    assert att.get("size_bytes") == len(_VALID_PNG_BODY)
    assert att.get("public_url") == up["public_url"]
    assert captured["request"].text == "my problem"
    assert captured["request"].image_url == up["public_url"]
