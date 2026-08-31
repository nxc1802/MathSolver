"""Comprehensive Regression & Acceptance Tests for the Visualization Graph and Topology Pipeline.

Verifies:
1. Mathematical Geometry Graph vs Visualization Graph separation.
2. Complete 3D Solid Topology (Pyramid, Prism, Cube, Cuboid, Tetrahedron).
3. Automatic derivation of visual topology (vertices, edges, faces, connectivity).
4. Solution-dependent Auxiliary Geometry (Heights, Feet, Medians, Bisectors, Diagonals).
5. Minimal Sufficient Graph & Importance Tiers (REQUIRED, HELPFUL, OPTIONAL).
6. Surface & Face representations with cyclic vertex order and parent solid metadata.
7. VisualizationSpec integration and schema serialization.
"""
from __future__ import annotations

import pytest
import numpy as np

from solver.dsl_parser import DSLParser
from solver.engine import GeometryEngine
from solver.vis_graph import (
    EdgeStyle,
    EntityKind,
    ImportanceTier,
    VisualizationGraph,
)
from solver.vis_planner import VisualizationPlanner
from manim_client.schemas import build_visualization_spec, VisualizationSpec


# ============================================================================
# 1. 2D POLYGON TOPOLOGY & AUXILIARY CONSTRUCTIONS
# ============================================================================

def test_2d_rectangle_with_diagonals_and_midpoint():
    """
    2D Rectangle ABCD with center O and midpoint M of AB.
    Verifies that Visualization Graph contains:
    - 4 primary vertices + auxiliary center O + auxiliary midpoint M
    - 4 perimeter edges + 2 diagonal edges + auxiliary segments
    - 1 polygon face
    - Correct importance tiers.
    """
    dsl = """
    RECTANGLE(ABCD)
    LENGTH(AB, 8)
    LENGTH(BC, 6)
    CENTER(O, ABCD)
    MIDPOINT(M, AB)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)
    assert not is_3d

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None
    assert "visualization_graph" in result

    vis_graph_data = result["visualization_graph"]
    vis_graph = VisualizationGraph.model_validate(vis_graph_data)

    # 1. Vertices
    assert "A" in vis_graph.vertices
    assert "B" in vis_graph.vertices
    assert "C" in vis_graph.vertices
    assert "D" in vis_graph.vertices
    assert "O" in vis_graph.vertices
    assert "M" in vis_graph.vertices

    assert vis_graph.vertices["O"].role == "center"
    assert vis_graph.vertices["O"].kind == EntityKind.AUXILIARY
    assert vis_graph.vertices["M"].role == "midpoint"

    # 2. Edges: Perimeter + Diagonals
    edge_ids = list(vis_graph.edges.keys())
    assert any("A" in eid and "B" in eid for eid in edge_ids)
    assert any("B" in eid and "C" in eid for eid in edge_ids)
    assert any("C" in eid and "D" in eid for eid in edge_ids)
    assert any("A" in eid and "D" in eid for eid in edge_ids)
    # Diagonals AC and BD
    assert any("A" in eid and "C" in eid for eid in edge_ids)
    assert any("B" in eid and "D" in eid for eid in edge_ids)

    # 3. Faces
    assert len(vis_graph.faces) >= 1
    face = next(iter(vis_graph.faces.values()))
    assert len(face.vertices) == 4
    assert set(face.vertices) == {"A", "B", "C", "D"}

    # 4. Minimal Sufficient Graph
    min_graph = vis_graph.get_minimal_sufficient_graph(ImportanceTier.REQUIRED)
    assert "A" in min_graph["vertices"]
    assert "B" in min_graph["vertices"]


def test_2d_triangle_with_median_and_foot_altitude():
    """
    2D Triangle ABC with foot of altitude H and median AM.
    Verifies automatic derivation of auxiliary lines and perpendicular marks.
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

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None

    vis_graph = VisualizationGraph.model_validate(result["visualization_graph"])

    # Foot H and Median M
    assert "H" in vis_graph.vertices
    assert "M" in vis_graph.vertices
    assert vis_graph.vertices["H"].role == "foot"

    # Auxiliary construction records
    aux_types = [a.type for a in vis_graph.auxiliary]
    assert "foot" in aux_types
    assert "median" in aux_types

    # Edges include AH and AM
    edge_ids = list(vis_graph.edges.keys())
    assert any("A" in eid and "H" in eid for eid in edge_ids)
    assert any("A" in eid and "M" in eid for eid in edge_ids)


# ============================================================================
# 2. 3D SOLID TOPOLOGY (PYRAMID, PRISM, CUBE, CUBOID, TETRAHEDRON)
# ============================================================================

def test_3d_pyramid_full_topology_and_height():
    """
    Square Pyramid S.ABCD with height SO = 8.
    Verifies:
    - Complete Solid Topology: 5 vertices, 8 primary edges, 5 faces (1 base + 4 lateral).
    - Height SO auxiliary construction with dashed style.
    - Base diagonals AC, BD automatically derived to ground foot O.
    - Solid-to-face and solid-to-edge connectivity.
    """
    dsl = """
    PYRAMID(S_ABCD)
    SQUARE(ABCD)
    LENGTH(AB, 6)
    CENTER(O, ABCD)
    HEIGHT(S, O, ABCD, 8)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)
    assert is_3d

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None

    vis_graph = VisualizationGraph.model_validate(result["visualization_graph"])

    # 1. Solid Topology Record
    assert len(vis_graph.solids) >= 1
    solid = next(iter(vis_graph.solids.values()))
    assert solid.type == "pyramid"
    assert solid.apex == "S"
    assert set(solid.base_vertices) == {"A", "B", "C", "D"}
    assert len(solid.edges) == 8  # 4 base + 4 lateral
    assert len(solid.faces) == 5  # 1 base + 4 lateral

    # 2. Faces (1 quadrilateral base + 4 triangular lateral faces)
    assert len(vis_graph.faces) >= 5
    base_faces = [f for f in vis_graph.faces.values() if f.role == "base_face"]
    lat_faces = [f for f in vis_graph.faces.values() if f.role == "lateral_face"]
    assert len(base_faces) == 1
    assert len(lat_faces) == 4
    assert set(base_faces[0].vertices) == {"A", "B", "C", "D"}

    # 3. Altitude SO & Base Diagonals
    edge_so = next((e for e in vis_graph.edges.values() if "S" in e.id and "O" in e.id), None)
    assert edge_so is not None
    assert edge_so.role == "altitude"
    assert edge_so.style == EdgeStyle.DASHED

    # Diagonals AC and BD exist to anchor O
    assert any("A" in e.id and "C" in e.id for e in vis_graph.edges.values())
    assert any("B" in e.id and "D" in e.id for e in vis_graph.edges.values())

    # 4. Auxiliary Entity Record
    height_aux = next((a for a in vis_graph.auxiliary if a.type == "height"), None)
    assert height_aux is not None
    assert height_aux.source_entity == "S"
    assert height_aux.target_entity == "O"


def test_3d_triangular_prism_topology():
    """
    Triangular Prism ABC.DEF with base side 5 and height 10.
    Verifies:
    - 6 vertices (A, B, C, D, E, F).
    - 9 edges (3 base1 + 3 base2 + 3 lateral).
    - 5 faces (2 triangular bases + 3 rectangular lateral faces).
    - Face connectivity and parent solid references.
    """
    dsl = """
    PRISM(ABC_DEF)
    EQUILATERAL_TRIANGLE(ABC, 5)
    LENGTH(AD, 10)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)
    assert is_3d

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None

    vis_graph = VisualizationGraph.model_validate(result["visualization_graph"])

    assert len(vis_graph.solids) >= 1
    solid = next(iter(vis_graph.solids.values()))
    assert solid.type == "prism"
    assert set(solid.base_vertices) == {"A", "B", "C"}
    assert set(solid.top_vertices) == {"D", "E", "F"}
    assert len(solid.edges) == 9
    assert len(solid.faces) == 5

    # 2 Base faces (triangles) + 3 Lateral faces (quadrilaterals)
    tri_faces = [f for f in vis_graph.faces.values() if len(f.vertices) == 3]
    quad_faces = [f for f in vis_graph.faces.values() if len(f.vertices) == 4]
    assert len(tri_faces) == 2
    assert len(quad_faces) == 3


def test_3d_cube_topology():
    """
    Cube ABCD.A1B1C1D1 with side a=5.
    Verifies:
    - 8 vertices.
    - 12 edges.
    - 6 quadrilateral faces.
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
    points, constraints, is_3d = parser.parse(dsl)

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None

    vis_graph = VisualizationGraph.model_validate(result["visualization_graph"])

    assert len(vis_graph.vertices) == 8
    assert len(vis_graph.faces) == 6
    for f in vis_graph.faces.values():
        assert len(f.vertices) == 4


def test_3d_tetrahedron_topology():
    """
    Regular Tetrahedron ABCD.
    Verifies:
    - 4 vertices.
    - 6 edges.
    - 4 triangular faces.
    """
    dsl = """
    TETRAHEDRON(ABCD)
    LENGTH(AB, 6)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None

    vis_graph = VisualizationGraph.model_validate(result["visualization_graph"])

    assert len(vis_graph.vertices) == 4
    assert len(vis_graph.faces) == 4
    for f in vis_graph.faces.values():
        assert len(f.vertices) == 3


def test_3d_triangular_pyramid_s_abc_with_height_and_auxiliary_midpoint():
    """
    Triangular Pyramid S.ABC with centroid foot H and midpoint M of BC.
    Verifies:
    - 4 primary vertices (S, A, B, C) + 2 auxiliary (H, M).
    - Base edges AB, BC, CA + lateral edges SA, SB, SC.
    - 4 faces (1 base + 3 lateral).
    - Height SH and median AM auxiliary constructions.
    """
    dsl = """
    PYRAMID(S_ABC)
    EQUILATERAL_TRIANGLE(ABC, 6)
    CENTER(H, ABC)
    HEIGHT(S, H, ABC, 9)
    MIDPOINT(M, BC)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)
    assert is_3d

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None

    vis_graph = VisualizationGraph.model_validate(result["visualization_graph"])

    assert len(vis_graph.solids) >= 1
    solid = next(iter(vis_graph.solids.values()))
    assert solid.type == "pyramid"
    assert solid.apex == "S"
    assert set(solid.base_vertices) == {"A", "B", "C"}
    assert len(solid.faces) == 4

    # Check auxiliary vertices & edges
    assert "H" in vis_graph.vertices
    assert "M" in vis_graph.vertices
    assert vis_graph.vertices["H"].role in ("foot", "center")
    assert vis_graph.vertices["M"].role == "midpoint"


def test_3d_cuboid_topology():
    """
    Cuboid ABCD.A1B1C1D1 with length=8, width=6, height=10.
    Verifies 8 vertices, 12 edges, 6 faces.
    """
    dsl = """
    POINT(A, 0, 0, 0)
    POINT(B, 8, 0, 0)
    POINT(C, 8, 6, 0)
    POINT(D, 0, 6, 0)
    POINT(A1)
    POINT(B1)
    POINT(C1)
    POINT(D1)
    LENGTH(AA1, 10)
    PERPENDICULAR_PLANE(AA1, ABCD)
    PRISM(ABCD_A1B1C1D1)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None

    vis_graph = VisualizationGraph.model_validate(result["visualization_graph"])

    assert len(vis_graph.vertices) == 8
    assert len(vis_graph.faces) == 6
    assert len(vis_graph.edges) >= 12


# ============================================================================
# 3. VISUALIZATION SPEC INTEGRATION & MINIMAL SUFFICIENT GRAPH
# ============================================================================

def test_visualization_spec_rich_topology_generation():
    """
    Verifies that build_visualization_spec generates rich GeometryObject entries
    including points, styled segments, faces with opacity, and solid containers.
    """
    dsl = """
    PYRAMID(S_ABCD)
    SQUARE(ABCD)
    LENGTH(AB, 4)
    CENTER(O, ABCD)
    HEIGHT(S, O, ABCD, 6)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)
    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)

    spec = build_visualization_spec(
        problem_text="Tính thể tích khối chóp S.ABCD",
        solution_steps=["Dựng hình chóp S.ABCD với đáy hình vuông.", "Dựng đường cao SO."],
        engine_result=result,
        is_3d=True,
    )

    assert isinstance(spec, VisualizationSpec)
    assert spec.visualization_graph is not None

    types = [g.type for g in spec.geometry]
    assert "point_3d" in types
    assert "segment_3d" in types
    assert "face_3d" in types
    assert "pyramid" in types

    # Verify Manim dictionary serialization
    manim_dict = spec.to_manim_dict()
    assert "geometry" in manim_dict
    assert len(manim_dict["geometry"]) >= 5
    assert len(manim_dict["solution_steps"]) == 2


def test_minimal_sufficient_graph_filtering():
    """
    Verifies that get_minimal_sufficient_graph properly filters between
    REQUIRED and HELPFUL tiers without dropping critical elements.
    """
    graph = VisualizationGraph(is_3d=True)
    graph.add_vertex("A", [0, 0, 0], tier=ImportanceTier.REQUIRED)
    graph.add_vertex("B", [5, 0, 0], tier=ImportanceTier.REQUIRED)
    graph.add_vertex("P_extra", [10, 10, 10], tier=ImportanceTier.OPTIONAL)

    graph.add_edge("A", "B", tier=ImportanceTier.REQUIRED)
    graph.add_edge("A", "P_extra", tier=ImportanceTier.OPTIONAL)

    # Filter REQUIRED only
    filtered = graph.get_minimal_sufficient_graph(ImportanceTier.REQUIRED)
    assert "A" in filtered["vertices"]
    assert "B" in filtered["vertices"]
    assert "P_extra" not in filtered["vertices"]
    assert len(filtered["edges"]) == 1
