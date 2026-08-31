"""Canonical Standard Geometry Constructors (P1).

Provides hierarchical, intuitive construction strategies for standard 2D/3D shapes
and solids before falling back to generic numerical optimization.
"""
from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional, Set, Tuple
import numpy as np

from .models import Point, Constraint
from .validator import GeometryValidator

logger = logging.getLogger(__name__)


class StandardGeometryConstructor:
    """
    Hierarchical and canonical geometry constructor for standard 2D and 3D shapes.
    Constructs well-formed, intuitive default representations on canonical planes (z=0 for 3D bases)
    while strictly preserving mathematical lengths and explicit user coordinates.
    """

    def __init__(self):
        self.validator = GeometryValidator(tolerance=0.02)

    def try_construct(
        self,
        points: List[Point],
        constraints: List[Constraint],
        solids_meta: List[Dict[str, Any]],
        is_3d: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """
        Attempts hierarchical canonical construction.
        Returns engine result dict if successful and fully validated, else None.
        """
        # If user gave explicit coordinates for multiple points, let the general solver handle it
        explicit_pts = {p.id: p for p in points if p.x is not None or p.y is not None or p.z is not None}
        if len(explicit_pts) >= 2:
            return None

        point_ids = [p.id for p in points]
        lengths: Dict[Tuple[str, str], float] = {}
        for c in constraints:
            if c.type == "length" and len(c.targets) == 2:
                p1, p2 = c.targets[0], c.targets[1]
                val = float(c.value)
                lengths[(p1, p2)] = val
                lengths[(p2, p1)] = val

        def get_len(p1: str, p2: str, default: float = 5.0) -> float:
            return lengths.get((p1, p2), default)

        # =========================================================================
        # 1. 3D SOLIDS CANONICAL CONSTRUCTORS
        # =========================================================================
        if is_3d:
            # ---------------------------------------------------------------------
            # A. PYRAMID (S_ABCD or S_ABC)
            # ---------------------------------------------------------------------
            pyramid_solid = next((s for s in solids_meta if s.get("type") == "pyramid"), None)
            if pyramid_solid:
                apex = pyramid_solid.get("apex")
                base = pyramid_solid.get("base", [])

                if apex and len(base) in (3, 4):
                    coords: Dict[str, List[float]] = {}

                    # 1. Construct Base on z=0
                    if len(base) == 4:
                        # Quadrilateral base: Square / Rectangle
                        pA, pB, pC, pD = base[0], base[1], base[2], base[3]
                        side_ab = get_len(pA, pB, 6.0)
                        side_bc = get_len(pB, pC, side_ab)
                        coords[pA] = [0.0, 0.0, 0.0]
                        coords[pB] = [side_ab, 0.0, 0.0]
                        coords[pC] = [side_ab, side_bc, 0.0]
                        coords[pD] = [0.0, side_bc, 0.0]
                    else:
                        # Triangular base
                        pA, pB, pC = base[0], base[1], base[2]
                        side_ab = get_len(pA, pB, 6.0)
                        side_bc = get_len(pB, pC, side_ab)
                        side_ca = get_len(pC, pA, side_ab)
                        # Equilateral or general triangle in z=0
                        coords[pA] = [0.0, 0.0, 0.0]
                        coords[pB] = [side_ab, 0.0, 0.0]
                        # Solve C_x, C_y in z=0
                        cos_A = (side_ab**2 + side_ca**2 - side_bc**2) / (2 * side_ab * side_ca + 1e-9)
                        cos_A = max(-1.0, min(1.0, cos_A))
                        sin_A = math.sqrt(max(0.0, 1.0 - cos_A**2))
                        coords[pC] = [side_ca * cos_A, side_ca * sin_A, 0.0]

                    # 2. Determine Foot of Altitude O
                    # Check if explicit center / foot constraint exists
                    foot_id = None
                    for c in constraints:
                        if c.type in ("center", "centroid") and len(c.targets) >= 2:
                            if c.targets[0] in point_ids and set(c.targets[1:]).issubset(set(base)):
                                foot_id = c.targets[0]
                                break
                        elif c.type in ("perp_plane", "height", "altitude") and len(c.targets) >= 2:
                            if c.targets[0] == apex and c.targets[1] in point_ids:
                                foot_id = c.targets[1]
                                break

                    base_vecs = [np.array(coords[bp]) for bp in base]
                    mean_center = np.mean(base_vecs, axis=0)

                    if foot_id and foot_id not in coords:
                        coords[foot_id] = [float(mean_center[0]), float(mean_center[1]), 0.0]

                    # 3. Determine Height / Apex S
                    height = None
                    if foot_id:
                        height = lengths.get((apex, foot_id))

                    if height is None:
                        # Check lateral edge length
                        lateral_len = get_len(apex, base[0], None)
                        if lateral_len is not None:
                            r_foot = float(np.linalg.norm(coords[base[0]] - mean_center))
                            if lateral_len > r_foot:
                                height = math.sqrt(lateral_len**2 - r_foot**2)

                    if height is None:
                        height = 8.0

                    apex_x = coords[foot_id][0] if foot_id and foot_id in coords else mean_center[0]
                    apex_y = coords[foot_id][1] if foot_id and foot_id in coords else mean_center[1]
                    coords[apex] = [float(apex_x), float(apex_y), float(height)]

                    # 4. Resolve any additional auxiliary points (midpoints, sections, point_on)
                    self._resolve_auxiliary_points(coords, constraints, point_ids)

                    # Validate construction
                    engine_res = {"coordinates": coords, "solids": solids_meta, "drawing_phases": []}
                    val = self.validator.validate(engine_res, constraints, is_3d=True)
                    if val.is_valid:
                        logger.info("[StandardGeometryConstructor] Canonical Pyramid construction SUCCESS.")
                        return engine_res

            # ---------------------------------------------------------------------
            # B. PRISM / CUBE / CUBOID
            # ---------------------------------------------------------------------
            prism_solid = next((s for s in solids_meta if s.get("type") in ("prism", "cube", "cuboid")), None)
            if prism_solid:
                b1 = prism_solid.get("base1", [])
                b2 = prism_solid.get("base2", [])
                s_type = prism_solid.get("type")

                if len(b1) == len(b2) and len(b1) in (3, 4):
                    coords: Dict[str, List[float]] = {}
                    height = get_len(b1[0], b2[0], 6.0)

                    if len(b1) == 4:
                        side_a = get_len(b1[0], b1[1], 5.0)
                        side_b = side_a if s_type == "cube" else get_len(b1[1], b1[2], 4.0)
                        if s_type == "cube":
                            height = side_a

                        coords[b1[0]] = [0.0, 0.0, 0.0]
                        coords[b1[1]] = [side_a, 0.0, 0.0]
                        coords[b1[2]] = [side_a, side_b, 0.0]
                        coords[b1[3]] = [0.0, side_b, 0.0]
                    else:
                        side_a = get_len(b1[0], b1[1], 5.0)
                        coords[b1[0]] = [0.0, 0.0, 0.0]
                        coords[b1[1]] = [side_a, 0.0, 0.0]
                        coords[b1[2]] = [side_a / 2.0, side_a * math.sqrt(3) / 2.0, 0.0]

                    # Translate Base 2 along +Z
                    for p1, p2 in zip(b1, b2):
                        coords[p2] = [coords[p1][0], coords[p1][1], float(height)]

                    self._resolve_auxiliary_points(coords, constraints, point_ids)
                    engine_res = {"coordinates": coords, "solids": solids_meta, "drawing_phases": []}
                    val = self.validator.validate(engine_res, constraints, is_3d=True)
                    if val.is_valid:
                        logger.info(f"[StandardGeometryConstructor] Canonical {s_type} construction SUCCESS.")
                        return engine_res

        # =========================================================================
        # 2. 2D POLYGON CANONICAL CONSTRUCTORS
        # =========================================================================
        else:
            poly_constraint = next(
                (c for c in constraints if c.type in ("square", "rectangle", "equilateral_triangle", "right_triangle")),
                None,
            )
            if poly_constraint:
                c_type = poly_constraint.type
                targets = poly_constraint.targets
                coords: Dict[str, List[float]] = {}

                if c_type == "square" and len(targets) >= 4:
                    pA, pB, pC, pD = targets[:4]
                    side = get_len(pA, pB, 6.0)
                    coords[pA] = [0.0, 0.0, 0.0]
                    coords[pB] = [side, 0.0, 0.0]
                    coords[pC] = [side, side, 0.0]
                    coords[pD] = [0.0, side, 0.0]

                elif c_type == "rectangle" and len(targets) >= 4:
                    pA, pB, pC, pD = targets[:4]
                    side_a = get_len(pA, pB, 8.0)
                    side_b = get_len(pB, pC, 6.0)
                    coords[pA] = [0.0, 0.0, 0.0]
                    coords[pB] = [side_a, 0.0, 0.0]
                    coords[pC] = [side_a, side_b, 0.0]
                    coords[pD] = [0.0, side_b, 0.0]

                elif c_type == "equilateral_triangle" and len(targets) >= 3:
                    pA, pB, pC = targets[:3]
                    side = get_len(pA, pB, 6.0)
                    coords[pA] = [0.0, 0.0, 0.0]
                    coords[pB] = [side, 0.0, 0.0]
                    coords[pC] = [side / 2.0, side * math.sqrt(3) / 2.0, 0.0]

                elif c_type == "right_triangle" and len(targets) >= 3:
                    pA, pB, pC = targets[:3]
                    side_ab = get_len(pA, pB, 6.0)
                    side_bc = get_len(pB, pC, 8.0)
                    coords[pB] = [0.0, 0.0, 0.0]
                    coords[pA] = [side_ab, 0.0, 0.0]
                    coords[pC] = [0.0, side_bc, 0.0]

                if coords:
                    self._resolve_auxiliary_points(coords, constraints, point_ids)
                    engine_res = {"coordinates": coords, "solids": solids_meta, "drawing_phases": []}
                    val = self.validator.validate(engine_res, constraints, is_3d=False)
                    if val.is_valid:
                        logger.info(f"[StandardGeometryConstructor] Canonical 2D {c_type} construction SUCCESS.")
                        return engine_res

        return None

    def _resolve_auxiliary_points(
        self,
        coords: Dict[str, List[float]],
        constraints: List[Constraint],
        point_ids: List[str],
    ):
        """Resolves midpoint, section, center, and point_on auxiliary points iteratively."""
        for _ in range(3):
            for c in constraints:
                c_type = c.type
                targets = c.targets
                val = c.value

                if c_type == "midpoint" and len(targets) == 3:
                    pM, pA, pB = targets[0], targets[1], targets[2]
                    if pM not in coords and pA in coords and pB in coords:
                        vA = np.array(coords[pA])
                        vB = np.array(coords[pB])
                        coords[pM] = list((vA + vB) / 2.0)

                elif c_type == "section" and len(targets) == 3:
                    pE, pA, pC = targets[0], targets[1], targets[2]
                    if pE not in coords and pA in coords and pC in coords:
                        vA = np.array(coords[pA])
                        vC = np.array(coords[pC])
                        k = float(val)
                        coords[pE] = list(vA + k * (vC - vA))

                elif c_type in ("center", "centroid") and len(targets) >= 3:
                    pO = targets[0]
                    poly_pts = targets[1:]
                    if pO not in coords and all(p in coords for p in poly_pts):
                        poly_vecs = [np.array(coords[p]) for p in poly_pts]
                        coords[pO] = list(np.mean(poly_vecs, axis=0))

                elif c_type == "point_on" and len(targets) == 3:
                    pP, pA, pB = targets[0], targets[1], targets[2]
                    if pP not in coords and pA in coords and pB in coords:
                        # If length AP is given
                        len_ap = next(
                            (
                                float(cc.value)
                                for cc in constraints
                                if cc.type == "length"
                                and set(cc.targets[:2]) == {pP, pA}
                            ),
                            None,
                        )
                        vA = np.array(coords[pA])
                        vB = np.array(coords[pB])
                        total_len = float(np.linalg.norm(vB - vA))
                        if len_ap is not None and total_len > 1e-4:
                            t = len_ap / total_len
                            coords[pP] = list(vA + t * (vB - vA))
