"""Unit tests that avoid importing the full FastAPI app (no Supabase)."""

from app.ocr_text_merge import build_combined_ocr_preview_draft


def test_build_combined_ocr_preview_draft():
    assert build_combined_ocr_preview_draft(None, "only ocr") == "only ocr"
    assert build_combined_ocr_preview_draft("", "only ocr") == "only ocr"
    assert build_combined_ocr_preview_draft("  caption  ", "") == "caption"
    assert build_combined_ocr_preview_draft("a", "b") == "a\n\nb"
