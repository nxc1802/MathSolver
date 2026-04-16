"""Shim: moved to ``vision_ocr.compat`` for OCR worker isolation."""

from vision_ocr.compat import allow_ultralytics_weights

__all__ = ["allow_ultralytics_weights"]
