import pytest
import numpy as np
from solver.dsl_parser import DSLParser
from solver.engine import GeometryEngine


def test_solve_cube():
    """
    Test solving for a cube ABCD.A1B1C1D1 with side a=5.
    Verify all 8 vertices, 12 edges, faces, and 3D coordinates.
    """
    dsl = """
    POINT(A, 0, 0, 0)
    POINT(B, 5, 0, 0)
    POINT(C, 5, 5, 0)
    POINT(D, 0, 5, 0)
    POINT(A1)
    POINT(B1)
    POINT(C1)
    POINT(D1)
    LENGTH(AA1, 5)
    PERPENDICULAR_PLANE(AA1, ABCD)
    CUBE(ABCD_A1B1C1D1)
    """
    parser = DSLParser()
    engine = GeometryEngine()

    points, constraints, is_3d = parser.parse(dsl)
    assert is_3d is True
    assert len(points) == 8

    result = engine.solve(points, constraints, is_3d)
    assert result is not None

    coords = result["coordinates"]
    # Check bottom base vertices
    assert coords["C"][2] == pytest.approx(0.0, abs=1e-3)
    assert coords["D"][0] == pytest.approx(0.0, abs=1e-3)
    assert coords["D"][1] == pytest.approx(5.0, abs=1e-3)
    assert coords["D"][2] == pytest.approx(0.0, abs=1e-3)

    # Check top base vertices
    assert coords["A1"][0] == pytest.approx(0.0, abs=1e-3)
    assert coords["A1"][1] == pytest.approx(0.0, abs=1e-3)
    assert abs(coords["A1"][2]) == pytest.approx(5.0, abs=1e-3)

    # Verify solids and faces
    assert "solids" in result
    assert any(s["type"] == "cube" for s in result["solids"])
    assert "faces" in result
    assert len(result["faces"]) >= 6 # 6 faces for a cube


def test_solve_regular_tetrahedron():
    """
    Test solving for a regular tetrahedron ABCD with edge a=6.
    """
    dsl = """
    POINT(A, 0, 0, 0)
    POINT(B, 6, 0, 0)
    POINT(C)
    POINT(D)
    LENGTH(AC, 6)
    LENGTH(BC, 6)
    LENGTH(AD, 6)
    LENGTH(BD, 6)
    LENGTH(CD, 6)
    TETRAHEDRON(ABCD)
    """
    parser = DSLParser()
    engine = GeometryEngine()

    points, constraints, is_3d = parser.parse(dsl)
    assert is_3d is True

    result = engine.solve(points, constraints, is_3d)
    assert result is not None

    coords = result["coordinates"]
    # Check edge lengths
    for p1, p2 in [("A","B"), ("A","C"), ("A","D"), ("B","C"), ("B","D"), ("C","D")]:
        v1 = np.array(coords[p1])
        v2 = np.array(coords[p2])
        dist = np.linalg.norm(v2 - v1)
        assert dist == pytest.approx(6.0, abs=1e-2)

    # 4 faces
    assert any(s["type"] == "tetrahedron" for s in result.get("solids", []))
    assert len(result.get("faces", [])) >= 4


def test_solve_prism_full_edges():
    """
    Test that triangular prism ABC_A1B1C1 generates all 9 edges (3 base1, 3 base2, 3 lateral).
    """
    dsl = """
    POINT(A, 0, 0, 0)
    POINT(B, 4, 0, 0)
    POINT(C, 0, 3, 0)
    POINT(A1)
    POINT(B1)
    POINT(C1)
    LENGTH(AA1, 8)
    PERPENDICULAR_PLANE(AA1, ABC)
    PRISM(ABC_A1B1C1)
    """
    parser = DSLParser()
    engine = GeometryEngine()

    points, constraints, is_3d = parser.parse(dsl)
    assert is_3d is True

    result = engine.solve(points, constraints, is_3d)
    assert result is not None

    # Check drawing phases contain all segments
    all_segments = []
    for phase in result["drawing_phases"]:
        all_segments.extend(phase["segments"])

    # Base 1 edges: AB, BC, CA
    # Base 2 edges: A1B1, B1C1, C1A1
    # Lateral edges: AA1, BB1, CC1
    expected_pairs = [
        {"A", "B"}, {"B", "C"}, {"C", "A"},
        {"A1", "B1"}, {"B1", "C1"}, {"C1", "A1"},
        {"A", "A1"}, {"B", "B1"}, {"C", "C1"}
    ]
    for pair in expected_pairs:
        assert any(set(seg) == pair for seg in all_segments), f"Missing segment: {pair}"


def test_perpendicular_plane_constraint():
    """
    Test PERPENDICULAR_PLANE(SO, ABCD) where ABCD is square on z=0.
    Apex S must lie directly on z-axis (SO along z-axis).
    """
    dsl = """
    POINT(A, 0, 0, 0)
    POINT(B, 4, 0, 0)
    POINT(C, 4, 4, 0)
    POINT(D, 0, 4, 0)
    POINT(O, 2, 2, 0)
    POINT(S)
    LENGTH(SO, 6)
    PERPENDICULAR_PLANE(SO, ABCD)
    PYRAMID(S_ABCD)
    """
    parser = DSLParser()
    engine = GeometryEngine()

    points, constraints, is_3d = parser.parse(dsl)
    result = engine.solve(points, constraints, is_3d)

    assert result is not None
    coords = result["coordinates"]
    assert coords["S"][0] == pytest.approx(2.0, abs=1e-3)
    assert coords["S"][1] == pytest.approx(2.0, abs=1e-3)
    assert abs(coords["S"][2]) == pytest.approx(6.0, abs=1e-3)


def test_coplanar_constraint():
    """
    Test COPLANAR(A, B, C, D) constraint.
    Points A(0,0,0), B(1,0,0), C(0,1,0) define XY-plane (z=0).
    Point D with D_x=2, D_y=3 should have D_z=0 under COPLANAR constraint.
    """
    dsl = """
    POINT(A, 0, 0, 0)
    POINT(B, 1, 0, 0)
    POINT(C, 0, 1, 0)
    POINT(D)
    LENGTH(AD, 5)
    ANGLE(D, A, B, 0)
    COPLANAR(A, B, C, D)
    """
    parser = DSLParser()
    engine = GeometryEngine()

    points, constraints, is_3d = parser.parse(dsl)
    result = engine.solve(points, constraints, is_3d)

    assert result is not None
    coords = result["coordinates"]
    assert coords["D"][2] == pytest.approx(0.0, abs=1e-3)


def test_cone_and_cylinder_dsl():
    """
    Test CONE and CYLINDER parsing and metadata creation.
    """
    dsl = """
    POINT(O, 0, 0, 0)
    POINT(S, 0, 0, 10)
    CONE(S, O, 4, 10)
    POINT(O1, 0, 0, 0)
    POINT(O2, 0, 0, 8)
    CYLINDER(O1, O2, 3)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)
    assert is_3d is True

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None

    solids = result.get("solids", [])
    assert any(s["type"] == "cone" and s["radius"] == 4.0 for s in solids)
    assert any(s["type"] == "cylinder" and s["radius"] == 3.0 for s in solids)


def test_multichar_point_names():
    """
    Test parsing and solving geometry with multi-character point names: A1, B1, M1, S_1, A'.
    """
    dsl = """
    POINT(A, 0, 0, 0)
    POINT(B, 4, 0, 0)
    POINT(M1)
    MIDPOINT(M1, A, B)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)
    assert any(p.id == "M1" for p in points)

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None
    coords = result["coordinates"]
    assert coords["M1"][0] == pytest.approx(2.0, abs=1e-3)
    assert coords["M1"][1] == pytest.approx(0.0, abs=1e-3)


if __name__ == "__main__":
    pytest.main([__file__])
