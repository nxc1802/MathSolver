import sympy as sp
import numpy as np
import logging
import string
from typing import List, Dict, Any
from .models import Point, Constraint

logger = logging.getLogger(__name__)


class GeometryEngine:
    def solve(self, points: List[Point], constraints: List[Constraint]) -> Dict[str, Any] | None:
        if not points:
            logger.error("[GeometryEngine] No points to solve.")
            return None

        logger.info(f"==[GeometryEngine] Starting solve with {len(points)} points, {len(constraints)} constraints==")

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
            else:
                real_constraints.append(c)

        # ── Setup symbols ─────────────────────────────────────────────────────
        point_vars: Dict[str, tuple] = {}
        equations = []

        for p in points:
            x = sp.Symbol(f"{p.id}_x")
            y = sp.Symbol(f"{p.id}_y")
            point_vars[p.id] = (x, y)
            logger.debug(f"[GeometryEngine]   Symbol: ({p.id}_x, {p.id}_y)")

        # ── Anchor first two points to fix translation + rotation DOF ─────────
        first_pt = points[0].id
        equations.append(point_vars[first_pt][0])   # A_x = 0
        equations.append(point_vars[first_pt][1])   # A_y = 0
        logger.debug(f"[GeometryEngine]   Anchor: {first_pt} = (0, 0)")

        if len(points) > 1:
            second_pt = points[1].id
            equations.append(point_vars[second_pt][1])  # B_y = 0
            logger.debug(f"[GeometryEngine]   Anchor: {second_pt}.y = 0 (on X-axis)")

        # ── Build equations from constraints ──────────────────────────────────
        for c in real_constraints:
            logger.debug(f"[GeometryEngine]   Processing constraint: type={c.type}, targets={c.targets}, value={c.value}")

            if c.type == 'length' and len(c.targets) == 2:
                p1, p2 = c.targets
                if p1 not in point_vars or p2 not in point_vars:
                    logger.warning(f"[GeometryEngine]   Skip length: {c.targets} not in symbols.")
                    continue
                v1, v2 = point_vars[p1], point_vars[p2]
                eq = (v2[0]-v1[0])**2 + (v2[1]-v1[1])**2 - float(c.value)**2
                equations.append(eq)
                logger.debug(f"[GeometryEngine]     -> Length eq: |{p1}{p2}|² = {c.value}²")

            elif c.type == 'angle' and len(c.targets) >= 1:
                if len(points) >= 3:
                    v_name = c.targets[0]
                    if v_name not in point_vars:
                        logger.warning(f"[GeometryEngine]   Skip angle: vertex {v_name} not in symbols.")
                        continue
                    other_pts = [p.id for p in points if p.id != v_name][:2]
                    if len(other_pts) < 2:
                        continue
                    pV = point_vars[v_name]
                    p1_vars = point_vars[other_pts[0]]
                    p2_vars = point_vars[other_pts[1]]
                    dx1, dy1 = p1_vars[0]-pV[0], p1_vars[1]-pV[1]
                    dx2, dy2 = p2_vars[0]-pV[0], p2_vars[1]-pV[1]
                    if abs(float(c.value) - 90.0) < 1e-9:
                        eq = dx1*dx2 + dy1*dy2
                        logger.debug(f"[GeometryEngine]     -> Angle eq at {v_name} (90° dot=0)")
                    else:
                        rad = sp.pi * float(c.value) / 180
                        eq = (dy2*dx1 - dy1*dx2) - sp.tan(rad)*(dx1*dx2 + dy1*dy2)
                        logger.debug(f"[GeometryEngine]     -> Angle eq at {v_name} ({c.value}°)")
                    equations.append(eq)

            elif c.type == 'parallel' and len(c.targets) == 4:
                pA, pB, pC, pD = c.targets
                if any(t not in point_vars for t in [pA, pB, pC, pD]):
                    logger.warning(f"[GeometryEngine]   Skip parallel: missing points in {c.targets}.")
                    continue
                va, vb, vc, vd = point_vars[pA], point_vars[pB], point_vars[pC], point_vars[pD]
                equations.append((vb[1]-va[1])*(vd[0]-vc[0]) - (vb[0]-va[0])*(vd[1]-vc[1]))
                logger.debug(f"[GeometryEngine]     -> Parallel eq: {pA}{pB} || {pC}{pD}")

            elif c.type == 'perpendicular' and len(c.targets) == 4:
                pA, pB, pC, pD = c.targets
                if any(t not in point_vars for t in [pA, pB, pC, pD]):
                    logger.warning(f"[GeometryEngine]   Skip perpendicular: missing points in {c.targets}.")
                    continue
                va, vb, vc, vd = point_vars[pA], point_vars[pB], point_vars[pC], point_vars[pD]
                equations.append((vb[0]-va[0])*(vd[0]-vc[0]) + (vb[1]-va[1])*(vd[1]-vc[1]))
                logger.debug(f"[GeometryEngine]     -> Perpendicular eq: {pA}{pB} ⊥ {pC}{pD}")

            elif c.type == 'midpoint' and len(c.targets) == 3:
                # MIDPOINT(M, A, B)  →  M = (A+B)/2
                pM, pA, pB = c.targets
                if any(t not in point_vars for t in [pM, pA, pB]):
                    logger.warning(f"[GeometryEngine]   Skip midpoint: missing points in {c.targets}.")
                    continue
                vM, vA, vB = point_vars[pM], point_vars[pA], point_vars[pB]
                equations.append(2*vM[0] - vA[0] - vB[0])  # 2*M_x = A_x + B_x
                equations.append(2*vM[1] - vA[1] - vB[1])  # 2*M_y = A_y + B_y
                logger.debug(f"[GeometryEngine]     -> Midpoint eq: {pM} = mid({pA},{pB})")

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
        if coords:
            return self._build_result(coords, polygon_order, circles_meta, segments_meta, points)

        # ── Strategy 2: Numerical nsolve ─────────────────────────────────────
        if n_eqs == n_vars:
            coords = self._try_nsolve(equations, all_vars, point_vars, n_vars)
            if coords:
                return self._build_result(coords, polygon_order, circles_meta, segments_meta, points)

        # ── Strategy 3: Scipy least-squares ─────────────────────────────────
        coords = self._try_lsq(equations, all_vars, point_vars, n_vars)
        if coords:
            return self._build_result(coords, polygon_order, circles_meta, segments_meta, points)

        # ── Strategy 4: Differential evolution ──────────────────────────────
        coords = self._try_global(equations, all_vars, point_vars, n_vars)
        if coords:
            return self._build_result(coords, polygon_order, circles_meta, segments_meta, points)

        logger.error("[GeometryEngine] All strategies exhausted.")
        return None

    # ─── Solving strategies ──────────────────────────────────────────────────

    def _try_symbolic(self, equations, all_vars, point_vars):
        try:
            solution = sp.solve(equations, all_vars, dict=True)
            if solution:
                res = solution[0]
                logger.info("[GeometryEngine] Strategy 1 (SymPy symbolic): SUCCESS.")
                logger.debug(f"[GeometryEngine] Symbolic solution: {res}")
                return {pid: [float(res.get(vx, 0)), float(res.get(vy, 0))]
                        for pid, (vx, vy) in point_vars.items()}
            else:
                logger.warning("[GeometryEngine] Strategy 1 returned no solution. Trying numerical...")
        except Exception as e:
            logger.warning(f"[GeometryEngine] Strategy 1 threw exception: {e}. Trying numerical...")
        return None

    def _try_nsolve(self, equations, all_vars, point_vars, n_vars):
        MAX_NSOLVE_ATTEMPTS = 10
        logger.info(f"[GeometryEngine] Strategy 2 (nsolve): square system ({n_vars}x{n_vars}). Trying {MAX_NSOLVE_ATTEMPTS} random starts...")
        for attempt in range(MAX_NSOLVE_ATTEMPTS):
            try:
                np.random.seed(attempt)
                guesses = [np.random.uniform(-10, 10) for _ in range(n_vars)]
                sol_vals = sp.nsolve(equations, all_vars, guesses, tol=1e-6, maxsteps=500)
                res = {var: float(val) for var, val in zip(all_vars, sol_vals)}
                logger.info(f"[GeometryEngine] Strategy 2 (nsolve): SUCCESS on attempt {attempt + 1}.")
                return {pid: [float(res.get(vx, 0)), float(res.get(vy, 0))]
                        for pid, (vx, vy) in point_vars.items()}
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
            for i in range(5):
                x0 = [np.random.uniform(-10, 10) for _ in range(n_vars)] if i > 0 else [1.0]*n_vars
                res = minimize(objective, x0, method='L-BFGS-B')
                if res.fun < best_val:
                    best_val, best_res = res.fun, res
                if best_val < 1e-4:
                    break

            TOLERANCE = 1e-4
            logger.info(f"[GeometryEngine] Strategy 3: best residual = {best_val:.2e} (tol={TOLERANCE})")
            if best_val < TOLERANCE:
                res = {var: float(val) for var, val in zip(all_vars, best_res.x)}
                logger.info("[GeometryEngine] Strategy 3 (least-squares): SUCCESS.")
                return {pid: [float(res.get(vx, 0)), float(res.get(vy, 0))]
                        for pid, (vx, vy) in point_vars.items()}
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

            result = differential_evolution(obj, bounds, maxiter=50, popsize=10, mutation=(0.5, 1), recombination=0.7)
            TOLERANCE = 1e-3
            logger.info(f"[GeometryEngine] Strategy 4: best residual = {result.fun:.2e} (tol={TOLERANCE})")
            if result.fun < TOLERANCE:
                res = {var: float(val) for var, val in zip(all_vars, result.x)}
                logger.info("[GeometryEngine] Strategy 4 (global opt): SUCCESS.")
                return {pid: [float(res.get(vx, 0)), float(res.get(vy, 0))]
                        for pid, (vx, vy) in point_vars.items()}
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
        points: List[Point],
    ) -> Dict[str, Any]:
        """
        Build structured result including drawing phases for the renderer.

        drawing_phases:
          Phase 1 — Base shape (main polygon)
          Phase 2 — Auxiliary/derived points and segments
        """
        all_ids = [p.id for p in points]

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
            "drawing_phases": drawing_phases,
        }
