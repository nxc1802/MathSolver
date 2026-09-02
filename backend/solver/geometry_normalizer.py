"""Geometry Normalizer: Normalizes coordinates, scales, frames, and removes degenerate geometries."""

from __future__ import annotations

import logging
import numpy as np
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class GeometryNormalizer:
    """Standardizes point naming, coordinate scaling, centering, and precision."""

    def normalize_coordinates(
        self,
        coords: Dict[str, List[float]],
        target_span: float = 8.0,
        is_3d: bool = False,
    ) -> Dict[str, List[float]]:
        if not coords:
            return {}

        cleaned: Dict[str, List[float]] = {}
        for pid, pt in coords.items():
            cleaned[pid] = [
                0.0 if abs(val) < 1e-6 else float(np.round(val, 6))
                for val in pt
            ]

        # Calculate bounding box
        all_pts = np.array(list(cleaned.values()))
        if len(all_pts) == 0:
            return cleaned

        mins = np.min(all_pts, axis=0)
        maxs = np.max(all_pts, axis=0)
        spans = maxs - mins
        max_span = float(np.max(spans))

        # If geometry is valid and non-degenerate, scale into comfortable viewing range
        if max_span > 1e-4:
            scale = target_span / max_span
            center = (mins + maxs) / 2.0

            normalized: Dict[str, List[float]] = {}
            for pid, pt in cleaned.items():
                pt_arr = np.array(pt)
                norm_pt = (pt_arr - center) * scale
                if not is_3d:
                    # In 2D, pin z to 0 and center in 2D plane
                    normalized[pid] = [
                        float(np.round(norm_pt[0], 4)),
                        float(np.round(norm_pt[1], 4)),
                        0.0,
                    ]
                else:
                    # In 3D, keep z >= 0 ground orientation when appropriate
                    normalized[pid] = [
                        float(np.round(norm_pt[0], 4)),
                        float(np.round(norm_pt[1], 4)),
                        float(np.round(norm_pt[2], 4)),
                    ]
            return normalized

        return cleaned
