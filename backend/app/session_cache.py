"""TTL in-memory cache để giảm truy vấn Supabase lặp lại (list session, quyền sở hữu session)."""

from __future__ import annotations

from typing import Any, Callable

from cachetools import TTLCache

from app.logutil import log_step

_session_list: TTLCache[str, list[Any]] = TTLCache(maxsize=512, ttl=45)
_session_owner: TTLCache[tuple[str, str], bool] = TTLCache(maxsize=4096, ttl=45)


def invalidate_for_user(user_id: str) -> None:
    """Xoá cache list session của user (sau create / delete / rename / solve đổi title)."""
    _session_list.pop(user_id, None)
    log_step("cache_invalidate", target="session_list", user_id=user_id)


def invalidate_session_owner(session_id: str, user_id: str) -> None:
    _session_owner.pop((session_id, user_id), None)
    log_step("cache_invalidate", target="session_owner", session_id=session_id, user_id=user_id)


def get_sessions_list_cached(user_id: str, fetch: Callable[[], list[Any]]) -> list[Any]:
    if user_id in _session_list:
        log_step("cache_hit", kind="session_list", user_id=user_id)
        return _session_list[user_id]
    log_step("cache_miss", kind="session_list", user_id=user_id)
    data = fetch()
    _session_list[user_id] = data
    return data


def session_owned_by_user(
    session_id: str,
    user_id: str,
    fetch: Callable[[], bool],
) -> bool:
    key = (session_id, user_id)
    if key in _session_owner:
        log_step("cache_hit", kind="session_owner", session_id=session_id)
        return _session_owner[key]
    log_step("cache_miss", kind="session_owner", session_id=session_id)
    ok = fetch()
    _session_owner[key] = ok
    return ok
