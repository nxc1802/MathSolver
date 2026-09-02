"""Coordinate Solver: Numerical & symbolic coordinate solver for geometric equation systems."""

from __future__ import annotations

import logging
import numpy as np
import scipy.optimize
import sympy as sp
from typing import Any, Dict, List, Optional, Tuple
from .constraint_compiler import CompiledSystem

logger = logging.getLogger(__name__)


class CoordinateSolver:
    """Solves compiled equation systems for exact or optimized 2D/3D numerical coordinates."""

    def solve(self, system: CompiledSystem, is_3d: bool = False) -> Optional[Dict[str, List[float]]]:
        all_vars = []
        for v in system.point_vars.values():
            all_vars.extend(v)

        n_eqs = len(system.equations)
        n_vars = len(all_vars)
        logger.info(f"[CoordinateSolver] Solving {n_eqs} equations for {n_vars} unknowns (is_3d={is_3d}).")

        # Strategy 1: SymPy symbolic
        coords = self._try_symbolic(system.equations, all_vars, system.point_vars)
        if coords:
            return coords

        # Strategy 2: Numerical nsolve (for square systems)
        if n_eqs == n_vars:
            coords = self._try_nsolve(system.equations, all_vars, system.point_vars, n_vars, system.pt_list, is_3d)
            if coords:
                return coords

        # Strategy 3: Scipy least-squares optimization
        coords = self._try_lsq(system.equations, all_vars, system.point_vars, n_vars, system.pt_list, is_3d)
        if coords:
            return coords

        # Strategy 4: Global differential evolution optimization
        coords = self._try_global(system.equations, all_vars, system.point_vars, n_vars, is_3d)
        if coords:
            return coords

        logger.error("[CoordinateSolver] All solving strategies exhausted.")
        return None

    def _try_symbolic(
        self,
        equations: List[sp.Expr],
        all_vars: List[sp.Symbol],
        point_vars: Dict[str, Tuple[sp.Symbol, sp.Symbol, sp.Symbol]],
    ) -> Optional[Dict[str, List[float]]]:
        if len(all_vars) > 10 or len(equations) != len(all_vars):
            return None

        try:
            solution = sp.solve(equations, all_vars, dict=True)
            if solution:
                best_res = solution[0]
                for candidate in solution:
                    z_vals = [float(candidate.get(vz, 0.0)) for _, (_, _, vz) in point_vars.items()]
                    if all(z >= -1e-6 for z in z_vals):
                        best_res = candidate
                        break
                    elif any(z > 1e-6 for z in z_vals):
                        best_res = candidate

                logger.info("[CoordinateSolver] Strategy 1 (SymPy symbolic): SUCCESS.")
                return {
                    pid: [
                        float(best_res.get(vx, 0.0)),
                        float(best_res.get(vy, 0.0)),
                        abs(float(best_res.get(vz, 0.0))),
                    ]
                    for pid, (vx, vy, vz) in point_vars.items()
                }
        except Exception as e:
            logger.debug("[CoordinateSolver] Strategy 1 threw exception: %s", e)
        return None

    def _try_nsolve(
        self,
        equations: List[sp.Expr],
        all_vars: List[sp.Symbol],
        point_vars: Dict[str, Tuple[sp.Symbol, sp.Symbol, sp.Symbol]],
        n_vars: int,
        pt_list: list,
        is_3d: bool,
    ) -> Optional[Dict[str, List[float]]]:
        MAX_NSOLVE_ATTEMPTS = 15
        for attempt in range(MAX_NSOLVE_ATTEMPTS):
            try:
                x0 = []
                n_pts = len(pt_list)
                for i, p in enumerate(pt_list):
                    px = float(p.x) if p.x is not None else None
                    py = float(p.y) if p.y is not None else None
                    pz = float(p.z) if p.z is not None else None
                    if is_3d:
                        if px is not None and py is not None and pz is not None:
                            x0.extend([px, py, pz])
                        elif i == 0:
                            x0.extend([px if px is not None else 0.0, py if py is not None else 0.0, pz if pz is not None else 0.0])
                        elif i == n_pts - 1 and n_pts >= 4:
                            x0.extend([px if px is not None else 2.0, py if py is not None else 2.0, pz if pz is not None else 4.0])
                        else:
                            angle = 2 * np.pi * i / max(n_pts - 1, 1)
                            x0.extend([
                                px if px is not None else 3.0 * np.cos(angle),
                                py if py is not None else 3.0 * np.sin(angle),
                                pz if pz is not None else 0.0,
                            ])
                    else:
                        angle = 2 * np.pi * i / max(n_pts, 1)
                        r = 4.0 + (attempt * 0.5)
                        x0.extend([
                            px if px is not None else r * np.cos(angle),
                            py if py is not None else r * np.sin(angle),
                            0.0,
                        ])

                if attempt > 0:
                    perturbation = np.random.uniform(-1.0, 1.0, size=len(x0))
                    x0 = [float(v + p) for v, p in zip(x0, perturbation)]

                sol = sp.nsolve(equations, all_vars, x0, verify=False, maxsteps=100)
                if sol is not None:
                    res_map = {var: float(sol[i]) for i, var in enumerate(all_vars)}
                    logger.info(f"[CoordinateSolver] Strategy 2 (nsolve): SUCCESS on attempt {attempt+1}.")
                    return {
                        pid: [
                            float(res_map.get(vx, 0.0)),
                            float(res_map.get(vy, 0.0)),
                            abs(float(res_map.get(vz, 0.0))) if is_3d else 0.0,
                        ]
                        for pid, (vx, vy, vz) in point_vars.items()
                    }
            except Exception:
                pass
        return None

    def _try_lsq(
        self,
        equations: List[sp.Expr],
        all_vars: List[sp.Symbol],
        point_vars: Dict[str, Tuple[sp.Symbol, sp.Symbol, sp.Symbol]],
        n_vars: int,
        pt_list: list,
        is_3d: bool,
    ) -> Optional[Dict[str, List[float]]]:
        try:
            f_lambdified = sp.lambdify([all_vars], equations, modules=['numpy', 'scipy'])

            def residual(x):
                try:
                    res = f_lambdified(x)
                    return np.array(res, dtype=float).flatten()
                except Exception:
                    return np.full(len(equations), 1e6)

            n_pts = len(pt_list)
            x0_base = []
            for i, p in enumerate(pt_list):
                px = float(p.x) if p.x is not None else None
                py = float(p.y) if p.y is not None else None
                pz = float(p.z) if p.z is not None else None
                if is_3d:
                    if px is not None and py is not None and pz is not None:
                        x0_base.extend([px, py, pz])
                    elif i == 0:
                        x0_base.extend([px if px is not None else 0.0, py if py is not None else 0.0, pz if pz is not None else 0.0])
                    elif i == n_pts - 1 and n_pts >= 4:
                        x0_base.extend([px if px is not None else 2.0, py if py is not None else 2.0, pz if pz is not None else 4.0])
                    else:
                        angle = 2 * np.pi * i / max(n_pts - 1, 1)
                        x0_base.extend([
                            px if px is not None else 3.0 * np.cos(angle),
                            py if py is not None else 3.0 * np.sin(angle),
                            pz if pz is not None else 0.0,
                        ])
                else:
                    angle = 2 * np.pi * i / max(n_pts, 1)
                    x0_base.extend([
                        px if px is not None else 4.0 * np.cos(angle),
                        py if py is not None else 4.0 * np.sin(angle),
                        0.0,
                    ])


            best_res = None
            best_cost = float('inf')

            for attempt in range(8):
                if attempt == 0:
                    x0 = np.array(x0_base, dtype=float)
                else:
                    x0 = np.array(x0_base, dtype=float) + np.random.normal(0, 1.5, len(x0_base))

                res = scipy.optimize.least_squares(
                    residual,
                    x0,
                    method='lm' if len(equations) >= n_vars else 'trf',
                    max_nfev=3000,
                    ftol=1e-8,
                    xtol=1e-8,
                )

                cost = np.sum(res.fun**2)
                if cost < best_cost:
                    best_cost = cost
                    best_res = res

                if best_cost < 1e-4:
                    break

            if best_res is not None and best_cost < 1e-2:
                logger.info(f"[CoordinateSolver] Strategy 3 (least_squares): SUCCESS (cost={best_cost:.2e}).")
                sol = best_res.x
                res_map = {var: float(sol[i]) for i, var in enumerate(all_vars)}
                return {
                    pid: [
                        float(res_map.get(vx, 0.0)),
                        float(res_map.get(vy, 0.0)),
                        abs(float(res_map.get(vz, 0.0))) if is_3d else 0.0,
                    ]
                    for pid, (vx, vy, vz) in point_vars.items()
                }
        except Exception as e:
            logger.debug("[CoordinateSolver] Strategy 3 failed: %s", e)
        return None

    def _try_global(
        self,
        equations: List[sp.Expr],
        all_vars: List[sp.Symbol],
        point_vars: Dict[str, Tuple[sp.Symbol, sp.Symbol, sp.Symbol]],
        n_vars: int,
        is_3d: bool,
    ) -> Optional[Dict[str, List[float]]]:
        try:
            f_lambdified = sp.lambdify([all_vars], equations, modules=['numpy', 'scipy'])

            def loss(x):
                try:
                    res = f_lambdified(x)
                    arr = np.array(res, dtype=float).flatten()
                    return float(np.sum(arr**2))
                except Exception:
                    return 1e9

            bounds = [(-15.0, 15.0)] * n_vars
            res = scipy.optimize.differential_evolution(loss, bounds, maxiter=500, popsize=15, tol=1e-5)
            if res.fun < 1e-2:
                logger.info(f"[CoordinateSolver] Strategy 4 (diff evolution): SUCCESS (loss={res.fun:.2e}).")
                sol = res.x
                res_map = {var: float(sol[i]) for i, var in enumerate(all_vars)}
                return {
                    pid: [
                        float(res_map.get(vx, 0.0)),
                        float(res_map.get(vy, 0.0)),
                        abs(float(res_map.get(vz, 0.0))) if is_3d else 0.0,
                    ]
                    for pid, (vx, vy, vz) in point_vars.items()
                }
        except Exception as e:
            logger.debug("[CoordinateSolver] Strategy 4 failed: %s", e)
        return None
