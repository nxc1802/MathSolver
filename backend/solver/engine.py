import sympy as sp
import numpy as np
from typing import List, Dict
from .models import Point, Constraint

class GeometryEngine:
    def __init__(self):
        self.symbols = {}

    def solve(self, points: List[Point], constraints: List[Constraint]):
        # Setup symbols for each point's coordinates (x, y)
        point_vars = {}
        equations = []

        for p in points:
            x = sp.Symbol(f"{p.id}_x")
            y = sp.Symbol(f"{p.id}_y")
            point_vars[p.id] = (x, y)

        # Anchor first point at (0,0) to reduce degrees of freedom
        first_pt = points[0].id
        equations.append(point_vars[first_pt][0]) # x = 0
        equations.append(point_vars[first_pt][1]) # y = 0

        # Anchor second point on X-axis if a length constraint exists for it
        if len(points) > 1:
            second_pt = points[1].id
            # Optionally anchor to x-axis
            equations.append(point_vars[second_pt][1]) # y = 0

        for c in constraints:
            if c.type == 'length' and len(c.targets) == 2:
                p1, p2 = c.targets
                v1, v2 = point_vars[p1], point_vars[p2]
                equations.append((v2[0] - v1[0])**2 + (v2[1] - v1[1])**2 - c.value**2)
            
            elif c.type == 'angle' and len(c.targets) >= 1:
                # Assuming targets[0] is vertex, and we need 2 more points for vectors
                # If only 3 points are in the system, we assume they form the angle
                if len(points) >= 3:
                    v_name = c.targets[0]
                    other_pts = [p.id for p in points if p.id != v_name][:2]
                    pV, p1, p2 = point_vars[v_name], point_vars[other_pts[0]], point_vars[other_pts[1]]
                    
                    # Vec1 = p1 - pV, Vec2 = p2 - pV
                    dx1, dy1 = p1[0] - pV[0], p1[1] - pV[1]
                    dx2, dy2 = p2[0] - pV[0], p2[1] - pV[1]
                    
                    # Use tangent of angle: tan(theta) = |v1 x v2| / (v1 . v2)
                    # dy/dx relation (simpler for PoC): slope2 - slope1 relation
                    rad = sp.pi * c.value / 180
                    # tan(theta) = (m2 - m1) / (1 + m1*m2)
                    # (dy2/dx2 - dy1/dx1) = tan(rad) * (1 + (dy2/dx2)*(dy1/dx1))
                    # Multiply by dx1*dx2: (dy2*dx1 - dy1*dx2) = tan(rad) * (dx1*dx2 + dy1*dy2)
                    equations.append((dy2*dx1 - dy1*dx2) - sp.tan(rad) * (dx1*dx2 + dy1*dy2))

            elif c.type == 'parallel' and len(c.targets) == 4:
                # Targets: [A, B, C, D] -> line AB parallel to line CD
                pA, pB, pC, pD = [point_vars[t] for t in c.targets]
                # (By-Ay)*(Dx-Cx) - (Bx-Ax)*(Dy-Cy) = 0 (Cross product of direction vectors)
                equations.append((pB[1]-pA[1])*(pD[0]-pC[0]) - (pB[0]-pA[0])*(pD[1]-pC[1]))

            elif c.type == 'perpendicular' and len(c.targets) == 4:
                # Targets: [A, B, C, D] -> line AB perp to line CD
                pA, pB, pC, pD = [point_vars[t] for t in c.targets]
                # (Bx-Ax)*(Dx-Cx) + (By-Ay)*(Dy-Cy) = 0 (Dot product = 0)
                equations.append((pB[0]-pA[0])*(pD[0]-pC[0]) + (pB[1]-pA[1])*(pD[1]-pC[1]))

        # Solve equations
        all_vars = []
        for v in point_vars.values(): all_vars.extend(v)
            
        try:
            solution = sp.solve(equations, all_vars, dict=True)
            if not solution:
                guesses = [np.random.uniform(-5, 5) for _ in range(len(all_vars))]
                sol_vals = sp.nsolve(equations, all_vars, guesses)
                res = {var: float(val) for var, val in zip(all_vars, sol_vals)}
            else:
                res = solution[0]
        except Exception as e:
            print(f"Solver Error: {e}")
            return None

        return {pid: [float(res.get(vx, 0)), float(res.get(vy, 0))] for pid, (vx, vy) in point_vars.items()}
