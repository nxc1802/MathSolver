import pytest
import numpy as np
from PIL import Image, ImageDraw

from vision_ocr.canonical_schema import CanonicalOCRResult, OCRElement
from vision_ocr.pix2text_engine import Pix2TextOCREngine
from vision_ocr.pipeline import OcrVisionPipeline


def create_sample_math_image() -> Image.Image:
    """Generates a test image with text and math symbols."""
    img = Image.new("RGB", (600, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((20, 30), "Cho hình chóp S.ABC có đáy là tam giác vuông.", fill=(0, 0, 0))
    draw.text((20, 80), "Diện tích đáy S_ABC = 1/2 * a * b = 24", fill=(0, 0, 0))
    draw.text((20, 130), "Chiều cao h = 10. Tính thể tích V = 1/3 * S * h", fill=(0, 0, 0))
    return img


def test_canonical_ocr_schema():
    """Validates the Canonical OCR schema structure and types."""
    elem1 = OCRElement(
        id=0,
        type="text",
        text="Cho hình chóp S.ABCD",
        bbox=[10, 20, 300, 50],
        reading_order=0,
        confidence=0.98,
    )
    elem2 = OCRElement(
        id=1,
        type="isolated_formula",
        text="$$V = \\frac{1}{3} S_{day} h$$",
        latex="V = \\frac{1}{3} S_{day} h",
        bbox=[10, 60, 250, 100],
        reading_order=1,
        confidence=0.99,
    )
    
    result = CanonicalOCRResult(
        text="Cho hình chóp S.ABCD\n$$V = \\frac{1}{3} S_{day} h$$",
        latex=["V = \\frac{1}{3} S_{day} h"],
        elements=[elem1, elem2],
        reading_order=[0, 1],
        confidence=0.985,
        metadata={"width": 600, "height": 400},
    )

    data = result.to_dict()
    assert data["text"] == "Cho hình chóp S.ABCD\n$$V = \\frac{1}{3} S_{day} h$$"
    assert len(data["latex"]) == 1
    assert data["latex"][0] == "V = \\frac{1}{3} S_{day} h"
    assert len(data["elements"]) == 2
    assert data["elements"][1]["type"] == "isolated_formula"
    assert data["confidence"] == 0.985
    assert data["reading_order"] == [0, 1]


def test_pix2text_engine_parsing():
    """Tests the parsing layer of Pix2Text raw output into CanonicalOCRResult."""
    engine = Pix2TextOCREngine()
    
    raw_p2t_mock = [
        {
            "type": "text",
            "text": "Cho hình chóp tam giác đều $S.ABC$ có cạnh đáy bằng $6$.",
            "position": [[10, 10], [400, 10], [400, 40], [10, 40]],
            "score": 0.95,
        },
        {
            "type": "isolated_formula",
            "text": "S_{ABC} = \\frac{a^2\\sqrt{3}}{4}",
            "position": [[10, 50], [300, 50], [300, 90], [10, 90]],
            "score": 0.99,
        },
    ]

    canonical = engine._parse_pix2text_output(raw_p2t_mock, {"width": 500, "height": 200})
    
    assert isinstance(canonical, CanonicalOCRResult)
    assert len(canonical.elements) == 2
    assert "S.ABC" in canonical.text
    assert "$$S_{ABC} = \\frac{a^2\\sqrt{3}}{4}$$" in canonical.text
    assert len(canonical.latex) >= 2  # inline $S.ABC$, $6$ and isolated formula
    assert canonical.elements[1].type == "isolated_formula"
    assert canonical.elements[1].bbox == [10, 50, 300, 90]
    assert canonical.confidence > 0.9


@pytest.mark.asyncio
async def test_ocr_vision_pipeline_integration(tmp_path):
    """Tests OcrVisionPipeline with a generated math image."""
    test_img = create_sample_math_image()
    img_path = str(tmp_path / "test_math.png")
    test_img.save(img_path)

    pipeline = OcrVisionPipeline()
    canonical = await pipeline.process_image_canonical(img_path)
    
    assert isinstance(canonical, CanonicalOCRResult)
    assert isinstance(canonical.text, str)
    assert canonical.metadata.get("width") == 600
    assert canonical.metadata.get("height") == 200
