"""Map exceptions to short, user-visible messages (avoid leaking HTML bodies from 404 proxies)."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def _looks_like_html(text: str) -> bool:
    t = text.lstrip()[:500].lower()
    return t.startswith("<!doctype") or t.startswith("<html") or "<html" in t[:200]


def format_error_for_user(exc: BaseException) -> str:
    """
    Produce a safe message for chat/UI. Full detail stays in server logs via logger.exception.
    """
    # httpx: wrong URL often returns 404 HTML; don't show body
    try:
        import httpx

        if isinstance(exc, httpx.HTTPStatusError):
            req = exc.request
            code = exc.response.status_code
            url_hint = ""
            try:
                url_hint = str(req.url.host) if req and req.url else ""
            except Exception:
                pass
            logger.warning(
                "HTTPStatusError %s for %s (response not shown to user)",
                code,
                url_hint or "?",
            )
            return (
                f"Lỗi gọi dịch vụ ngoài (HTTP {code}). "
                "Kiểm tra URL API, khóa bí mật và biến môi trường (MegaLLM/Supabase/Redis)."
            )

        if isinstance(exc, httpx.RequestError):
            return "Không kết nối được tới dịch vụ ngoài (mạng hoặc URL sai)."
    except ImportError:
        pass

    raw = str(exc).strip()
    if not raw:
        return "Đã xảy ra lỗi không xác định."

    if _looks_like_html(raw):
        logger.warning("Suppressed HTML error body from user-facing message")
        return (
            "Dịch vụ trả về trang lỗi (thường là URL API sai hoặc endpoint không tồn tại — HTTP 404). "
            "Kiểm tra MEGALLM_BASE_URL và khóa API trên server."
        )

    if len(raw) > 800:
        return raw[:800] + "…"

    return raw
