"""Result Assembler: Assembles the canonical Geometry IR (Intermediate Representation) output."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ResultAssembler:
    """Assembles the unified, canonical Geometry IR representation."""

    def assemble(
        self,
        coordinates: Dict[str, List[float]],
        topology_data: Dict[str, Any],
        validation_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        result = {
            "coordinates": coordinates,
            "polygon_order": topology_data.get("polygon_order", []),
            "circles": topology_data.get("circles", []),
            "solids": topology_data.get("solids", []),
            "faces": topology_data.get("faces", []),
            "lines": topology_data.get("lines", []),
            "rays": topology_data.get("rays", []),
            "drawing_phases": topology_data.get("drawing_phases", []),
            "visualization_graph": topology_data.get("visualization_graph"),
            "geometry_objects": topology_data.get("geometry_objects", []),
            "auxiliary": topology_data.get("auxiliary", []),
            "is_3d": topology_data.get("is_3d", False),
        }
        if validation_info:
            result["validation"] = validation_info
        return result
