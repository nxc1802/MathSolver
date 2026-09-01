import pytest
from unittest.mock import MagicMock, patch
import uuid
from fastapi import HTTPException

from app.chat_image_upload import cleanup_session_storage, validate_chat_image_bytes
from app.session_cache import (
    _session_owner,
    invalidate_session_owner,
    session_owned_by_user,
)
from app.websocket_manager import active_connections, notify_status


def test_session_owner_cache():
    user_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    fetch_count = 0

    def mock_owns():
        nonlocal fetch_count
        fetch_count += 1
        return True

    assert session_owned_by_user(session_id, user_id, mock_owns) is True
    assert fetch_count == 1

    # Hit
    assert session_owned_by_user(session_id, user_id, mock_owns) is True
    assert fetch_count == 1

    # Invalidate
    invalidate_session_owner(session_id, user_id)
    assert session_owned_by_user(session_id, user_id, mock_owns) is True
    assert fetch_count == 2


def test_chat_image_validation_magic_bytes():
    # Valid PNG magic bytes
    png_bytes = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
    ext, mime = validate_chat_image_bytes("test.png", png_bytes, "image/png")
    assert ext == ".png"
    assert mime == "image/png"

    # Valid JPEG magic bytes
    jpeg_bytes = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01"
    ext, mime = validate_chat_image_bytes("test.jpg", jpeg_bytes, "image/jpeg")
    assert ext == ".jpg"
    assert mime == "image/jpeg"

    # Invalid corrupted content
    bad_bytes = b"NOT_AN_IMAGE_DATA_HEADER"
    with pytest.raises(HTTPException) as exc_info:
        validate_chat_image_bytes("test.png", bad_bytes, "image/png")
    assert exc_info.value.status_code == 400


def test_cleanup_session_storage():
    session_id = str(uuid.uuid4())
    mock_supabase = MagicMock()
    
    mock_from = MagicMock()
    mock_from.list.return_value = [
        {"name": f"image_v1_{session_id}.png"},
        {"name": ".emptyFolderPlaceholder"},
    ]
    mock_supabase.storage.from_.return_value = mock_from

    with patch("app.supabase_client.get_supabase", return_value=mock_supabase):
        cleanup_session_storage(session_id)
        assert mock_supabase.storage.from_.called
        assert mock_from.remove.called


@pytest.mark.asyncio
async def test_websocket_dead_connection_pruning():
    job_id = str(uuid.uuid4())

    from unittest.mock import AsyncMock

    good_ws = MagicMock()
    good_ws.send_json = AsyncMock()

    bad_ws = MagicMock()
    async def bad_send(_):
        raise RuntimeError("Connection closed")
    bad_ws.send_json = bad_send

    active_connections[job_id] = [good_ws, bad_ws]

    # Notify status should prune bad_ws
    await notify_status(job_id, {"status": "processing"})

    assert job_id in active_connections
    assert bad_ws not in active_connections[job_id]
    assert good_ws in active_connections[job_id]

    # Clean up
    active_connections.clear()
