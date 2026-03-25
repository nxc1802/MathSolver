import sympy as sp
import numpy as np
import logging
from typing import List, Dict
from .models import Point, Constraint

logger = logging.getLogger(__name__)

class GeometryEngine:
    def solve(self, points: List[Point], constraints: List[Constraint]) -> Dict | None:
        if not points:
            logger.error("[GeometryEngine] No points to solve.")
            return None

        logger.info(f"==[GeometryEngine] Starting solve with {len(points)} points, {len(constraints)} constraints==")

        # Setup symbols for each point's coordinates (x, y)
        point_vars = {}
        equations = []

        for p in points:
            x = sp.Symbol(f"{p.id}_x")
            y = sp.Symbol(f"{p.id}_y")
            point_vars[p.id] = (x, y)
            logger.debug(f"[GeometryEngine]   Symbol: ({p.id}_x, {p.id}_y)")

        # Anchor first point at origin (0,0) to fix translation DOF
        first_pt = points[0].id
        equations.append(point_vars[first_pt][0])  # x = 0
        equations.append(point_vars[first_pt][1])  # y = 0
        logger.debug(f"[GeometryEngine]   Anchor: {first_pt} = (0, 0)")

        # Anchor second point on X-axis to fix rotation DOF
        if len(points) > 1:
            second_pt = points[1].id
            equations.append(point_vars[second_pt][1])  # y = 0
            logger.debug(f"[GeometryEngine]   Anchor: {second_pt}.y = 0 (on X-axis)")

        for c in constraints:
            logger.debug(f"[GeometryEngine]   Processing constraint: type={c.type}, targets={c.targets}, value={c.value}")

            if c.type == 'length' and len(c.targets) == 2:
                p1, p2 = c.targets
                if p1 not in point_vars or p2 not in point_vars:
                    logger.warning(f"[GeometryEngine]   Skipping length constraint: point(s) {c.targets} not found in symbol table.")
                    continue
                v1, v2 = point_vars[p1], point_vars[p2]
                eq = (v2[0] - v1[0])**2 + (v2[1] - v1[1])**2 - c.value**2
                equations.append(eq)
                logger.debug(f"[GeometryEngine]     -> Length eq: |{p1}{p2}|² = {c.value}² added.")

            elif c.type == 'angle' and len(c.targets) >= 1:
                if len(points) >= 3:
                    v_name = c.targets[0]
                    if v_name not in point_vars:
                        logger.warning(f"[GeometryEngine]   Skipping angle constraint: vertex {v_name} not found.")
                        continue
                    other_pts = [p.id for p in points if p.id != v_name][:2]
                    if len(other_pts) < 2:
                        logger.warning(f"[GeometryEngine]   Skipping angle constraint: not enough other points to form angle at {v_name}.")
                        continue
                    pV = point_vars[v_name]
                    p1_vars = point_vars[other_pts[0]]
                    p2_vars = point_vars[other_pts[1]]

                    dx1, dy1 = p1_vars[0] - pV[0], p1_vars[1] - pV[1]
                    dx2, dy2 = p2_vars[0] - pV[0], p2_vars[1] - pV[1]

                    rad = sp.pi * c.value / 180
                    eq = (dy2*dx1 - dy1*dx2) - sp.tan(rad) * (dx1*dx2 + dy1*dy2)
                    equations.append(eq)
                    logger.debug(f"[GeometryEngine]     -> Angle eq at vertex {v_name} ({c.value}°) added.")

            elif c.type == 'parallel' and len(c.targets) == 4:
                pA, pB, pC, pD = c.targets
                if any(t not in point_vars for t in [pA, pB, pC, pD]):
                    logger.warning(f"[GeometryEngine]   Skipping parallel constraint: missing points in {c.targets}.")
                    continue
                va, vb, vc, vd = point_vars[pA], point_vars[pB], point_vars[pC], point_vars[pD]
                equations.append((vb[1]-va[1])*(vd[0]-vc[0]) - (vb[0]-va[0])*(vd[1]-vc[1]))
                logger.debug(f"[GeometryEngine]     -> Parallel eq: {pA}{pB} || {pC}{pD} added.")

            elif c.type == 'perpendicular' and len(c.targets) == 4:
                pA, pB, pC, pD = c.targets
                if any(t not in point_vars for t in [pA, pB, pC, pD]):
                    logger.warning(f"[GeometryEngine]   Skipping perpendicular constraint: missing points in {c.targets}.")
                    continue
                va, vb, vc, vd = point_vars[pA], point_vars[pB], point_vars[pC], point_vars[pD]
                equations.append((vb[0]-va[0])*(vd[0]-vc[0]) + (vb[1]-va[1])*(vd[1]-vc[1]))
                logger.debug(f"[GeometryEngine]     -> Perpendicular eq: {pA}{pB} ⊥ {pC}{pD} added.")

        all_vars = []
        for v in point_vars.values():
            all_vars.extend(v)

        logger.info(f"[GeometryEngine] Built {len(equations)} equations for {len(all_vars)} unknowns. Solving with SymPy...")

        # --- Strategy 1: Symbolic solve ---
        try:
            solution = sp.solve(equations, all_vars, dict=True)
            if solution:
                res = solution[0]
                logger.info("[GeometryEngine] SymPy symbolic solve: SUCCESS.")
                logger.debug(f"[GeometryEngine] Symbolic solution: {res}")
                return {pid: [float(res.get(vx, 0)), float(res.get(vy, 0))] for pid, (vx, vy) in point_vars.items()}
            else:
                logger.warning("[GeometryEngine] SymPy symbolic solve returned no solution. Falling back to numerical solver.")
        except Exception as e:
            logger.warning(f"[GeometryEngine] SymPy symbolic solve threw exception: {e}. Falling back to numerical solver.")

        # --- Strategy 2: Numerical nsolve with multiple starting points ---
        MAX_NSOLVE_ATTEMPTS = 10
        logger.info(f"[GeometryEngine] Attempting nsolve with up to {MAX_NSOLVE_ATTEMPTS} random starting points...")
        for attempt in range(MAX_NSOLVE_ATTEMPTS):
            try:
                np.random.seed(attempt)  # Reproducible seeds
                # Use a tighter range for initial guesses based on expected geometry scale
                guesses = [np.random.uniform(-10, 10) for _ in range(len(all_vars))]
                sol_vals = sp.nsolve(equations, all_vars, guesses, tol=1e-6, maxsteps=500)
                res = {var: float(val) for var, val in zip(all_vars, sol_vals)}
                logger.info(f"[GeometryEngine] nsolve SUCCESS on attempt {attempt + 1}.")
                logger.debug(f"[GeometryEngine] Numerical solution: {res}")
                return {pid: [float(res.get(vx, 0)), float(res.get(vy, 0))] for pid, (vx, vy) in point_vars.items()}
            except Exception as e:
                logger.debug(f"[GeometryEngine]   nsolve attempt {attempt + 1} failed: {e}")

        logger.error(f"[GeometryEngine] All {MAX_NSOLVE_ATTEMPTS} nsolve attempts failed. Could not find solution.")
        return None
