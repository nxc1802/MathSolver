"""Helpers for OCR preview combined draft (no Pydantic email deps)."""

from __future__ import annotations

from typing import Optional


def build_combined_ocr_preview_draft(user_message: Optional[str], ocr_text: str) -> str:
    """Merge user caption and OCR text for confirm step (user message first, then OCR)."""
    u = (user_message or "").strip()
    o = (ocr_text or "").strip()
    if u and o:
        return f"{u}\n\n{o}"
    return u or o
