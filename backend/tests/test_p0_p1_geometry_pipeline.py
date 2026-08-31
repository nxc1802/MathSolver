"""Tests for P0 (Semantic Constraints, Derived Constraint Compilation, Validation)
and P1 (Hierarchical Constructors, Canonical 2D/3D Placement, Explicit Coordinate Preservation).
"""
from __future__ import annotations

import math
import numpy as np
import pytest

from solver.dsl_parser import DSLParser
from solver.compiler import ConstraintCompiler
from solver.constructors import StandardGeometryConstructor
from solver.engine import GeometryEngine
from solver.validator import GeometryValidator, ValidationResult
from solver.models import Point, Constraint


# ============================================================================
# P0 TESTS: SEMANTIC AUDIT & DERIVED CONSTRAINT COMPILATION
# ============================================================================

def test_p0_height_derived_constraints():
    """
    HEIGHT(S, O, ABCD) must compile into:
    - O on plane(ABCD)
    - SO perp to plane(ABCD)
    - segment SO
    """
    dsl = """
    PYRAMID(S_ABCD)
    SQUARE(ABCD)
    LENGTH(AB, 6)
    HEIGHT(S, O, ABCD, 10)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)
    assert is_3d

    c_types = [c.type for c in constraints]
    assert "point_on_plane" in c_types
    assert "perp_plane" in c_types
    assert "length" in c_types

    # Ensure O and S were declared
    pt_ids = [p.id for p in points]
    assert "S" in pt_ids and "O" in pt_ids

    # Solve and validate
    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None
    coords = result["coordinates"]

    # Verify O is on z=0 and S is directly above O along +Z
    assert pytest.approx(coords["O"][2], abs=1e-3) == 0.0
    assert pytest.approx(coords["S"][0], abs=1e-3) == coords["O"][0]
    assert pytest.approx(coords["S"][1], abs=1e-3) == coords["O"][1]
    assert pytest.approx(coords["S"][2], abs=1e-3) == 10.0


def test_p0_foot_and_median_derived_constraints():
    """
    FOOT(H, P, AB) compiles to H on AB, PH perp AB.
    MEDIAN(A, M, BC) compiles to M midpoint of BC.
    """
    dsl = """
    TRIANGLE(ABC)
    POINT(A, 0, 4)
    POINT(B, -3, 0)
    POINT(C, 3, 0)
    FOOT(H, A, BC)
    MEDIAN(A, M, BC)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)

    c_types = [c.type for c in constraints]
    assert "point_on" in c_types
    assert "perpendicular" in c_types
    assert "midpoint" in c_types

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None
    coords = result["coordinates"]

    # In symmetric triangle with A(0,4), B(-3,0), C(3,0):
    # Foot H of A on BC is (0, 0)
    # Median M of BC is (0, 0)
    assert pytest.approx(coords["H"][:2], abs=1e-3) == [0.0, 0.0]
    assert pytest.approx(coords["M"][:2], abs=1e-3) == [0.0, 0.0]


def test_p0_square_and_rectangle_derived_properties():
    """
    SQUARE(ABCD) compiler expands into equal sides, perpendicular adjacent edges,
    and equal/orthogonal diagonals.
    """
    dsl = """
    SQUARE(ABCD)
    LENGTH(AB, 5)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)

    # Solve
    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None
    coords = result["coordinates"]

    # Verify sides
    vA = np.array(coords["A"][:2])
    vB = np.array(coords["B"][:2])
    vC = np.array(coords["C"][:2])
    vD = np.array(coords["D"][:2])

    assert pytest.approx(np.linalg.norm(vB - vA), rel=1e-3) == 5.0
    assert pytest.approx(np.linalg.norm(vC - vB), rel=1e-3) == 5.0
    assert pytest.approx(np.linalg.norm(vD - vC), rel=1e-3) == 5.0
    assert pytest.approx(np.linalg.norm(vA - vD), rel=1e-3) == 5.0

    # Diagonals equal and perpendicular
    diag1 = vC - vA
    diag2 = vD - vB
    assert pytest.approx(np.linalg.norm(diag1), rel=1e-3) == pytest.approx(np.linalg.norm(diag2), rel=1e-3)
    assert pytest.approx(np.dot(diag1, diag2), abs=1e-3) == 0.0


# ============================================================================
# P1 TESTS: CANONICAL GEOMETRY CONSTRUCTORS & PLACEMENT
# ============================================================================

def test_p1_canonical_pyramid_hierarchy():
    """
    Pyramid S.ABCD with square base AB=4, SO=8.
    Ensures hierarchical canonical construction:
    - Base ABCD on z=0
    - Center O at origin or (2, 2, 0)
    - Apex S directly above O along +Z
    - Scale strictly preserved (AB=4, SO=8)
    """
    dsl = """
    PYRAMID(S_ABCD)
    SQUARE(ABCD)
    LENGTH(AB, 4)
    CENTER(O, ABCD)
    HEIGHT(S, O, ABCD, 8)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)
    assert is_3d

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None
    coords = result["coordinates"]

    # All base points on z=0
    for p in ["A", "B", "C", "D", "O"]:
        assert pytest.approx(coords[p][2], abs=1e-3) == 0.0

    # Base side = 4
    vA = np.array(coords["A"])
    vB = np.array(coords["B"])
    assert pytest.approx(np.linalg.norm(vB - vA), rel=1e-3) == 4.0

    # Apex S is at (Ox, Oy, 8)
    vO = np.array(coords["O"])
    vS = np.array(coords["S"])
    assert pytest.approx(vS[0], abs=1e-3) == vO[0]
    assert pytest.approx(vS[1], abs=1e-3) == vO[1]
    assert pytest.approx(vS[2], abs=1e-3) == 8.0
    assert pytest.approx(np.linalg.norm(vS - vO), rel=1e-3) == 8.0


def test_p1_preserves_explicit_user_coordinates():
    """
    If explicit coordinates are provided, canonicalization must honor them
    without arbitrary rotation or relocation.
    """
    dsl = """
    POINT(A, 1, 2, 3)
    POINT(B, 5, 2, 3)
    POINT(C, 5, 6, 3)
    POINT(D)
    RECTANGLE(ABCD)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None
    coords = result["coordinates"]

    # Explicit coordinates MUST match exactly
    assert pytest.approx(coords["A"], abs=1e-3) == [1.0, 2.0, 3.0]
    assert pytest.approx(coords["B"], abs=1e-3) == [5.0, 2.0, 3.0]
    assert pytest.approx(coords["C"], abs=1e-3) == [5.0, 6.0, 3.0]
    # D must complete the rectangle at (1, 6, 3)
    assert pytest.approx(coords["D"], abs=1e-3) == [1.0, 6.0, 3.0]


def test_p1_canonical_prism_construction():
    """
    Prism ABC.DEF with equilateral base side 6, height 12.
    Base 1 on z=0, Base 2 on z=12.
    """
    dsl = """
    PRISM(ABC_DEF)
    EQUILATERAL_TRIANGLE(ABC, 6)
    LENGTH(AD, 12)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None
    coords = result["coordinates"]

    for p in ["A", "B", "C"]:
        assert pytest.approx(coords[p][2], abs=1e-3) == 0.0

    for p in ["D", "E", "F"]:
        assert pytest.approx(coords[p][2], abs=1e-3) == 12.0

    # Check lateral lengths
    assert pytest.approx(np.linalg.norm(np.array(coords["D"]) - np.array(coords["A"])), rel=1e-3) == 12.0
    assert pytest.approx(np.linalg.norm(np.array(coords["E"]) - np.array(coords["B"])), rel=1e-3) == 12.0
    assert pytest.approx(np.linalg.norm(np.array(coords["F"]) - np.array(coords["C"])), rel=1e-3) == 12.0
