"""Constraint Compiler: Compiles geometric DSL objects & constraints into symbolic equation systems."""

from __future__ import annotations

import json
import logging
import numpy as np
import sympy as sp
from typing import Any, Dict, List, Tuple
from .models import Point, Constraint

logger = logging.getLogger(__name__)


class CompiledSystem:
    def __init__(
        self,
        pt_list: List[Point],
        point_vars: Dict[str, Tuple[sp.Symbol, sp.Symbol, sp.Symbol]],
        equations: List[sp.Expr],
        polygon_order: List[str],
        circles_meta: List[Dict[str, Any]],
        solids_meta: List[Dict[str, Any]],
        segments_meta: List[List[str]],
        lines_ext: List[List[str]],
        rays_ext: List[List[str]],
        real_constraints: List[Constraint],
    ):
        self.pt_list = pt_list
        self.point_vars = point_vars
        self.equations = equations
        self.polygon_order = polygon_order
        self.circles_meta = circles_meta
        self.solids_meta = solids_meta
        self.segments_meta = segments_meta
        self.lines_ext = lines_ext
        self.rays_ext = rays_ext
        self.real_constraints = real_constraints


class ConstraintCompiler:
    """Compiles geometric constraints and anchor rules into symbolic equations."""

    def compile(self, points: List[Point], constraints: List[Constraint], is_3d: bool = False) -> CompiledSystem:
        pt_list = list(points.values()) if isinstance(points, dict) else list(points)

        polygon_order: List[str] = []
        circles_meta: List[Dict[str, Any]] = []
        solids_meta: List[Dict[str, Any]] = []
        segments_meta: List[List[str]] = []
        lines_ext: List[List[str]] = []
        rays_ext: List[List[str]] = []
        real_constraints: List[Constraint] = []

        for c in constraints:
            if c.type == 'polygon_order':
                polygon_order = list(c.targets)
            elif c.type == 'explicit_points' and not polygon_order:
                polygon_order = list(c.targets)
            elif c.type == 'circle':
                circles_meta.append({"center": c.targets[0], "radius": float(c.value)})
                real_constraints.append(c)
            elif c.type == 'sphere':
                solids_meta.append({"type": "sphere", "center": c.targets[0], "radius": float(c.value)})
                real_constraints.append(c)
            elif c.type == 'cone':
                if len(c.targets) >= 2:
                    solids_meta.append({"type": "cone", "apex": c.targets[0], "center": c.targets[1], "radius": float(c.value)})
                real_constraints.append(c)
            elif c.type == 'cylinder':
                if len(c.targets) >= 2:
                    solids_meta.append({"type": "cylinder", "center1": c.targets[0], "center2": c.targets[1], "radius": float(c.value)})
                real_constraints.append(c)
            elif c.type == 'solids_metadata':
                for s_str in c.targets:
                    try:
                        s_data = json.loads(s_str)
                        if s_data not in solids_meta:
                            solids_meta.append(s_data)
                    except Exception:
                        pass
            elif c.type == 'segment':
                segments_meta.append(list(c.targets))
            elif c.type == 'lines_metadata':
                lines_ext = [t.split(',') for t in c.targets]
            elif c.type == 'rays_metadata':
                rays_ext = [t.split(',') for t in c.targets]
            else:
                real_constraints.append(c)

        # Setup symbols
        point_vars: Dict[str, Tuple[sp.Symbol, sp.Symbol, sp.Symbol]] = {}
        equations: List[sp.Expr] = []

        for p in pt_list:
            x = sp.Symbol(f"{p.id}_x")
            y = sp.Symbol(f"{p.id}_y")
            z = sp.Symbol(f"{p.id}_z")
            point_vars[p.id] = (x, y, z)

            if not is_3d:
                equations.append(z)

        # Anchor logic to fix translation + rotation DOF if no explicit coordinates
        has_explicit = any(p.x is not None or p.y is not None for p in pt_list)
        if not has_explicit and len(pt_list) > 0:
            if is_3d and solids_meta:
                base_ids = []
                for s in solids_meta:
                    if s.get("type") == "pyramid" and s.get("base"):
                        base_ids = s["base"]
                        break
                    elif s.get("type") in ("prism", "frustum") and s.get("base1"):
                        base_ids = s["base1"]
                        break

                base_pts = [p for p in pt_list if p.id in base_ids]
                if len(base_pts) >= 3:
                    p1, p2, p3 = base_pts[0], base_pts[1], base_pts[2]
                    if p1.x is None: equations.append(point_vars[p1.id][0])
                    if p1.y is None: equations.append(point_vars[p1.id][1])
                    if p1.z is None: equations.append(point_vars[p1.id][2])
                    if p2.y is None: equations.append(point_vars[p2.id][1])
                    if p2.z is None: equations.append(point_vars[p2.id][2])
                    if p3.z is None: equations.append(point_vars[p3.id][2])
                    for bp in base_pts[3:]:
                        if bp.z is None:
                            equations.append(point_vars[bp.id][2])
                else:
                    p1 = pt_list[0]
                    if p1.x is None: equations.append(point_vars[p1.id][0])
                    if p1.y is None: equations.append(point_vars[p1.id][1])
                    if p1.z is None: equations.append(point_vars[p1.id][2])
                    if len(pt_list) > 1:
                        p2 = pt_list[1]
                        if p2.y is None: equations.append(point_vars[p2.id][1])
                        if p2.z is None: equations.append(point_vars[p2.id][2])
                    if len(pt_list) > 2:
                        p3 = pt_list[2]
                        if p3.z is None: equations.append(point_vars[p3.id][2])
            else:
                p1 = pt_list[0]
                if p1.x is None: equations.append(point_vars[p1.id][0])
                if p1.y is None: equations.append(point_vars[p1.id][1])
                if is_3d and p1.z is None:
                    equations.append(point_vars[p1.id][2])

                if len(pt_list) > 1:
                    p2 = pt_list[1]
                    if p2.y is None: equations.append(point_vars[p2.id][1])
                    if is_3d and p2.z is None:
                        equations.append(point_vars[p2.id][2])

                if is_3d and len(pt_list) > 2:
                    p3 = pt_list[2]
                    if p3.z is None: equations.append(point_vars[p3.id][2])

        # Explicit coordinates
        for p in pt_list:
            if p.x is not None: equations.append(point_vars[p.id][0] - p.x)
            if p.y is not None: equations.append(point_vars[p.id][1] - p.y)
            if p.z is not None: equations.append(point_vars[p.id][2] - p.z)

        # Geometric constraints to algebraic equations
        for c in real_constraints:
            if c.type == 'length' and len(c.targets) == 2:
                p1, p2 = c.targets
                if p1 in point_vars and p2 in point_vars:
                    v1, v2 = point_vars[p1], point_vars[p2]
                    eq = (v2[0]-v1[0])**2 + (v2[1]-v1[1])**2 + (v2[2]-v1[2])**2 - float(c.value)**2
                    equations.append(eq)

            elif c.type == 'length_equal' and len(c.targets) == 4:
                pA, pB, pC, pD = c.targets
                if all(t in point_vars for t in [pA, pB, pC, pD]):
                    va, vb, vc, vd = point_vars[pA], point_vars[pB], point_vars[pC], point_vars[pD]
                    d1_sq = sum((vb[i]-va[i])**2 for i in range(3))
                    d2_sq = sum((vd[i]-vc[i])**2 for i in range(3))
                    equations.append(d1_sq - d2_sq)

            elif c.type == 'angle' and len(c.targets) >= 1:
                v_name = c.targets[0]
                if v_name in point_vars:
                    if len(c.targets) >= 3:
                        p1_name, p2_name = c.targets[1], c.targets[2]
                    else:
                        other_pts = [p.id for p in pt_list if p.id != v_name][:2]
                        if len(other_pts) < 2:
                            continue
                        p1_name, p2_name = other_pts

                    if p1_name in point_vars and p2_name in point_vars:
                        pV = point_vars[v_name]
                        p1_vars = point_vars[p1_name]
                        p2_vars = point_vars[p2_name]
                        v1 = [p1_vars[i] - pV[i] for i in range(3)]
                        v2 = [p2_vars[i] - pV[i] for i in range(3)]

                        if abs(float(c.value) - 90.0) < 1e-9:
                            eq = sum(v1[i]*v2[i] for i in range(3))
                        else:
                            cos_val = np.cos(np.deg2rad(float(c.value)))
                            d1_sq = sum(v1[i]**2 for i in range(3))
                            d2_sq = sum(v2[i]**2 for i in range(3))
                            dot = sum(v1[i]*v2[i] for i in range(3))
                            eq = dot**2 - (cos_val**2) * d1_sq * d2_sq
                        equations.append(eq)

            elif c.type == 'parallel' and len(c.targets) == 4:
                pA, pB, pC, pD = c.targets
                if all(t in point_vars for t in [pA, pB, pC, pD]):
                    va, vb, vc, vd = point_vars[pA], point_vars[pB], point_vars[pC], point_vars[pD]
                    v1 = [vb[i]-va[i] for i in range(3)]
                    v2 = [vd[i]-vc[i] for i in range(3)]
                    equations.append(v1[1]*v2[2] - v1[2]*v2[1])
                    equations.append(v1[2]*v2[0] - v1[0]*v2[2])
                    equations.append(v1[0]*v2[1] - v1[1]*v2[0])

            elif c.type == 'perpendicular' and len(c.targets) == 4:
                pA, pB, pC, pD = c.targets
                if all(t in point_vars for t in [pA, pB, pC, pD]):
                    va, vb, vc, vd = point_vars[pA], point_vars[pB], point_vars[pC], point_vars[pD]
                    dot = sum((vb[i]-va[i])*(vd[i]-vc[i]) for i in range(3))
                    equations.append(dot)

            elif c.type == 'perp_plane' and len(c.targets) >= 4:
                pL1, pL2 = c.targets[0], c.targets[1]
                plane_pts = c.targets[2:]
                if pL1 in point_vars and pL2 in point_vars and len(plane_pts) >= 2:
                    vL1, vL2 = point_vars[pL1], point_vars[pL2]
                    v_line = [vL2[i] - vL1[i] for i in range(3)]
                    p0 = point_vars[plane_pts[0]]
                    for pk_id in plane_pts[1:]:
                        if pk_id in point_vars:
                            pk = point_vars[pk_id]
                            v_plane = [pk[i] - p0[i] for i in range(3)]
                            dot = sum(v_line[i] * v_plane[i] for i in range(3))
                            equations.append(dot)

            elif c.type == 'midpoint' and len(c.targets) == 3:
                m_id, p1_id, p2_id = c.targets
                if all(t in point_vars for t in [m_id, p1_id, p2_id]):
                    vm, v1, v2 = point_vars[m_id], point_vars[p1_id], point_vars[p2_id]
                    for i in range(3):
                        equations.append(2*vm[i] - (v1[i] + v2[i]))

            elif c.type == 'collinear' and len(c.targets) >= 3:
                p_ref1, p_ref2 = c.targets[0], c.targets[1]
                if p_ref1 in point_vars and p_ref2 in point_vars:
                    v1, v2 = point_vars[p_ref1], point_vars[p_ref2]
                    v_dir = [v2[i] - v1[i] for i in range(3)]
                    for p_mid in c.targets[2:]:
                        if p_mid in point_vars:
                            vm = point_vars[p_mid]
                            v_m = [vm[i] - v1[i] for i in range(3)]
                            equations.append(v_dir[1]*v_m[2] - v_dir[2]*v_m[1])
                            equations.append(v_dir[2]*v_m[0] - v_dir[0]*v_m[2])
                            equations.append(v_dir[0]*v_m[1] - v_dir[1]*v_m[0])

            elif c.type == 'coplanar' and len(c.targets) >= 4:
                p0_id = c.targets[0]
                if p0_id in point_vars and len(c.targets) >= 4:
                    v0 = point_vars[p0_id]
                    v1 = point_vars.get(c.targets[1])
                    v2 = point_vars.get(c.targets[2])
                    if v1 and v2:
                        d1 = [v1[i]-v0[i] for i in range(3)]
                        d2 = [v2[i]-v0[i] for i in range(3)]
                        n = [
                            d1[1]*d2[2] - d1[2]*d2[1],
                            d1[2]*d2[0] - d1[0]*d2[2],
                            d1[0]*d2[1] - d1[1]*d2[0]
                        ]
                        for pk_id in c.targets[3:]:
                            vk = point_vars.get(pk_id)
                            if vk:
                                dk = [vk[i]-v0[i] for i in range(3)]
                                equations.append(sum(n[i]*dk[i] for i in range(3)))

            elif c.type == 'section' and len(c.targets) >= 3:
                pE, pA, pC = c.targets[0], c.targets[1], c.targets[2]
                if all(t in point_vars for t in [pE, pA, pC]):
                    k = float(c.value) if c.value is not None else 0.5
                    vE, vA, vC = point_vars[pE], point_vars[pA], point_vars[pC]
                    for i in range(3):
                        equations.append(vE[i] - (vA[i] + k * (vC[i] - vA[i])))

            elif c.type == 'point_on' and len(c.targets) >= 3:
                pP, pA, pB = c.targets[0], c.targets[1], c.targets[2]
                if all(t in point_vars for t in [pP, pA, pB]):
                    vp, va, vb = point_vars[pP], point_vars[pA], point_vars[pB]
                    v1 = [vp[i] - va[i] for i in range(3)]
                    v2 = [vb[i] - va[i] for i in range(3)]
                    equations.append(v1[1]*v2[2] - v1[2]*v2[1])
                    equations.append(v1[2]*v2[0] - v1[0]*v2[2])
                    equations.append(v1[0]*v2[1] - v1[1]*v2[0])

            elif c.type == 'point_on_plane' and len(c.targets) >= 4:
                pP, pA, pB, pC = c.targets[0], c.targets[1], c.targets[2], c.targets[3]
                if all(p in point_vars for p in [pP, pA, pB, pC]):
                    vp, va, vb, vc = point_vars[pP], point_vars[pA], point_vars[pB], point_vars[pC]
                    v1 = [vb[i] - va[i] for i in range(3)]
                    v2 = [vc[i] - va[i] for i in range(3)]
                    v3 = [vp[i] - va[i] for i in range(3)]
                    det = (
                        v1[0] * (v2[1] * v3[2] - v2[2] * v3[1])
                        - v1[1] * (v2[0] * v3[2] - v2[2] * v3[0])
                        + v1[2] * (v2[0] * v3[1] - v2[1] * v3[0])
                    )
                    equations.append(det)

            elif c.type == 'center' and len(c.targets) >= 3:
                pO = c.targets[0]
                poly_pts = c.targets[1:]
                if pO in point_vars and all(p in point_vars for p in poly_pts):
                    vO = point_vars[pO]
                    n_pts = len(poly_pts)
                    for i in range(3):
                        eq_center = n_pts * vO[i] - sum(point_vars[p][i] for p in poly_pts)
                        equations.append(eq_center)

            elif c.type == 'ratio_point' and len(c.targets) >= 3:
                pP, pA, pB = c.targets[0], c.targets[1], c.targets[2]
                if all(t in point_vars for t in [pP, pA, pB]):
                    k = float(c.value) if c.value is not None else 0.5
                    vP, vA, vB = point_vars[pP], point_vars[pA], point_vars[pB]
                    for i in range(3):
                        equations.append(vP[i] - (vA[i] + k * (vB[i] - vA[i])))

            elif c.type == 'vector_sum' and len(c.targets) >= 3:
                pC, pA, pB = c.targets[0], c.targets[1], c.targets[2]
                p0 = c.targets[3] if len(c.targets) > 3 else None
                if all(t in point_vars for t in [pC, pA, pB]):
                    vC, vA, vB = point_vars[pC], point_vars[pA], point_vars[pB]
                    v0 = point_vars[p0] if (p0 and p0 in point_vars) else (0, 0, 0)
                    for i in range(3):
                        equations.append((vC[i] - v0[i]) - ((vA[i] - v0[i]) + (vB[i] - v0[i])))


        return CompiledSystem(
            pt_list=pt_list,
            point_vars=point_vars,
            equations=equations,
            polygon_order=polygon_order,
            circles_meta=circles_meta,
            solids_meta=solids_meta,
            segments_meta=segments_meta,
            lines_ext=lines_ext,
            rays_ext=rays_ext,
            real_constraints=real_constraints,
        )
