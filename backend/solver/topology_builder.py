"""Topology Builder: Builds drawing phases, adjacency, faces, solids, and visualization graph."""

from __future__ import annotations

import logging
import string
from typing import Any, Dict, List, Optional, Set
from .models import Point, Constraint
from .vis_planner import VisualizationPlanner

logger = logging.getLogger(__name__)


class TopologyBuilder:
    """Generates geometric topology, faces, drawing phases, and complete visualization graph."""

    def __init__(self):
        self.planner = VisualizationPlanner()

    def build_topology(
        self,
        coords: Dict[str, List[float]],
        polygon_order: List[str],
        circles_meta: List[Dict[str, Any]],
        solids_meta: List[Dict[str, Any]],
        segments_meta: List[List[str]],
        lines_meta: List[List[str]],
        rays_meta: List[List[str]],
        pt_list: List[Point],
        constraints_meta: Optional[List[Constraint]] = None,
    ) -> Dict[str, Any]:
        all_ids = [p.id for p in pt_list]
        constraints = constraints_meta or []

        # Canonical ordering if empty
        if not polygon_order:
            base_pts = sorted(
                all_ids,
                key=lambda p: (string.ascii_uppercase.index(p) if p in string.ascii_uppercase else 100, p),
            )
            polygon_order = base_pts

        base_ids = [pid for pid in polygon_order if pid in all_ids]
        derived_ids = [pid for pid in all_ids if pid not in polygon_order]

        drawn_segments: Set[frozenset] = set()

        def add_segment(p1: str, p2: str, target_list: List[List[str]]):
            if p1 == p2:
                return
            s = frozenset([p1, p2])
            if s not in drawn_segments:
                drawn_segments.add(s)
                target_list.append([p1, p2])

        # Phase 1: Main polygon / base shape boundary
        phase1_segments: List[List[str]] = []
        if len(base_ids) >= 2:
            for i in range(len(base_ids) - 1):
                add_segment(base_ids[i], base_ids[i + 1], phase1_segments)
            if len(base_ids) > 2:
                add_segment(base_ids[-1], base_ids[0], phase1_segments)

        # Phase 2: Auxiliary segments from DSL and 3D solids
        phase2_segments: List[List[str]] = []
        for seg in segments_meta:
            if len(seg) >= 2:
                add_segment(seg[0], seg[1], phase2_segments)

        drawing_phases = [
            {
                "phase": 1,
                "label": "Hình cơ bản",
                "points": base_ids,
                "segments": phase1_segments,
            }
        ]
        if derived_ids or phase2_segments:
            drawing_phases.append({
                "phase": 2,
                "label": "Điểm và đoạn phụ",
                "points": derived_ids,
                "segments": phase2_segments,
            })

        is_3d = any(len(c) >= 3 and abs(c[2]) > 1e-4 for c in coords.values())

        # Plan topological visualization graph
        vis_graph = self.planner.plan(
            coords=coords,
            constraints=constraints,
            solids_meta=solids_meta,
            circles_meta=circles_meta,
            polygon_order=polygon_order,
            segments_meta=segments_meta,
            lines_meta=lines_meta,
            rays_meta=rays_meta,
            pt_list=pt_list,
            is_3d=is_3d,
        )

        faces: List[List[str]] = [f.vertices for f in vis_graph.faces.values()]

        return {
            "polygon_order": polygon_order,
            "circles": circles_meta,
            "solids": solids_meta,
            "faces": faces,
            "lines": lines_meta,
            "rays": rays_meta,
            "drawing_phases": vis_graph.drawing_phases if vis_graph.drawing_phases else drawing_phases,
            "visualization_graph": vis_graph.model_dump(mode="json"),
            "geometry_objects": vis_graph.to_geometry_objects_list(),
            "auxiliary": [a.to_dict() for a in vis_graph.auxiliary],
            "is_3d": is_3d,
        }
