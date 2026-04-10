import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from solver.engine import GeometryEngine
from solver.models import Point, Constraint

def test_triangle_abc():
    engine = GeometryEngine()
    
    # Triangle ABC: AB=5, AC=7, angle A=60
    points = [
        Point(id="A"),
        Point(id="B"),
        Point(id="C")
    ]
    
    constraints = [
        Constraint(type="length", targets=["A", "B"], value=5.0),
        Constraint(type="length", targets=["A", "C"], value=7.0),
        Constraint(type="angle", targets=["A"], value=60.0) # Angle at A
    ]
    
    print("Solving for Triangle ABC (AB=5, AC=7, angle A=60)...")
    results = engine.solve(points, constraints)
    
    if results:
        coords = results["coordinates"]
        print("Success! Coordinates:")
        for pid, c in coords.items():
            print(f"Point {pid}: {c}")
            
        # Verify distance AB
        dist_ab = ((coords["B"][0] - coords["A"][0])**2 + (coords["B"][1] - coords["A"][1])**2)**0.5
        print(f"Verified AB distance: {dist_ab:.2f}")
        
        # Verify distance AC
        dist_ac = ((coords["C"][0] - coords["A"][0])**2 + (coords["C"][1] - coords["A"][1])**2)**0.5
        print(f"Verified AC distance: {dist_ac:.2f}")
    else:
        print("Solver failed.")

if __name__ == "__main__":
    test_triangle_abc()
