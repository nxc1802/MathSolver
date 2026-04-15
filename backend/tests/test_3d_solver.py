import pytest
from solver.dsl_parser import DSLParser
from solver.engine import GeometryEngine
from solver.models import Point, Constraint

def test_solve_square_pyramid():
    """
    Test solving for a square pyramid S.ABCD.
    Base ABCD is a square with side 10.
    Height SO = 15, where O is the center of ABCD.
    """
    dsl = """
    POINT(A, 0, 0, 0)
    POINT(B, 10, 0, 0)
    POINT(C, 10, 10, 0)
    POINT(D, 0, 10, 0)
    POINT(S)
    POINT(O)
    MIDPOINT(M1, AB)
    MIDPOINT(M2, AC)
    SECTION(O, A, C, 0.5)
    LENGTH(SO, 15)
    PERPENDICULAR(SO, AC)
    PERPENDICULAR(SO, AB)
    PYRAMID(S_ABCD)
    """
    parser = DSLParser()
    engine = GeometryEngine()
    
    points, constraints, is_3d = parser.parse(dsl)
    result = engine.solve(points, constraints, is_3d)
    
    assert result is not None
    coords = result["coordinates"]
    
    # Check base points
    assert coords["A"] == [0.0, 0.0, 0.0]
    assert coords["B"] == [10.0, 0.0, 0.0]
    assert coords["C"] == [10.0, 10.0, 0.0]
    assert coords["D"] == [0.0, 10.0, 0.0]
    
    # Check center O (should be (5, 5, 0))
    assert coords["O"][0] == pytest.approx(5.0)
    assert coords["O"][1] == pytest.approx(5.0)
    assert coords["O"][2] == pytest.approx(0.0)
    
    # Check apex S (should be (5, 5, 15) or (5, 5, -15))
    assert coords["S"][0] == pytest.approx(5.0)
    assert coords["S"][1] == pytest.approx(5.0)
    assert abs(coords["S"][2]) == pytest.approx(15.0)

def test_solve_prism():
    """
    Triangular prism ABC_DEF.
    Base ABC is right triangle at A. AB=3, AC=4.
    Height AD=10.
    """
    dsl = """
    POINT(A, 0, 0, 0)
    POINT(B, 3, 0, 0)
    POINT(C, 0, 4, 0)
    POINT(D)
    POINT(E)
    POINT(F)
    LENGTH(AD, 10)
    PERPENDICULAR(AD, AB)
    PERPENDICULAR(AD, AC)
    PRISM(ABC_DEF)
    """
    parser = DSLParser()
    engine = GeometryEngine()
    
    points, constraints, is_3d = parser.parse(dsl)
    result = engine.solve(points, constraints, is_3d)
    
    assert result is not None
    coords = result["coordinates"]
    
    # D should be (0, 0, 10)
    assert coords["D"][0] == pytest.approx(0.0, abs=1e-3)
    assert coords["D"][1] == pytest.approx(0.0, abs=1e-3)
    assert abs(coords["D"][2]) == pytest.approx(10.0, rel=1e-4, abs=1e-3)

if __name__ == "__main__":
    pytest.main([__file__])
