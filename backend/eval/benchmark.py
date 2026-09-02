"""
Benchmark Dataset Models and Loader for MathSolver Evaluation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class BenchmarkSample(BaseModel):
    """Evaluation sample definition representing a standardized geometry problem."""
    id: str = Field(..., description="Unique sample identifier")
    category: str = Field(default="geometry", description="Problem category: geometry, algebra, 3d, 2d")
    image_url: Optional[str] = Field(default=None, description="Image URL if testing OCR")
    problem_text: str = Field(..., description="Canonical Vietnamese/LaTeX problem statement")
    expected_type: Optional[str] = Field(default=None, description="Expected shape type (e.g. pyramid, cube)")
    expected_entities: Optional[List[str]] = Field(default=None, description="Expected primary entities")
    expected_dsl: Optional[str] = Field(default=None, description="Reference Geometry DSL")
    expected_answer: Optional[str] = Field(default=None, description="Ground-truth final answer / value")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional reference annotations")


class BenchmarkDataset:
    """Benchmark dataset container."""

    def __init__(self, samples: List[BenchmarkSample]):
        self.samples = samples

    def __len__(self) -> int:
        return len(self.samples)

    def __iter__(self):
        return iter(self.samples)

    @classmethod
    def from_file(cls, path: str | Path) -> "BenchmarkDataset":
        """Loads benchmark samples from a JSON file."""
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Benchmark file not found: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, list):
            samples = [BenchmarkSample(**item) for item in data]
        elif isinstance(data, dict) and "samples" in data:
            samples = [BenchmarkSample(**item) for item in data["samples"]]
        else:
            raise ValueError(f"Unrecognized benchmark dataset format in {file_path}")

        return cls(samples)

    @classmethod
    def load_all_standard(cls, base_dir: Optional[Path] = None) -> "BenchmarkDataset":
        """Loads all JSON files under eval/datasets/."""
        if base_dir is None:
            base_dir = Path(__file__).parent / "datasets"

        all_samples: List[BenchmarkSample] = []
        for json_file in base_dir.rglob("*.json"):
            try:
                ds = cls.from_file(json_file)
                all_samples.extend(ds.samples)
            except Exception:
                pass

        return cls(all_samples)
