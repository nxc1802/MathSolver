import os
from PIL import Image
try:
    from pix2tex.cli import LatexOCR
except ImportError:
    LatexOCR = None

class OCRAgent:
    """Real OCR Agent using Pix2Tex for LaTeX recognition."""
    def __init__(self):
        if LatexOCR:
            self.model = LatexOCR()
        else:
            self.model = None

    async def process_image(self, image_path: str) -> str:
        if not self.model:
            return "OCR Engine (Pix2Tex) not installed. Please install it to use this feature."
        
        img = Image.open(image_path)
        return self.model(img)

    async def process_url(self, url: str) -> str:
        if not self.model:
            return "OCR Engine not installed."
        
        import httpx
        import io
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                img = Image.open(io.BytesIO(resp.content))
                return self.model(img)
            else:
                return f"Failed to download image from {url}"
