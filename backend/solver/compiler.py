"""Semantic Constraint Compiler for Geometry Engine.

Audits high-level geometric primitives and expands them into complete,
unambiguous low-level mathematical and topological constraints (P0).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple
from .models import Point, Constraint

logger = logging.getLogger(__name__)


class ConstraintCompiler:
    """
    Compiles and expands high-level semantic geometry DSL into complete,
    rigorous low-level geometric invariants and topological constraints.
    """

    def compile(
        self,
        points: Dict[str, Point],
        raw_constraints: List[Constraint],
        is_3d: bool = False,
    ) -> Tuple[List[Point], List[Constraint], bool]:
        """
        Takes raw parsed points and constraints and returns expanded points
        and complete low-level mathematical constraints.
        """
        expanded_constraints: List[Constraint] = []
        derived_segments: List[List[str]] = []
        solids_meta: List[Dict[str, Any]] = []

        def ensure_point(pid: str) -> Point:
            if pid not in points:
                points[pid] = Point(id=pid)
            return points[pid]

        def add_segment(p1: str, p2: str):
            if p1 != p2:
                ensure_point(p1)
                ensure_point(p2)
                pair = [p1, p2]
                if pair not in derived_segments and [p2, p1] not in derived_segments:
                    derived_segments.append(pair)
                    expanded_constraints.append(Constraint(type="segment", targets=pair, value=0))

        # 1. First pass: scan and expand high-level semantic constraints
        for c in raw_constraints:
            c_type = c.type
            targets = [t.strip() for t in c.targets if isinstance(t, str)]
            val = c.value

            # -------------------------------------------------------------
            # HEIGHT / ALTITUDE: HEIGHT(S, O, ABCD) or HEIGHT(S, O, ABC)
            # Semantics: O in plane(Base), SO perp to plane(Base)
            # -------------------------------------------------------------
            if c_type in ("height", "altitude") and len(targets) >= 3:
                is_3d = True
                s_apex = targets[0]
                o_foot = targets[1]
                base_pts = targets[2:]
                ensure_point(s_apex)
                ensure_point(o_foot)
                for bp in base_pts:
                    ensure_point(bp)

                add_segment(s_apex, o_foot)

                # 1. Foot O lies on the base plane
                expanded_constraints.append(
                    Constraint(type="point_on_plane", targets=[o_foot] + base_pts[:3], value=0)
                )
                # 2. SO is perpendicular to base plane
                expanded_constraints.append(
                    Constraint(type="perp_plane", targets=[s_apex, o_foot] + base_pts, value=0)
                )
                # 3. Explicit height length if provided as value > 0
                if isinstance(val, (int, float)) and float(val) > 0:
                    expanded_constraints.append(
                        Constraint(type="length", targets=[s_apex, o_foot], value=float(val))
                    )
                logger.debug(f"[ConstraintCompiler] Expanded HEIGHT: {s_apex}{o_foot} _|_ plane({base_pts})")

            # -------------------------------------------------------------
            # MIDPOINT: MIDPOINT(M, A, B)
            # Semantics: M on AB, MA = MB, 2M - A - B = 0
            # -------------------------------------------------------------
            elif c_type == "midpoint" and len(targets) == 3:
                pM, pA, pB = targets[0], targets[1], targets[2]
                for p in [pM, pA, pB]:
                    ensure_point(p)
                add_segment(pA, pM)
                add_segment(pM, pB)
                expanded_constraints.append(Constraint(type="point_on", targets=[pM, pA, pB], value=0))
                expanded_constraints.append(Constraint(type="length_equal", targets=[pM, pA, pM, pB], value=0))
                expanded_constraints.append(Constraint(type="midpoint", targets=[pM, pA, pB], value=0))
                logger.debug(f"[ConstraintCompiler] Expanded MIDPOINT: {pM} = mid({pA}, {pB})")

            # -------------------------------------------------------------
            # CENTER / CENTROID: CENTER(O, A, B, C, ...)
            # Semantics: O in plane(Poly), O = mean(vertices)
            # -------------------------------------------------------------
            elif c_type in ("center", "centroid") and len(targets) >= 3:
                pO = targets[0]
                poly_pts = targets[1:]
                ensure_point(pO)
                for p in poly_pts:
                    ensure_point(p)

                if is_3d or len(poly_pts) >= 3:
                    expanded_constraints.append(
                        Constraint(type="point_on_plane", targets=[pO] + poly_pts[:3], value=0)
                    )
                expanded_constraints.append(Constraint(type="center", targets=[pO] + poly_pts, value=0))
                logger.debug(f"[ConstraintCompiler] Expanded CENTER: {pO} center of {poly_pts}")

            # -------------------------------------------------------------
            # FOOT OF PERPENDICULAR: FOOT(H, P, A, B)
            # Semantics: H on line(AB), PH perp AB
            # -------------------------------------------------------------
            elif c_type in ("foot", "foot_perp") and len(targets) >= 4:
                pH, pP, pA, pB = targets[0], targets[1], targets[2], targets[3]
                for p in [pH, pP, pA, pB]:
                    ensure_point(p)
                add_segment(pP, pH)
                expanded_constraints.append(Constraint(type="point_on", targets=[pH, pA, pB], value=0))
                expanded_constraints.append(
                    Constraint(type="perpendicular", targets=[pP, pH, pA, pB], value=0)
                )
                logger.debug(f"[ConstraintCompiler] Expanded FOOT: {pH} foot of {pP} on {pA}{pB}")

            # -------------------------------------------------------------
            # FOOT ON PLANE: FOOT_PLANE(H, P, A, B, C)
            # Semantics: H in plane(ABC), PH perp plane(ABC)
            # -------------------------------------------------------------
            elif c_type in ("foot_plane", "perp_foot_plane") and len(targets) >= 4:
                is_3d = True
                pH, pP = targets[0], targets[1]
                plane_pts = targets[2:]
                ensure_point(pH)
                ensure_point(pP)
                for p in plane_pts:
                    ensure_point(p)
                add_segment(pP, pH)
                expanded_constraints.append(
                    Constraint(type="point_on_plane", targets=[pH] + plane_pts[:3], value=0)
                )
                expanded_constraints.append(
                    Constraint(type="perp_plane", targets=[pP, pH] + plane_pts, value=0)
                )
                logger.debug(f"[ConstraintCompiler] Expanded FOOT_PLANE: {pH} on plane({plane_pts})")

            # -------------------------------------------------------------
            # MEDIAN: MEDIAN(A, M, B, C)
            # Semantics: M is midpoint of BC, segment AM
            # -------------------------------------------------------------
            elif c_type == "median" and len(targets) >= 4:
                pA, pM, pB, pC = targets[0], targets[1], targets[2], targets[3]
                for p in [pA, pM, pB, pC]:
                    ensure_point(p)
                add_segment(pA, pM)
                expanded_constraints.append(Constraint(type="midpoint", targets=[pM, pB, pC], value=0))
                logger.debug(f"[ConstraintCompiler] Expanded MEDIAN: {pA}{pM} to {pB}{pC}")

            # -------------------------------------------------------------
            # SQUARE: SQUARE(ABCD)
            # Semantics: 4 equal sides, 4 right angles, 2 equal & orthogonal diagonals, coplanar
            # -------------------------------------------------------------
            elif c_type == "square" and len(targets) >= 4:
                pA, pB, pC, pD = targets[:4]
                for p in [pA, pB, pC, pD]:
                    ensure_point(p)
                add_segment(pA, pB)
                add_segment(pB, pC)
                add_segment(pC, pD)
                add_segment(pD, pA)
                expanded_constraints.append(
                    Constraint(type="perpendicular", targets=[pA, pB, pA, pD], value=0)
                )
                expanded_constraints.append(
                    Constraint(type="perpendicular", targets=[pB, pA, pB, pC], value=0)
                )
                expanded_constraints.append(
                    Constraint(type="parallel", targets=[pA, pB, pD, pC], value=0)
                )
                expanded_constraints.append(
                    Constraint(type="parallel", targets=[pA, pD, pB, pC], value=0)
                )
                expanded_constraints.append(
                    Constraint(type="length_equal", targets=[pA, pB, pB, pC], value=0)
                )
                expanded_constraints.append(
                    Constraint(type="length_equal", targets=[pB, pC, pC, pD], value=0)
                )
                expanded_constraints.append(
                    Constraint(type="length_equal", targets=[pC, pD, pD, pA], value=0)
                )
                # Diagonals
                expanded_constraints.append(
                    Constraint(type="length_equal", targets=[pA, pC, pB, pD], value=0)
                )
                expanded_constraints.append(
                    Constraint(type="perpendicular", targets=[pA, pC, pB, pD], value=0)
                )
                if is_3d:
                    expanded_constraints.append(
                        Constraint(type="coplanar", targets=[pA, pB, pC, pD], value=0)
                    )
                logger.debug(f"[ConstraintCompiler] Expanded SQUARE: {targets[:4]}")

            # -------------------------------------------------------------
            # RECTANGLE: RECTANGLE(ABCD)
            # Semantics: Opposite sides parallel & equal, right angles, diagonals equal, coplanar
            # -------------------------------------------------------------
            elif c_type == "rectangle" and len(targets) >= 4:
                pA, pB, pC, pD = targets[:4]
                for p in [pA, pB, pC, pD]:
                    ensure_point(p)
                add_segment(pA, pB)
                add_segment(pB, pC)
                add_segment(pC, pD)
                add_segment(pD, pA)
                expanded_constraints.append(
                    Constraint(type="perpendicular", targets=[pA, pB, pA, pD], value=0)
                )
                expanded_constraints.append(
                    Constraint(type="perpendicular", targets=[pB, pA, pB, pC], value=0)
                )
                expanded_constraints.append(
                    Constraint(type="parallel", targets=[pA, pB, pD, pC], value=0)
                )
                expanded_constraints.append(
                    Constraint(type="parallel", targets=[pA, pD, pB, pC], value=0)
                )
                expanded_constraints.append(
                    Constraint(type="length_equal", targets=[pA, pB, pD, pC], value=0)
                )
                expanded_constraints.append(
                    Constraint(type="length_equal", targets=[pA, pD, pB, pC], value=0)
                )
                expanded_constraints.append(
                    Constraint(type="length_equal", targets=[pA, pC, pB, pD], value=0)
                )
                if is_3d:
                    expanded_constraints.append(
                        Constraint(type="coplanar", targets=[pA, pB, pC, pD], value=0)
                    )
                logger.debug(f"[ConstraintCompiler] Expanded RECTANGLE: {targets[:4]}")

            # -------------------------------------------------------------
            # PARALLELOGRAM / RHOMBUS
            # -------------------------------------------------------------
            elif c_type in ("parallelogram", "rhombus") and len(targets) >= 4:
                pA, pB, pC, pD = targets[:4]
                for p in [pA, pB, pC, pD]:
                    ensure_point(p)
                add_segment(pA, pB)
                add_segment(pB, pC)
                add_segment(pC, pD)
                add_segment(pD, pA)
                expanded_constraints.append(
                    Constraint(type="parallel", targets=[pA, pB, pD, pC], value=0)
                )
                expanded_constraints.append(
                    Constraint(type="parallel", targets=[pA, pD, pB, pC], value=0)
                )
                expanded_constraints.append(
                    Constraint(type="length_equal", targets=[pA, pB, pD, pC], value=0)
                )
                expanded_constraints.append(
                    Constraint(type="length_equal", targets=[pA, pD, pB, pC], value=0)
                )
                if c_type == "rhombus":
                    expanded_constraints.append(
                        Constraint(type="length_equal", targets=[pA, pB, pB, pC], value=0)
                    )
                    expanded_constraints.append(
                        Constraint(type="perpendicular", targets=[pA, pC, pB, pD], value=0)
                    )
                if is_3d:
                    expanded_constraints.append(
                        Constraint(type="coplanar", targets=[pA, pB, pC, pD], value=0)
                    )

            # -------------------------------------------------------------
            # TRAPEZOID: TRAPEZOID(ABCD) (AB || CD)
            # -------------------------------------------------------------
            elif c_type in ("trapezoid", "isosceles_trapezoid", "right_trapezoid") and len(targets) >= 4:
                pA, pB, pC, pD = targets[:4]
                for p in [pA, pB, pC, pD]:
                    ensure_point(p)
                add_segment(pA, pB)
                add_segment(pB, pC)
                add_segment(pC, pD)
                add_segment(pD, pA)
                expanded_constraints.append(
                    Constraint(type="parallel", targets=[pA, pB, pD, pC], value=0)
                )
                if c_type == "isosceles_trapezoid":
                    expanded_constraints.append(
                        Constraint(type="length_equal", targets=[pA, pD, pB, pC], value=0)
                    )
                elif c_type == "right_trapezoid":
                    expanded_constraints.append(
                        Constraint(type="perpendicular", targets=[pA, pD, pA, pB], value=0)
                    )
                if is_3d:
                    expanded_constraints.append(
                        Constraint(type="coplanar", targets=[pA, pB, pC, pD], value=0)
                    )

            # -------------------------------------------------------------
            # Metadata constraints (pass-through without treating targets as point IDs)
            # -------------------------------------------------------------
            elif c_type in ("solids_metadata", "lines_metadata", "rays_metadata", "polygon_order", "explicit_points"):
                expanded_constraints.append(c)

            # -------------------------------------------------------------
            # Standard Constraints (pass-through with point validation)
            # -------------------------------------------------------------
            else:
                for t in targets:
                    ensure_point(t)
                expanded_constraints.append(c)

        # 2. Add derived segments to constraints
        for seg in derived_segments:
            if not any(
                c.type == "segment" and set(c.targets[:2]) == set(seg)
                for c in expanded_constraints
            ):
                expanded_constraints.append(Constraint(type="segment", targets=seg, value=0))

        # 3. Final sanity check: all points referenced in constraints must exist
        for c in expanded_constraints:
            if c.type in ("solids_metadata", "lines_metadata", "rays_metadata", "polygon_order", "explicit_points"):
                continue
            for pid in c.targets:
                if isinstance(pid, str) and pid not in points and not pid.replace(".", "", 1).isdigit() and not pid.startswith("{"):
                    points[pid] = Point(id=pid)

        logger.info(
            f"[ConstraintCompiler] Compiled {len(raw_constraints)} raw constraints into "
            f"{len(expanded_constraints)} low-level constraints for {len(points)} points (is_3d={is_3d})."
        )
        return list(points.values()), expanded_constraints, is_3d
