import base64
from typing import Optional

class OCRAgent:
    """OCR Agent Stub for Phase 3.
    In production, this would use Pix2Tex or TrOCR via a separate service or local model.
    """
    async def process_image(self, image_data: str) -> str:
        # Mock behavior: If image is provided, return a predefined math text
        # In a real scenario, this would decode base64 and run inference
        return "Cho tam giác ABC đều cạnh 5"

    async def process_url(self, url: str) -> str:
        # Mock behavior
        return "Cho hình vuông ABCD có cạnh bằng 4"
