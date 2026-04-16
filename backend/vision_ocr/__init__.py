"""Vision-only OCR (YOLO layout load / PaddleOCR / Pix2Tex). No LLM — safe for dedicated OCR workers."""

from .compat import allow_ultralytics_weights
from .pipeline import OcrVisionPipeline

__all__ = ["OcrVisionPipeline", "allow_ultralytics_weights"]
