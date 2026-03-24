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
                v1 = point_vars[p1]
                v2 = point_vars[p2]
                # Distance formula: (x2-x1)^2 + (y2-y1)^2 = d^2
                eq = (v2[0] - v1[0])**2 + (v2[1] - v1[1])**2 - c.value**2
                equations.append(eq)
            
            elif c.type == 'angle' and len(c.targets) == 1:
                # Basic angle constraint at Vertex A relative to AB line (assuming AB is on X-axis)
                # This is a simplified PoC version
                v_name = c.targets[0]
                if v_name == points[0].id and len(points) >= 3:
                    # Angle at vertex A for triangle ABC
                    # Vec AB = (Bx-Ax, By-Ay), Vec AC = (Cx-Ax, Cy-Ay)
                    # Use dot product: A.B = |A||B|Cos(theta)
                    pA = point_vars[points[0].id]
                    pB = point_vars[points[1].id]
                    pC = point_vars[points[2].id]
                    
                    vec1 = (pB[0] - pA[0], pB[1] - pA[1])
                    vec2 = (pC[0] - pA[0], pC[1] - pA[1])
                    
                    rad = sp.pi * c.value / 180
                    # Simplified: vec2_x = cos(rad)*|vec2|, vec2_y = sin(rad)*|vec2|
                    # But we don't know |vec2| length yet if not provided.
                    # If AC length is provided in another constraint, this works.
                    # For now, let's just use the slope if possible or basic trig.
                    tan_val = sp.tan(rad)
                    equations.append((pC[1] - pA[1]) - tan_val * (pC[0] - pA[0]))

        # Solve equations
        all_vars = []
        for v in point_vars.values():
            all_vars.extend(v)
            
        try:
            # Try exact symbolic solution first
            solution = sp.solve(equations, all_vars, dict=True)
            if not solution:
                # Provide initial guesses for nsolve
                guesses = [0] * len(all_vars)
                # Simple heuristic for guesses: Points are spread out
                for i in range(len(all_vars)):
                    if i % 2 == 0: guesses[i] = i # x
                    else: guesses[i] = 0 # y
                
                # nsolve for numerical approximation
                sol_vals = sp.nsolve(equations, all_vars, guesses)
                res = {var: float(val) for var, val in zip(all_vars, sol_vals)}
            else:
                res = solution[0]
        except Exception as e:
            print(f"Solver Error: {e}")
            return None

        output = {}
        for pid, (vx, vy) in point_vars.items():
            output[pid] = [float(res.get(vx, 0)), float(res.get(vy, 0))]
            
        return output
