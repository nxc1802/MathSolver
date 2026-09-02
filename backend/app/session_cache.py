"""Deterministic session ownership verification (Server-authoritative, no process-local drift)."""

from __future__ import annotations

from typing import Callable
from app.logutil import log_step


def invalidate_session_owner(session_id: str, user_id: str) -> None:
    """No-op for backward compatibility now that ownership is direct DB authoritative."""
    log_step("session_owner_check", target="session_owner", session_id=session_id, user_id=user_id)


def session_owned_by_user(
    session_id: str,
    user_id: str,
    fetch: Callable[[], bool],
) -> bool:
    """
    Direct authoritative ownership check via provided fetch function.
    Eliminates multi-worker drift by always evaluating against the authoritative DB.
    """
    ok = fetch()
    log_step("session_owner_verified", session_id=session_id, user_id=user_id, is_owner=ok)
    return ok

