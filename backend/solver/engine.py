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

                    if abs(c.value - 90.0) < 1e-9:
                        # Special case: 90° angle → perpendicular vectors → dot product = 0
                        eq = dx1 * dx2 + dy1 * dy2
                        logger.debug(f"[GeometryEngine]     -> Angle eq at vertex {v_name} (90° → dot product = 0) added.")
                    else:
                        rad = sp.pi * c.value / 180
                        # cross = tan(θ) * dot  →  cross - tan(θ)*dot = 0
                        eq = (dy2*dx1 - dy1*dx2) - sp.tan(rad) * (dx1*dx2 + dy1*dy2)
                        logger.debug(f"[GeometryEngine]     -> Angle eq at vertex {v_name} ({c.value}°) added.")
                    equations.append(eq)


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

        n_eqs = len(equations)
        n_vars = len(all_vars)
        logger.info(f"[GeometryEngine] Built {n_eqs} equations for {n_vars} unknowns.")

        # --- Strategy 1: Symbolic solve (works best for well-determined systems) ---
        try:
            solution = sp.solve(equations, all_vars, dict=True)
            if solution:
                res = solution[0]
                logger.info("[GeometryEngine] Strategy 1 (SymPy symbolic): SUCCESS.")
                logger.debug(f"[GeometryEngine] Symbolic solution: {res}")
                return {pid: [float(res.get(vx, 0)), float(res.get(vy, 0))] for pid, (vx, vy) in point_vars.items()}
            else:
                logger.warning("[GeometryEngine] Strategy 1 returned no solution. Trying numerical...")
        except Exception as e:
            logger.warning(f"[GeometryEngine] Strategy 1 threw exception: {e}. Trying numerical...")

        # --- Strategy 2: Numerical nsolve (works for square systems) ---
        # Only works when n_eqs == n_vars
        MAX_NSOLVE_ATTEMPTS = 10
        if n_eqs == n_vars:
            logger.info(f"[GeometryEngine] Strategy 2 (nsolve): system is square ({n_eqs}x{n_vars}). Trying {MAX_NSOLVE_ATTEMPTS} random starts...")
            for attempt in range(MAX_NSOLVE_ATTEMPTS):
                try:
                    np.random.seed(attempt)
                    guesses = [np.random.uniform(-10, 10) for _ in range(n_vars)]
                    sol_vals = sp.nsolve(equations, all_vars, guesses, tol=1e-6, maxsteps=500)
                    res = {var: float(val) for var, val in zip(all_vars, sol_vals)}
                    logger.info(f"[GeometryEngine] Strategy 2 (nsolve): SUCCESS on attempt {attempt + 1}.")
                    return {pid: [float(res.get(vx, 0)), float(res.get(vy, 0))] for pid, (vx, vy) in point_vars.items()}
                except Exception as e:
                    logger.debug(f"[GeometryEngine]   nsolve attempt {attempt + 1} failed: {e}")
        else:
            logger.warning(f"[GeometryEngine] Strategy 2 (nsolve) skipped: over/under-determined ({n_eqs} eqs, {n_vars} vars).")

        # --- Strategy 3: Least-squares (handles over-determined & redundant systems) ---
        logger.info(f"[GeometryEngine] Strategy 3 (scipy least-squares): minimizing sum of squared residuals...")
        try:
            from scipy.optimize import minimize

            # Lambdify all equations for fast evaluation
            eq_funcs = [sp.lambdify(all_vars, eq, 'numpy') for eq in equations]

            def objective(x):
                return sum(float(f(*x))**2 for f in eq_funcs)

            best_res = None
            best_val = float('inf')
            
            # Multi-start to avoid local minima
            for i in range(5):
                x0 = [np.random.uniform(-10, 10) for _ in range(n_vars)] if i > 0 else [1.0]*n_vars
                res = minimize(objective, x0, method='L-BFGS-B')
                if res.fun < best_val:
                    best_val = res.fun
                    best_res = res
                if best_val < 1e-4: break # Early exit if a good solution is found
            
            TOLERANCE_LSQ = 1e-4 # More lenient for over-determined systems
            logger.info(f"[GeometryEngine] Strategy 3: best residual sum = {best_val:.2e} (tolerance={TOLERANCE_LSQ})")
            if best_val < TOLERANCE_LSQ:
                res = {var: float(val) for var, val in zip(all_vars, best_res.x)}
                logger.info("[GeometryEngine] Strategy 3 (least-squares): SUCCESS.")
                return {pid: [float(res.get(vx, 0)), float(res.get(vy, 0))] for pid, (vx, vy) in point_vars.items()}
            else:
                logger.warning(f"[GeometryEngine] Strategy 3 failed: residual {best_val:.2e} > tolerance {TOLERANCE_LSQ}. Trying Strategy 4...")
        except Exception as e:
            logger.error(f"[GeometryEngine] Strategy 3 threw exception: {e}")

        # --- Strategy 4: Global Optimization (Differential Evolution) ---
        logger.info("[GeometryEngine] Strategy 4 (Global Opt / Differential Evolution): exploring domain...")
        try:
            from scipy.optimize import differential_evolution
            
            # Use a slightly wider bound for global search
            bounds = [(-20, 20)] * n_vars
            
            # Update residuals_sq to be robust
            eq_funcs = [sp.lambdify(all_vars, eq, 'numpy') for eq in equations]
            def obj(x):
                s = 0.0
                for f in eq_funcs:
                    try:
                        val = float(f(*x))
                        s += val**2
                    except:
                        s += 1e6
                return s

            result = differential_evolution(obj, bounds, maxiter=50, popsize=10, mutation=(0.5, 1), recombination=0.7)
            
            TOLERANCE_GLOBAL = 1e-3
            logger.info(f"[GeometryEngine] Strategy 4: best residual sum = {result.fun:.2e} (tolerance={TOLERANCE_GLOBAL})")
            if result.fun < TOLERANCE_GLOBAL:
                res = {var: float(val) for var, val in zip(all_vars, result.x)}
                logger.info("[GeometryEngine] Strategy 4 (global opt): SUCCESS.")
                return {pid: [float(res.get(vx, 0)), float(res.get(vy, 0))] for pid, (vx, vy) in point_vars.items()}
        except Exception as e:
            logger.error(f"[GeometryEngine] Strategy 4 threw exception: {e}")

        logger.error("[GeometryEngine] All strategies exhausted. Could not find a valid solution.")
        return None


