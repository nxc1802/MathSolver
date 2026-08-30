from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class OCRElement(BaseModel):
    """
    Represents an individual recognized layout region/element from the image
    (text paragraph, inline formula, standalone equation, table, diagram/figure).
    """
    id: int = Field(..., description="Unique index of the element")
    type: str = Field(
        default="text",
        description="Type of region: 'text', 'isolated_formula', 'embedding_formula', 'table', 'figure'",
    )
    text: str = Field(default="", description="Extracted text or markdown content")
    latex: Optional[str] = Field(
        default=None,
        description="Clean LaTeX formula code if element represents or contains mathematics",
    )
    bbox: List[int] = Field(
        default_factory=list,
        description="Bounding box [x_min, y_min, x_max, y_max] or polygon points",
    )
    reading_order: int = Field(
        default=0, description="Sequential index in the document reading order"
    )
    confidence: float = Field(
        default=1.0, description="Recognition confidence score in range [0.0, 1.0]"
    )


class CanonicalOCRResult(BaseModel):
    """
    Standardized, canonical OCR output schema (v5.3).
    Preserves raw text, LaTeX formulas, layout reading order, and spatial bounding boxes.
    """
    text: str = Field(
        default="",
        description="Full reconstructed Markdown text containing inline and display LaTeX math",
    )
    latex: List[str] = Field(
        default_factory=list,
        description="List of all isolated and embedded LaTeX formulas extracted from the document",
    )
    elements: List[OCRElement] = Field(
        default_factory=list,
        description="Structured list of layout regions and bounding boxes in reading order",
    )
    reading_order: List[int] = Field(
        default_factory=list,
        description="IDs of elements sorted according to reconstructed reading order",
    )
    confidence: float = Field(
        default=1.0,
        description="Overall aggregate confidence score across all recognized regions",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional spatial and image metadata (dimensions, orientation, engine version)",
    )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
