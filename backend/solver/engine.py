"""Geometry Engine: Modular Geometry IR Pipeline Coordinator."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from .models import Point, Constraint
from .constraint_compiler import ConstraintCompiler, CompiledSystem
from .constructors import StandardGeometryConstructor
from .coordinate_solver import CoordinateSolver
from .geometry_normalizer import GeometryNormalizer
from .topology_builder import TopologyBuilder
from .result_assembler import ResultAssembler

logger = logging.getLogger(__name__)


class GeometryEngine:
    """
    Modular Geometry Solver Engine (P4 Architecture):
    - ConstraintCompiler: Compiles DSL & constraints into algebraic systems
    - StandardGeometryConstructor: Canonical analytical construction for standard primitives
    - CoordinateSolver: Numerical & symbolic solver for equations
    - GeometryNormalizer: Centering, orientation, bounding box and coordinate scaling
    - TopologyBuilder: Drawing phases, faces, solids, and complete visualization graph
    - ResultAssembler: Canonical Geometry IR assembly
    """

    def __init__(self):
        self.compiler = ConstraintCompiler()
        self.constructor = StandardGeometryConstructor()
        self.coord_solver = CoordinateSolver()
        self.normalizer = GeometryNormalizer()
        self.topology_builder = TopologyBuilder()
        self.assembler = ResultAssembler()

    def solve(
        self,
        points: List[Point] | Dict[str, Point],
        constraints: List[Constraint],
        is_3d: bool = False,
    ) -> Optional[Dict[str, Any]]:
        if not points:
            logger.error("[GeometryEngine] No points to solve.")
            return None

        pt_list = list(points.values()) if isinstance(points, dict) else list(points)
        logger.info(f"==[GeometryEngine] Starting solve with {len(pt_list)} points, {len(constraints)} constraints (is_3d={is_3d})==")

        # 1. Compile constraints and symbols
        system: CompiledSystem = self.compiler.compile(pt_list, constraints, is_3d=is_3d)

        # 2. Step 0: Try Canonical Hierarchical Constructor
        canonical_res = self.constructor.try_construct(
            pt_list,
            system.real_constraints,
            system.solids_meta,
            is_3d,
        )

        if canonical_res and "coordinates" in canonical_res:
            logger.info("[GeometryEngine] Successfully constructed canonical standard representation.")
            return self._build_result(
                canonical_res["coordinates"],
                system.polygon_order,
                system.circles_meta,
                system.solids_meta,
                system.segments_meta,
                system.lines_ext,
                system.rays_ext,
                pt_list,
                system.real_constraints,
            )

        # 3. Solve numerical / symbolic coordinate equations
        raw_coords = self.coord_solver.solve(system, is_3d=is_3d)
        if not raw_coords:
            logger.error("[GeometryEngine] CoordinateSolver failed to find a valid solution.")
            return None

        # 4. Normalize coordinates and assemble Geometry IR
        return self._build_result(
            raw_coords,
            system.polygon_order,
            system.circles_meta,
            system.solids_meta,
            system.segments_meta,
            system.lines_ext,
            system.rays_ext,
            pt_list,
            system.real_constraints,
        )

    def _build_result(
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
        """Backward-compatible result builder delegating to modular topology & assembler."""
        # 1. Clean float zero residuals and restore explicit coordinates
        cleaned_coords = coords.copy()
        for p in pt_list:
            if p.id in cleaned_coords:
                if p.x is not None:
                    cleaned_coords[p.id][0] = float(p.x)
                elif abs(cleaned_coords[p.id][0]) < 1e-10:
                    cleaned_coords[p.id][0] = 0.0

                if p.y is not None:
                    cleaned_coords[p.id][1] = float(p.y)
                elif abs(cleaned_coords[p.id][1]) < 1e-10:
                    cleaned_coords[p.id][1] = 0.0

                if len(cleaned_coords[p.id]) >= 3:
                    if p.z is not None:
                        cleaned_coords[p.id][2] = float(p.z)
                    elif abs(cleaned_coords[p.id][2]) < 1e-10:
                        cleaned_coords[p.id][2] = 0.0

        for pid in list(cleaned_coords.keys()):
            for idx in range(len(cleaned_coords[pid])):
                if abs(cleaned_coords[pid][idx]) < 1e-10:
                    cleaned_coords[pid][idx] = 0.0

        # 2. Build topology and visualization graph
        topology_data = self.topology_builder.build_topology(
            coords=cleaned_coords,
            polygon_order=polygon_order,
            circles_meta=circles_meta,
            solids_meta=solids_meta,
            segments_meta=segments_meta,
            lines_meta=lines_meta,
            rays_meta=rays_meta,
            pt_list=pt_list,
            constraints_meta=constraints_meta,
        )

        # 3. Assemble canonical IR
        return self.assembler.assemble(
            coordinates=cleaned_coords,
            topology_data=topology_data,
        )
