import json
import sympy as sp
import numpy as np
import logging
import string
from typing import List, Dict, Any
from .models import Point, Constraint

logger = logging.getLogger(__name__)


class GeometryEngine:
    def solve(self, points: List[Point], constraints: List[Constraint], is_3d: bool = False) -> Dict[str, Any] | None:
        if not points:
            logger.error("[GeometryEngine] No points to solve.")
            return None

        logger.info(f"==[GeometryEngine] Starting solve with {len(points)} points, {len(constraints)} constraints (is_3d={is_3d})==")

        # ── Separate metadata constraints from real ones ──────────────────────
        polygon_order: List[str] = []
        circles_meta: List[Dict] = []
        solids_meta: List[Dict] = []
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

        pt_list = list(points.values()) if isinstance(points, dict) else points

        # ── Step 0: Try Canonical Hierarchical Constructor (P1) ─────────────
        from .constructors import StandardGeometryConstructor
        constructor = StandardGeometryConstructor()
        canonical_res = constructor.try_construct(pt_list, real_constraints, solids_meta, is_3d)
        if canonical_res and "coordinates" in canonical_res:
            logger.info("[GeometryEngine] Successfully constructed canonical standard representation.")
            return self._build_result(
                canonical_res["coordinates"],
                polygon_order,
                circles_meta,
                solids_meta,
                segments_meta,
                lines_ext,
                rays_ext,
                pt_list,
            )

        # ── Setup symbols ─────────────────────────────────────────────────────
        point_vars: Dict[str, tuple] = {}
        equations = []

        for p in pt_list:
            x = sp.Symbol(f"{p.id}_x")
            y = sp.Symbol(f"{p.id}_y")
            z = sp.Symbol(f"{p.id}_z")
            point_vars[p.id] = (x, y, z)
            logger.debug(f"[GeometryEngine]   Symbol: ({p.id}_x, {p.id}_y, {p.id}_z)")

            # If 2D problem, pin all z to 0 immediately
            if not is_3d:
                equations.append(z)

        # ── Anchor logic to fix translation + rotation DOF ────────────────────
        # ONLY anchor if NO point has explicit coordinates
        has_explicit = any(p.x is not None or p.y is not None for p in pt_list)
        if not has_explicit and len(pt_list) > 0:
            if is_3d and solids_meta:
                # Find base points from pyramid / prism / frustum
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
                    # Fix base vertex 1 at (0,0,0)
                    if p1.x is None: equations.append(point_vars[p1.id][0])
                    if p1.y is None: equations.append(point_vars[p1.id][1])
                    if p1.z is None: equations.append(point_vars[p1.id][2])
                    # Fix base vertex 2 on X-axis (y=0, z=0)
                    if p2.y is None: equations.append(point_vars[p2.id][1])
                    if p2.z is None: equations.append(point_vars[p2.id][2])
                    # Fix base vertex 3 on XY-plane (z=0)
                    if p3.z is None: equations.append(point_vars[p3.id][2])
                    # Pin all base vertices to z=0 (ground plane)
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
                # Translation: fix p1 at (0,0) or (0,0,0)
                if p1.x is None: equations.append(point_vars[p1.id][0]); logger.debug(f"Anchor {p1.id}_x=0")
                if p1.y is None: equations.append(point_vars[p1.id][1]); logger.debug(f"Anchor {p1.id}_y=0")
                if is_3d and p1.z is None:
                    equations.append(point_vars[p1.id][2]); logger.debug(f"Anchor {p1.id}_z=0")

                if len(pt_list) > 1:
                    p2 = pt_list[1]
                    # Rotation: fix p2 on X-axis (y=0)
                    if p2.y is None: equations.append(point_vars[p2.id][1]); logger.debug(f"Anchor {p2.id}_y=0")
                    if is_3d and p2.z is None:
                        equations.append(point_vars[p2.id][2]); logger.debug(f"Anchor {p2.id}_z=0")

                if is_3d and len(pt_list) > 2:
                    p3 = pt_list[2]
                    # Planar rotation: fix p3 on XY-plane (z=0)
                    if p3.z is None: equations.append(point_vars[p3.id][2]); logger.debug(f"Anchor {p3.id}_z=0")

        # ── Build equations from explicit point coordinates ──────────────────
        for p in pt_list:
            if p.x is not None:
                equations.append(point_vars[p.id][0] - p.x)
            if p.y is not None:
                equations.append(point_vars[p.id][1] - p.y)
            if p.z is not None:
                equations.append(point_vars[p.id][2] - p.z)

        # ── Build equations from constraints ──────────────────────────────────
        for c in real_constraints:
            logger.debug(f"[GeometryEngine]   Processing constraint: type={c.type}, targets={c.targets}, value={c.value}")

            if c.type == 'length' and len(c.targets) == 2:
                p1, p2 = c.targets
                if p1 not in point_vars or p2 not in point_vars:
                    logger.warning(f"[GeometryEngine]   Skip length: {c.targets} not in symbols.")
                    continue
                v1, v2 = point_vars[p1], point_vars[p2]
                eq = (v2[0]-v1[0])**2 + (v2[1]-v1[1])**2 + (v2[2]-v1[2])**2 - float(c.value)**2
                equations.append(eq)
                logger.debug(f"[GeometryEngine]     -> Length eq (3D): |{p1}{p2}|² = {c.value}²")

            elif c.type == 'length_equal' and len(c.targets) == 4:
                pA, pB, pC, pD = c.targets
                if all(t in point_vars for t in [pA, pB, pC, pD]):
                    va, vb, vc, vd = point_vars[pA], point_vars[pB], point_vars[pC], point_vars[pD]
                    d1_sq = sum((vb[i]-va[i])**2 for i in range(3))
                    d2_sq = sum((vd[i]-vc[i])**2 for i in range(3))
                    equations.append(d1_sq - d2_sq)
                    logger.debug(f"[GeometryEngine]     -> LengthEqual: |{pA}{pB}| = |{pC}{pD}|")

            elif c.type == 'angle' and len(c.targets) >= 1:
                v_name = c.targets[0]
                if v_name not in point_vars:
                    continue
                if len(c.targets) >= 3:
                    p1_name, p2_name = c.targets[1], c.targets[2]
                else:
                    other_pts = [p.id for p in pt_list if p.id != v_name][:2]
                    if len(other_pts) < 2: continue
                    p1_name, p2_name = other_pts

                pV = point_vars[v_name]
                p1_vars = point_vars[p1_name]
                p2_vars = point_vars[p2_name]

                v1 = [p1_vars[i] - pV[i] for i in range(3)]
                v2 = [p2_vars[i] - pV[i] for i in range(3)]

                if abs(float(c.value) - 90.0) < 1e-9:
                    eq = sum(v1[i]*v2[i] for i in range(3))
                    logger.debug(f"[GeometryEngine]     -> Angle eq at {v_name} (90° dot=0)")
                else:
                    cos_val = np.cos(np.deg2rad(float(c.value)))
                    d1_sq = sum(v1[i]**2 for i in range(3))
                    d2_sq = sum(v2[i]**2 for i in range(3))
                    dot = sum(v1[i]*v2[i] for i in range(3))
                    eq = dot**2 - (cos_val**2) * d1_sq * d2_sq
                    logger.debug(f"[GeometryEngine]     -> Angle eq at {v_name} ({c.value}° cos² relation)")
                equations.append(eq)

            elif c.type == 'parallel' and len(c.targets) == 4:
                pA, pB, pC, pD = c.targets
                if any(t not in point_vars for t in [pA, pB, pC, pD]): continue
                va, vb, vc, vd = point_vars[pA], point_vars[pB], point_vars[pC], point_vars[pD]
                v1 = [vb[i]-va[i] for i in range(3)]
                v2 = [vd[i]-vc[i] for i in range(3)]
                equations.append(v1[1]*v2[2] - v1[2]*v2[1])
                equations.append(v1[2]*v2[0] - v1[0]*v2[2])
                equations.append(v1[0]*v2[1] - v1[1]*v2[0])
                logger.debug(f"[GeometryEngine]     -> Parallel eq (3D cross=0): {pA}{pB} || {pC}{pD}")

            elif c.type == 'perpendicular' and len(c.targets) == 4:
                pA, pB, pC, pD = c.targets
                if any(t not in point_vars for t in [pA, pB, pC, pD]): continue
                va, vb, vc, vd = point_vars[pA], point_vars[pB], point_vars[pC], point_vars[pD]
                dot = sum((vb[i]-va[i])*(vd[i]-vc[i]) for i in range(3))
                equations.append(dot)
                logger.debug(f"[GeometryEngine]     -> Perpendicular eq (3D dot=0): {pA}{pB} ⊥ {pC}{pD}")

            elif c.type == 'perp_plane' and len(c.targets) >= 4:
                pL1, pL2 = c.targets[0], c.targets[1]
                plane_pts = c.targets[2:]
                if pL1 in point_vars and pL2 in point_vars and len(plane_pts) >= 2:
                    vL1, vL2 = point_vars[pL1], point_vars[pL2]
                    v_line = [vL2[i] - vL1[i] for i in range(3)]

                    pP0, pP1 = plane_pts[0], plane_pts[1]
                    if pP0 in point_vars and pP1 in point_vars:
                        vP0, vP1 = point_vars[pP0], point_vars[pP1]
                        v_plane1 = [vP1[i] - vP0[i] for i in range(3)]
                        equations.append(sum(v_line[i] * v_plane1[i] for i in range(3)))
                        logger.debug(f"[GeometryEngine]     -> PerpPlane dot 1: {pL1}{pL2} ⊥ {pP0}{pP1}")

                    pP2 = plane_pts[2] if len(plane_pts) > 2 else plane_pts[-1]
                    if pP2 != pP1 and pP2 in point_vars and pP0 in point_vars:
                        vP2 = point_vars[pP2]
                        v_plane2 = [vP2[i] - vP0[i] for i in range(3)]
                        equations.append(sum(v_line[i] * v_plane2[i] for i in range(3)))
                        logger.debug(f"[GeometryEngine]     -> PerpPlane dot 2: {pL1}{pL2} ⊥ {pP0}{pP2}")

            elif c.type == 'coplanar' and len(c.targets) >= 4:
                pA, pB, pC, pD = c.targets[0], c.targets[1], c.targets[2], c.targets[3]
                if all(p in point_vars for p in [pA, pB, pC, pD]):
                    va, vb, vc, vd = point_vars[pA], point_vars[pB], point_vars[pC], point_vars[pD]
                    v1 = [vb[i] - va[i] for i in range(3)]
                    v2 = [vc[i] - va[i] for i in range(3)]
                    v3 = [vd[i] - va[i] for i in range(3)]
                    det = (
                        v1[0] * (v2[1] * v3[2] - v2[2] * v3[1])
                        - v1[1] * (v2[0] * v3[2] - v2[2] * v3[0])
                        + v1[2] * (v2[0] * v3[1] - v2[1] * v3[0])
                    )
                    equations.append(det)
                    logger.debug(f"[GeometryEngine]     -> Coplanar eq (det=0): {pA}, {pB}, {pC}, {pD}")

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
                    logger.debug(f"[GeometryEngine]     -> PointOnPlane eq (det=0): {pP} on plane({pA},{pB},{pC})")

            elif c.type == 'midpoint' and len(c.targets) == 3:
                pM, pA, pB = c.targets
                if any(t not in point_vars for t in [pM, pA, pB]): continue
                vM, vA, vB = point_vars[pM], point_vars[pA], point_vars[pB]
                for i in range(3):
                    equations.append(2*vM[i] - vA[i] - vB[i])
                logger.debug(f"[GeometryEngine]     -> Midpoint eq (3D): {pM} = mid({pA},{pB})")

            elif c.type == 'section' and len(c.targets) == 3:
                pE, pA, pC = c.targets
                if any(t not in point_vars for t in [pE, pA, pC]): continue
                vE, vA, vC = point_vars[pE], point_vars[pA], point_vars[pC]
                k = float(c.value)
                for i in range(3):
                    equations.append(vE[i] - (vA[i] + k * (vC[i] - vA[i])))
                logger.debug(f"[GeometryEngine]     -> Section eq (3D): {pE} = {pA} + {k}({pC}-{pA})")

            elif c.type == 'point_on' and len(c.targets) == 3:
                pP, pA, pB = c.targets
                if all(t in point_vars for t in [pP, pA, pB]):
                    vp, va, vb = point_vars[pP], point_vars[pA], point_vars[pB]
                    v1 = [vp[i] - va[i] for i in range(3)]
                    v2 = [vb[i] - va[i] for i in range(3)]
                    equations.append(v1[1]*v2[2] - v1[2]*v2[1])
                    equations.append(v1[2]*v2[0] - v1[0]*v2[2])
                    equations.append(v1[0]*v2[1] - v1[1]*v2[0])
                    logger.debug(f"[GeometryEngine]     -> PointOn eq (3D cross=0): {pP} on line {pA}{pB}")

            elif c.type == 'center' and len(c.targets) >= 3:
                pO = c.targets[0]
                poly_pts = c.targets[1:]
                if pO in point_vars and all(p in point_vars for p in poly_pts):
                    vO = point_vars[pO]
                    n_pts = len(poly_pts)
                    for i in range(3):
                        eq_center = n_pts * vO[i] - sum(point_vars[p][i] for p in poly_pts)
                        equations.append(eq_center)
                    logger.debug(f"[GeometryEngine]     -> Center eq: {pO} = mean({poly_pts})")

        all_vars = []
        for v in point_vars.values():
            all_vars.extend(v)

        n_eqs = len(equations)
        n_vars = len(all_vars)
        logger.info(f"[GeometryEngine] Built {n_eqs} equations for {n_vars} unknowns.")

        # ── Strategy 1: SymPy symbolic ───────────────────────────────────────
        coords = self._try_symbolic(equations, all_vars, point_vars)

        if coords:
            return self._build_result(coords, polygon_order, circles_meta, solids_meta, segments_meta, lines_ext, rays_ext, pt_list)

        # ── Strategy 2: Numerical nsolve ─────────────────────────────────────
        if n_eqs == n_vars:
            coords = self._try_nsolve(equations, all_vars, point_vars, n_vars)
            if coords:
                return self._build_result(coords, polygon_order, circles_meta, solids_meta, segments_meta, lines_ext, rays_ext, pt_list)

        # ── Strategy 3: Scipy least-squares ─────────────────────────────────
        coords = self._try_lsq(equations, all_vars, point_vars, n_vars)
        if coords:
            return self._build_result(coords, polygon_order, circles_meta, solids_meta, segments_meta, lines_ext, rays_ext, pt_list)

        # ── Strategy 4: Differential evolution ──────────────────────────────
        coords = self._try_global(equations, all_vars, point_vars, n_vars)
        if coords:
            return self._build_result(coords, polygon_order, circles_meta, solids_meta, segments_meta, lines_ext, rays_ext, pt_list)

        logger.error("[GeometryEngine] All strategies exhausted.")
        return None

    # ─── Solving strategies ──────────────────────────────────────────────────

    def _try_symbolic(self, equations, all_vars, point_vars):
        if len(all_vars) > 10 or len(equations) != len(all_vars):
            logger.info(f"[GeometryEngine] Strategy 1: Skipping symbolic solve on non-square/large system ({len(equations)} eqs, {len(all_vars)} vars).")
            return None

        try:
            solution = sp.solve(equations, all_vars, dict=True)
            if solution:
                # Prefer solutions where z >= 0 for apexes
                best_res = solution[0]
                for candidate in solution:
                    z_vals = [float(candidate.get(vz, 0.0)) for _, (_, _, vz) in point_vars.items()]
                    if all(z >= -1e-6 for z in z_vals):
                        best_res = candidate
                        break
                    elif any(z > 1e-6 for z in z_vals):
                        best_res = candidate

                logger.info("[GeometryEngine] Strategy 1 (SymPy symbolic): SUCCESS.")
                logger.debug(f"[GeometryEngine] Symbolic solution: {best_res}")
                return {pid: [abs(float(best_res.get(vx, 0.0))), abs(float(best_res.get(vy, 0.0))), abs(float(best_res.get(vz, 0.0)))] if (float(best_res.get(vz, 0.0)) < 0 and float(best_res.get(vx, 0.0)) >= 0 and float(best_res.get(vy, 0.0)) >= 0) else [float(best_res.get(vx, 0.0)), float(best_res.get(vy, 0.0)), abs(float(best_res.get(vz, 0.0)))]
                        for pid, (vx, vy, vz) in point_vars.items()}
            else:
                logger.warning("[GeometryEngine] Strategy 1 returned no solution. Trying numerical...")
        except Exception as e:
            logger.warning(f"[GeometryEngine] Strategy 1 threw exception: {e}. Trying numerical...")
        return None

    def _try_nsolve(self, equations, all_vars, point_vars, n_vars):
        MAX_NSOLVE_ATTEMPTS = 15
        logger.info(f"[GeometryEngine] Strategy 2 (nsolve): square system ({n_vars}x{n_vars}). Trying {MAX_NSOLVE_ATTEMPTS} random starts...")
        import random
        for attempt in range(MAX_NSOLVE_ATTEMPTS):
            try:
                scale = 10 if attempt < 5 else (100 if attempt < 10 else 1)
                guesses = [random.uniform(-scale, scale) for _ in all_vars]
                sol_vals = sp.nsolve(equations, all_vars, guesses, tol=1e-6, maxsteps=1000)
                res = {var: float(val) for var, val in zip(all_vars, sol_vals)}
                logger.info(f"[GeometryEngine] Strategy 2 (nsolve): SUCCESS on attempt {attempt + 1}.")
                return {pid: [float(res.get(vx, 0.0)), float(res.get(vy, 0.0)), float(res.get(vz, 0.0))]
                        for pid, (vx, vy, vz) in point_vars.items()}
            except Exception as e:
                logger.debug(f"[GeometryEngine]   nsolve attempt {attempt + 1} failed: {e}")
        return None

    def _try_lsq(self, equations, all_vars, point_vars, n_vars):
        logger.info("[GeometryEngine] Strategy 3 (scipy least-squares): minimizing residuals...")
        try:
            from scipy.optimize import least_squares, minimize
            eq_funcs = [sp.lambdify(all_vars, eq, 'numpy') for eq in equations]

            def residuals(x):
                return np.array([float(f(*x)) for f in eq_funcs], dtype=float)

            def objective(x):
                res = residuals(x)
                return float(np.sum(res**2))

            best_res, best_val = None, float('inf')
            for i in range(12):
                if i == 0:
                    x0 = [1.0] * n_vars
                elif i < 4:
                    x0 = [float(np.random.uniform(-10, 10)) for _ in range(n_vars)]
                else:
                    x0 = [float(np.random.uniform(-50, 50)) for _ in range(n_vars)]

                try:
                    res = least_squares(residuals, x0, method='trf', ftol=1e-12, xtol=1e-12, gtol=1e-12, max_nfev=2000)
                    cost = float(res.cost) * 2.0
                    if cost < best_val:
                        best_val, best_res = cost, res
                    if best_val < 1e-8:
                        break
                except Exception:
                    res = minimize(objective, x0, method='L-BFGS-B', options={'ftol': 1e-14, 'gtol': 1e-12})
                    if res.fun < best_val:
                        best_val, best_res = res.fun, res
                    if best_val < 1e-8:
                        break

            TOLERANCE = 1e-4
            logger.info(f"[GeometryEngine] Strategy 3: best residual = {best_val:.2e} (tol={TOLERANCE})")
            if best_val < TOLERANCE and best_res is not None:
                sol_x = best_res.x if hasattr(best_res, 'x') else best_res
                res = {var: float(val) for var, val in zip(all_vars, sol_x)}
                logger.info("[GeometryEngine] Strategy 3 (least-squares): SUCCESS.")
                return {pid: [float(res.get(vx, 0.0)), float(res.get(vy, 0.0)), float(res.get(vz, 0.0))]
                        for pid, (vx, vy, vz) in point_vars.items()}
            else:
                logger.warning(f"[GeometryEngine] Strategy 3 failed: residual {best_val:.2e} > {TOLERANCE}")
        except Exception as e:
            logger.error(f"[GeometryEngine] Strategy 3 threw exception: {e}")
        return None

    def _try_global(self, equations, all_vars, point_vars, n_vars):
        logger.info("[GeometryEngine] Strategy 4 (Differential Evolution): global search...")
        try:
            from scipy.optimize import differential_evolution
            bounds = [(-20, 20)] * n_vars
            eq_funcs = [sp.lambdify(all_vars, eq, 'numpy') for eq in equations]

            def obj(x):
                s = 0.0
                for f in eq_funcs:
                    try:
                        s += float(f(*x))**2
                    except Exception:
                        s += 1e6
                return s

            result = differential_evolution(obj, bounds, maxiter=500, popsize=15, mutation=(0.5, 1), recombination=0.7)
            TOLERANCE = 1e-3
            logger.info(f"[GeometryEngine] Strategy 4: best residual = {result.fun:.2e} (tol={TOLERANCE})")
            if result.fun < TOLERANCE:
                res = {var: float(val) for var, val in zip(all_vars, result.x)}
                logger.info("[GeometryEngine] Strategy 4 (global opt): SUCCESS.")
                return {pid: [float(res.get(vx, 0)), float(res.get(vy, 0)), float(res.get(vz, 0))]
                        for pid, (vx, vy, vz) in point_vars.items()}
        except Exception as e:
            logger.error(f"[GeometryEngine] Strategy 4 threw exception: {e}")
        return None

    # ─── Result builder ──────────────────────────────────────────────────────

    def _build_result(
        self,
        coords: Dict[str, List[float]],
        polygon_order: List[str],
        circles_meta: List[Dict],
        solids_meta: List[Dict],
        segments_meta: List[List[str]],
        lines_meta: List[List[str]],
        rays_meta: List[List[str]],
        pt_list: List[Point],
    ) -> Dict[str, Any]:
        """
        Build structured result including drawing phases, faces and 3D solids for renderers.
        """
        all_ids = [p.id for p in pt_list]

        # Ensure canonical positive orientation (y >= 0 for base vertices, z >= 0 for apexes)
        has_explicit_pts = {p.id for p in pt_list if p.x is not None or p.y is not None or p.z is not None}
        if not any(p.id in has_explicit_pts and (p.y is not None and p.y < -1e-4) for p in pt_list):
            y_vals = [coords[pid][1] for pid in coords if pid in coords and pid not in has_explicit_pts]
            if y_vals and sum(1 for y in y_vals if y < -1e-4) > sum(1 for y in y_vals if y > 1e-4):
                for pid in coords:
                    if pid not in has_explicit_pts:
                        coords[pid][1] = -coords[pid][1]

        if not any(p.id in has_explicit_pts and (p.z is not None and p.z < -1e-4) for p in pt_list):
            z_vals = [coords[pid][2] for pid in coords if len(coords[pid]) >= 3 and pid not in has_explicit_pts]
            if z_vals and sum(1 for z in z_vals if z < -1e-4) > sum(1 for z in z_vals if z > 1e-4):
                for pid in coords:
                    if len(coords[pid]) >= 3 and pid not in has_explicit_pts:
                        coords[pid][2] = -coords[pid][2]

        # Clean float zero residuals and restore explicit coordinates
        for p in pt_list:
            if p.id in coords:
                if p.x is not None:
                    coords[p.id][0] = float(p.x)
                elif abs(coords[p.id][0]) < 1e-10:
                    coords[p.id][0] = 0.0

                if p.y is not None:
                    coords[p.id][1] = float(p.y)
                elif abs(coords[p.id][1]) < 1e-10:
                    coords[p.id][1] = 0.0

                if len(coords[p.id]) >= 3:
                    if p.z is not None:
                        coords[p.id][2] = float(p.z)
                    elif abs(coords[p.id][2]) < 1e-10:
                        coords[p.id][2] = 0.0

        for pid in list(coords.keys()):
            for idx in range(len(coords[pid])):
                if abs(coords[pid][idx]) < 1e-10:
                    coords[pid][idx] = 0.0

        if not polygon_order:
            base_pts = sorted(
                all_ids,
                key=lambda p: (string.ascii_uppercase.index(p) if p in string.ascii_uppercase else 100, p)
            )
            polygon_order = base_pts

        base_ids = [pid for pid in polygon_order if pid in all_ids]
        derived_ids = [pid for pid in all_ids if pid not in polygon_order]

        drawn_segments = set()

        def add_segment(p1, p2, target_list):
            if p1 == p2:
                return
            s = frozenset([p1, p2])
            if s not in drawn_segments:
                drawn_segments.add(s)
                target_list.append([p1, p2])

        # Phase 1: Main polygon / base shape boundary
        phase1_segments = []
        if len(base_ids) >= 2:
            for i in range(len(base_ids) - 1):
                add_segment(base_ids[i], base_ids[i+1], phase1_segments)
            if len(base_ids) > 2:
                add_segment(base_ids[-1], base_ids[0], phase1_segments)

        # Phase 2: Auxiliary segments from DSL and 3D solids
        phase2_segments = []
        for p1, p2 in segments_meta:
            add_segment(p1, p2, phase2_segments)

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

        # Generate 3D polygonal faces for semi-transparent rendering
        faces: List[List[str]] = []
        for solid in solids_meta:
            s_type = solid.get("type")
            if s_type == "pyramid":
                base = solid.get("base", [])
                apex = solid.get("apex")
                if len(base) >= 3:
                    faces.append(base)
                    for i in range(len(base)):
                        faces.append([apex, base[i], base[(i+1)%len(base)]])
            elif s_type in ("prism", "cube", "cuboid", "frustum"):
                b1 = solid.get("base1", [])
                b2 = solid.get("base2", [])
                if len(b1) >= 3 and len(b2) >= 3 and len(b1) == len(b2):
                    faces.append(b1)
                    faces.append(b2)
                    for i in range(len(b1)):
                        i_next = (i + 1) % len(b1)
                        faces.append([b1[i], b1[i_next], b2[i_next], b2[i]])
            elif s_type == "tetrahedron":
                pts = solid.get("points", [])
                if len(pts) >= 4:
                    faces.append([pts[1], pts[2], pts[3]])
                    faces.append([pts[0], pts[1], pts[2]])
                    faces.append([pts[0], pts[2], pts[3]])
                    faces.append([pts[0], pts[3], pts[1]])

        return {
            "coordinates": coords,
            "polygon_order": polygon_order,
            "circles": circles_meta,
            "solids": solids_meta,
            "faces": faces,
            "lines": lines_meta,
            "rays": rays_meta,
            "drawing_phases": drawing_phases,
        }
