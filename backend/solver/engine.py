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
        segments_meta: List[List[str]] = []
        real_constraints: List[Constraint] = []

        for c in constraints:
            if c.type == 'polygon_order':
                polygon_order = list(c.targets)
            elif c.type == 'explicit_points' and not polygon_order:
                polygon_order = list(c.targets)
            elif c.type == 'circle':
                circles_meta.append({"center": c.targets[0], "radius": float(c.value)})
                real_constraints.append(c)
            elif c.type == 'segment':
                segments_meta.append(list(c.targets))
                # don't add to equations — pure drawing annotation
            elif c.type == 'lines_metadata':
                lines_meta_list = [t.split(',') for t in c.targets]
                real_constraints.append(c) # for passing to builder? or just keep here
            elif c.type == 'rays_metadata':
                rays_meta_list = [t.split(',') for t in c.targets]
                real_constraints.append(c)
            else:
                real_constraints.append(c)

        # ── Setup symbols ─────────────────────────────────────────────────────
        point_vars: Dict[str, tuple] = {}
        equations = []

        # Convert to list for stable indexing and to handle both Dict and List inputs
        pt_list = list(points.values()) if isinstance(points, dict) else points

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
        # Skip anchoring if points already have explicit coordinates that fix DOFs
        
        if len(pt_list) > 0:
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
                # 3D distance
                eq = (v2[0]-v1[0])**2 + (v2[1]-v1[1])**2 + (v2[2]-v1[2])**2 - float(c.value)**2
                equations.append(eq)
                logger.debug(f"[GeometryEngine]     -> Length eq (3D): |{p1}{p2}|² = {c.value}²")

            elif c.type == 'angle' and len(c.targets) >= 1:
                # In 3D, 'angle' usually refers to the angle between two vectors (e.g., ∠BAC)
                v_name = c.targets[0]
                if v_name not in point_vars:
                    continue
                # For simplicity, we assume the next two points in targets or fallback to first 2 others
                if len(c.targets) >= 3:
                    p1_name, p2_name = c.targets[1], c.targets[2]
                else:
                    other_pts = [p.id for p in pt_list if p.id != v_name][:2]
                    if len(other_pts) < 2: continue
                    p1_name, p2_name = other_pts
                
                pV = point_vars[v_name]
                p1_vars = point_vars[p1_name]
                p2_vars = point_vars[p2_name]
                
                # Vectors V1 and V2
                v1 = [p1_vars[i] - pV[i] for i in range(3)]
                v2 = [p2_vars[i] - pV[i] for i in range(3)]
                
                # Dot product relation: v1.v2 = |v1||v2| cos(theta)
                # But we use the tangent relation or square it to avoid sqrt if possible
                # If 90 deg: dot product = 0
                if abs(float(c.value) - 90.0) < 1e-9:
                    eq = sum(v1[i]*v2[i] for i in range(3))
                    logger.debug(f"[GeometryEngine]     -> Angle eq at {v_name} (90° dot=0)")
                else:
                    # Generic angle using law of cosines (squared)
                    cos_val = np.cos(np.deg2rad(float(c.value)))
                    d1_sq = sum(v1[i]**2 for i in range(3))
                    d2_sq = sum(v2[i]**2 for i in range(3))
                    dot = sum(v1[i]*v2[i] for i in range(3))
                    eq = dot**2 - (cos_val**2) * d1_sq * d2_sq
                    # Note: this allows theta and 180-theta. 
                    # Better: dot - cos(theta) * sqrt(d1_sq * d2_sq) = 0, but that has sqrt.
                    logger.debug(f"[GeometryEngine]     -> Angle eq at {v_name} ({c.value}° cos² relation)")
                equations.append(eq)

            elif c.type == 'parallel' and len(c.targets) == 4:
                pA, pB, pC, pD = c.targets
                if any(t not in point_vars for t in [pA, pB, pC, pD]): continue
                va, vb, vc, vd = point_vars[pA], point_vars[pB], point_vars[pC], point_vars[pD]
                # AB || CD means vector(AB) = lambda * vector(CD)
                # In 3D, cross product = 0. (b-a) x (d-c) = 0
                v1 = [vb[i]-va[i] for i in range(3)]
                v2 = [vd[i]-vc[i] for i in range(3)]
                # Cross product components:
                equations.append(v1[1]*v2[2] - v1[2]*v2[1])
                equations.append(v1[2]*v2[0] - v1[0]*v2[2])
                equations.append(v1[0]*v2[1] - v1[1]*v2[0])
                logger.debug(f"[GeometryEngine]     -> Parallel eq (3D cross=0): {pA}{pB} || {pC}{pD}")

            elif c.type == 'perpendicular' and len(c.targets) == 4:
                pA, pB, pC, pD = c.targets
                if any(t not in point_vars for t in [pA, pB, pC, pD]): continue
                va, vb, vc, vd = point_vars[pA], point_vars[pB], point_vars[pC], point_vars[pD]
                # Dot product = 0
                dot = sum((vb[i]-va[i])*(vd[i]-vc[i]) for i in range(3))
                equations.append(dot)
                logger.debug(f"[GeometryEngine]     -> Perpendicular eq (3D dot=0): {pA}{pB} ⊥ {pC}{pD}")

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

            elif c.type == 'circle':
                # Circle doesn't add position constraints for center (already a point)
                logger.debug(f"[GeometryEngine]     -> Circle: center={c.targets[0]}, r={c.value} (meta only)")

        all_vars = []
        for v in point_vars.values():
            all_vars.extend(v)

        n_eqs = len(equations)
        n_vars = len(all_vars)
        logger.info(f"[GeometryEngine] Built {n_eqs} equations for {n_vars} unknowns.")

        # ── Strategy 1: SymPy symbolic ───────────────────────────────────────
        coords = self._try_symbolic(equations, all_vars, point_vars)
        
        # Extract lines/rays from constraints for builder
        lines_ext = []
        rays_ext = []
        for c in constraints:
            if c.type == 'lines_metadata':
                lines_ext = [t.split(',') for t in c.targets]
            if c.type == 'rays_metadata':
                rays_ext = [t.split(',') for t in c.targets]

        if coords:
            return self._build_result(coords, polygon_order, circles_meta, segments_meta, lines_ext, rays_ext, pt_list)

        # ── Strategy 2: Numerical nsolve ─────────────────────────────────────
        if n_eqs == n_vars:
            coords = self._try_nsolve(equations, all_vars, point_vars, n_vars)
            if coords:
                return self._build_result(coords, polygon_order, circles_meta, segments_meta, lines_ext, rays_ext, pt_list)

        # ── Strategy 3: Scipy least-squares ─────────────────────────────────
        coords = self._try_lsq(equations, all_vars, point_vars, n_vars)
        if coords:
            return self._build_result(coords, polygon_order, circles_meta, segments_meta, lines_ext, rays_ext, pt_list)

        # ── Strategy 4: Differential evolution ──────────────────────────────
        coords = self._try_global(equations, all_vars, point_vars, n_vars)
        if coords:
            return self._build_result(coords, polygon_order, circles_meta, segments_meta, lines_ext, rays_ext, pt_list)

        logger.error("[GeometryEngine] All strategies exhausted.")
        return None

    # ─── Solving strategies ──────────────────────────────────────────────────

    def _try_symbolic(self, equations, all_vars, point_vars):
        # Optimization: SymPy's symbolic solver becomes extremely slow for many variables.
        # For 3D problems (usually 12-18+ variables), we prefer using numerical methods directly.
        if len(all_vars) > 10:
            logger.info(f"[GeometryEngine] Strategy 1: Skipping symbolic solve due to high variable count ({len(all_vars)}).")
            return None

        try:
            solution = sp.solve(equations, all_vars, dict=True)
            if solution:
                res = solution[0]
                logger.info("[GeometryEngine] Strategy 1 (SymPy symbolic): SUCCESS.")
                logger.debug(f"[GeometryEngine] Symbolic solution: {res}")
                return {pid: [float(res.get(vx, 0.0)), float(res.get(vy, 0.0)), float(res.get(vz, 0.0))]
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
                # Use varying scales for the random guesses to handle different problem sizes
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
            from scipy.optimize import minimize
            eq_funcs = [sp.lambdify(all_vars, eq, 'numpy') for eq in equations]

            def objective(x):
                return sum(float(f(*x))**2 for f in eq_funcs)

            best_res, best_val = None, float('inf')
            # Increase restarts for better coverage of local minima
            for i in range(12):
                if i == 0:
                    x0 = [1.0]*n_vars
                elif i < 4:
                    x0 = [np.random.uniform(-10, 10) for _ in range(n_vars)]
                else:
                    x0 = [np.random.uniform(-100, 100) for _ in range(n_vars)]
                
                res = minimize(objective, x0, method='L-BFGS-B')
                if res.fun < best_val:
                    best_val, best_res = res.fun, res
                if best_val < 1e-6:
                    break

            TOLERANCE = 1e-4
            logger.info(f"[GeometryEngine] Strategy 3: best residual = {best_val:.2e} (tol={TOLERANCE})")
            if best_val < TOLERANCE:
                res = {var: float(val) for var, val in zip(all_vars, best_res.x)}
                logger.info("[GeometryEngine] Strategy 3 (least-squares): SUCCESS.")
                return {pid: [float(res.get(vx, 0)), float(res.get(vy, 0)), float(res.get(vz, 0))]
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
                    except:
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
        segments_meta: List[List[str]],
        lines_meta: List[List[str]],
        rays_meta: List[List[str]],
        pt_list: List[Point],
    ) -> Dict[str, Any]:
        """
        Build structured result including drawing phases for the renderer.

        drawing_phases:
          Phase 1 — Base shape (main polygon)
          Phase 2 — Auxiliary/derived points and segments
        """
        all_ids = [p.id for p in pt_list]

        # 1. Infer/clean polygon_order
        if not polygon_order:
            # Fallback: use all declared point IDs sorted by conventional uppercase order.
            # This is far safer than only looking for A/B/C/D.
            base_pts = sorted(
                all_ids,
                key=lambda p: (string.ascii_uppercase.index(p) if p in string.ascii_uppercase else 100, p)
            )
            polygon_order = base_pts

        base_ids = [pid for pid in polygon_order if pid in all_ids]
        derived_ids = [pid for pid in all_ids if pid not in polygon_order]

        # 2. Collect unique segments to avoid redundancy (AB == BA)
        drawn_segments = set()

        def add_segment(p1, p2, target_list):
            if p1 == p2:
                return
            s = frozenset([p1, p2])
            if s not in drawn_segments:
                drawn_segments.add(s)
                target_list.append([p1, p2])

        # Phase 1: Main polygon boundary
        phase1_segments = []
        if len(base_ids) >= 2:
            # Connect in sequence: A-B, B-C, etc.
            for i in range(len(base_ids) - 1):
                add_segment(base_ids[i], base_ids[i+1], phase1_segments)
            
            # ONLY close the loop if we have 3 or more points (a real polygon)
            if len(base_ids) > 2:
                add_segment(base_ids[-1], base_ids[0], phase1_segments)

        # Phase 2: Auxiliary segments from DSL
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

        return {
            "coordinates": coords,
            "polygon_order": polygon_order,
            "circles": circles_meta,
            "lines": lines_meta,
            "rays": rays_meta,
            "drawing_phases": drawing_phases,
        }
