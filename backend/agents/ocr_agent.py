import os
import io
import logging
from PIL import Image

try:
    from pix2tex.cli import LatexOCR
except ImportError:
    LatexOCR = None

logger = logging.getLogger(__name__)

class OCRAgent:
    """Real OCR Agent using Pix2Tex for LaTeX recognition."""
    def __init__(self):
        if LatexOCR:
            logger.info("[OCRAgent] Loading Pix2Tex model...")
            self.model = LatexOCR()
            logger.info("[OCRAgent] Pix2Tex model loaded successfully.")
        else:
            self.model = None
            logger.warning("[OCRAgent] Pix2Tex not installed. OCR features will be unavailable.")

    async def process_image(self, image_path: str) -> str:
        logger.info(f"==[OCRAgent] Processing local image: {image_path}==")
        if not self.model:
            logger.error("[OCRAgent] OCR model not available.")
            return "OCR Engine (Pix2Tex) not installed. Please install it to use this feature."
        img = Image.open(image_path)
        result = self.model(img)
        logger.info(f"[OCRAgent] OCR result (len={len(result)}): {result[:200]}")
        return result

    async def process_url(self, url: str) -> str:
        logger.info(f"==[OCRAgent] Processing image from URL: {url}==")
        if not self.model:
            logger.error("[OCRAgent] OCR model not available.")
            return "OCR Engine not installed."

        import httpx
        async with httpx.AsyncClient() as client:
            logger.debug(f"[OCRAgent] Downloading image from {url}...")
            resp = await client.get(url)
            if resp.status_code == 200:
                img = Image.open(io.BytesIO(resp.content))
                result = self.model(img)
                logger.info(f"[OCRAgent] OCR result (len={len(result)}): {result[:200]}")
                return result
            else:
                logger.error(f"[OCRAgent] Failed to download image. HTTP {resp.status_code}: {url}")
                return f"Failed to download image from {url} (HTTP {resp.status_code})"
