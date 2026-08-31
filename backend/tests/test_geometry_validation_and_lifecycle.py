"""Comprehensive Regression Test Suite for Geometry Engine, Validator, VisualizationSpec,
and Manim Job Lifecycle.
"""
from __future__ import annotations

import asyncio
import math
from typing import Any, Dict
import numpy as np
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from solver.dsl_parser import DSLParser
from solver.engine import GeometryEngine
from solver.validator import GeometryValidator, ValidationResult
from solver.models import Point, Constraint
from manim_client.schemas import (
    ErrorCode,
    StructuredError,
    VisualizationConfig,
    VisualizationSpec,
    MathRenderResponse,
    build_visualization_spec,
)
from manim_client.client import ManimClient


# ============================================================================
# 1. GEOMETRY ENGINE & CANONICAL PLACEMENT TESTS
# ============================================================================

def test_2d_rectangle_constraints():
    """Tests 2D rectangle parsing, solving, canonical placement and validation."""
    dsl = """
    RECTANGLE(ABCD)
    LENGTH(AB, 8)
    LENGTH(BC, 6)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)
    assert not is_3d

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None
    coords = result["coordinates"]
    assert "A" in coords and "B" in coords and "C" in coords and "D" in coords

    # Check mathematical scale and dimensions
    vA = np.array(coords["A"][:2])
    vB = np.array(coords["B"][:2])
    vC = np.array(coords["C"][:2])
    vD = np.array(coords["D"][:2])

    assert pytest.approx(np.linalg.norm(vB - vA), rel=1e-3) == 8.0
    assert pytest.approx(np.linalg.norm(vC - vB), rel=1e-3) == 6.0
    assert pytest.approx(np.linalg.norm(vD - vC), rel=1e-3) == 8.0
    assert pytest.approx(np.linalg.norm(vA - vD), rel=1e-3) == 6.0

    # Orthogonality: AB ⊥ BC
    dot = np.dot(vB - vA, vC - vB)
    assert pytest.approx(dot, abs=1e-3) == 0.0

    # Validate with GeometryValidator
    validator = GeometryValidator()
    val_res = validator.validate(result, constraints, is_3d)
    assert val_res.is_valid, f"Validation failed: {val_res.errors}"


def test_2d_equilateral_triangle():
    """Tests equilateral triangle parsing and solving."""
    dsl = """
    EQUILATERAL_TRIANGLE(ABC, 6)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None
    coords = result["coordinates"]

    vA = np.array(coords["A"][:2])
    vB = np.array(coords["B"][:2])
    vC = np.array(coords["C"][:2])

    assert pytest.approx(np.linalg.norm(vB - vA), rel=1e-2) == 6.0
    assert pytest.approx(np.linalg.norm(vC - vB), rel=1e-2) == 6.0
    assert pytest.approx(np.linalg.norm(vA - vC), rel=1e-2) == 6.0

    validator = GeometryValidator()
    val_res = validator.validate(result, constraints, is_3d)
    assert val_res.is_valid, f"Validation failed: {val_res.errors}"


def test_3d_canonical_pyramid_placement():
    """
    Tests 3D Pyramid S.ABCD with square base AB=4, SO ⊥ (ABCD), SO=6.
    Ensures canonical coordinate policy:
    - Base on z=0
    - Center O at mean of base
    - Apex S at (Ox, Oy, 6) along +Z
    - Mathematical scale preserved.
    """
    dsl = """
    PYRAMID(S_ABCD)
    SQUARE(ABCD)
    LENGTH(AB, 4)
    POINT(S)
    POINT(O)
    CENTER(O, ABCD)
    PERPENDICULAR_PLANE(SO, ABCD)
    LENGTH(SO, 6)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)
    assert is_3d

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None
    coords = result["coordinates"]

    # Verify base vertices are in plane z = 0
    for p in ["A", "B", "C", "D", "O"]:
        assert pytest.approx(coords[p][2], abs=1e-3) == 0.0, f"Point {p} not on z=0 ground plane"

    # Base square edge length = 4
    vA = np.array(coords["A"])
    vB = np.array(coords["B"])
    assert pytest.approx(np.linalg.norm(vB - vA), rel=1e-3) == 4.0

    # Center O is at midpoint/mean
    vO = np.array(coords["O"])
    mean_base = np.mean([coords["A"], coords["B"], coords["C"], coords["D"]], axis=0)
    assert pytest.approx(np.linalg.norm(vO - mean_base), abs=1e-3) == 0.0

    # Apex S is directly above O along +Z with height 6
    vS = np.array(coords["S"])
    assert pytest.approx(vS[0], abs=1e-3) == vO[0]
    assert pytest.approx(vS[1], abs=1e-3) == vO[1]
    assert pytest.approx(vS[2], abs=1e-3) == 6.0
    assert pytest.approx(np.linalg.norm(vS - vO), rel=1e-3) == 6.0

    # Validate with GeometryValidator
    validator = GeometryValidator()
    val_res = validator.validate(result, constraints, is_3d)
    assert val_res.is_valid, f"Validation failed: {val_res.errors}"


def test_3d_prism_canonical():
    """Tests 3D Triangular Prism ABC.DEF with side 5, height 8."""
    dsl = """
    PRISM(ABC_DEF)
    EQUILATERAL_TRIANGLE(ABC, 5)
    EQUILATERAL_TRIANGLE(DEF, 5)
    LENGTH(AD, 8)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)
    assert is_3d

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None
    coords = result["coordinates"]

    # Base 1 on z=0
    for p in ["A", "B", "C"]:
        assert pytest.approx(coords[p][2], abs=1e-3) == 0.0

    # Base 2 on z=8
    for p in ["D", "E", "F"]:
        assert pytest.approx(coords[p][2], abs=1e-3) == 8.0

    validator = GeometryValidator()
    val_res = validator.validate(result, constraints, is_3d)
    assert val_res.is_valid, f"Validation failed: {val_res.errors}"


def test_geometric_constraints_midpoint_section_point_on():
    """Tests MIDPOINT, SECTION, and POINT_ON constraints."""
    dsl = """
    POINT(A, 0, 0)
    POINT(B, 10, 0)
    POINT(M)
    MIDPOINT(M, AB)
    POINT(E)
    SECTION(E, A, B, 0.3)
    POINT(P)
    POINT_ON(P, AB)
    LENGTH(AP, 7)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None
    coords = result["coordinates"]

    assert pytest.approx(coords["M"][0], abs=1e-3) == 5.0
    assert pytest.approx(coords["E"][0], abs=1e-3) == 3.0
    assert pytest.approx(coords["P"][0], abs=1e-3) == 7.0

    validator = GeometryValidator()
    val_res = validator.validate(result, constraints, is_3d)
    assert val_res.is_valid, f"Validation failed: {val_res.errors}"


# ============================================================================
# 2. GEOMETRY VALIDATOR REJECTION TESTS
# ============================================================================

def test_validator_detects_length_violation():
    """Validator should reject coordinates when length constraint is violated."""
    engine_result = {
        "coordinates": {
            "A": [0.0, 0.0, 0.0],
            "B": [10.0, 0.0, 0.0],
        },
        "drawing_phases": [{"phase": 1, "points": ["A", "B"], "segments": [["A", "B"]]}],
    }
    # Expected length 5, actual is 10
    constraints = [Constraint(type="length", targets=["A", "B"], value=5.0)]

    validator = GeometryValidator(tolerance=0.05)
    val_res = validator.validate(engine_result, constraints, is_3d=False)
    assert not val_res.is_valid
    assert any("Length constraint violated" in err for err in val_res.errors)


def test_validator_detects_perpendicularity_violation():
    """Validator should reject non-orthogonal vectors for perpendicular constraint."""
    engine_result = {
        "coordinates": {
            "A": [0.0, 0.0, 0.0],
            "B": [1.0, 0.0, 0.0],
            "C": [0.0, 0.0, 0.0],
            "D": [1.0, 1.0, 0.0],  # 45 deg angle, not 90 deg
        },
        "drawing_phases": [],
    }
    constraints = [Constraint(type="perpendicular", targets=["A", "B", "C", "D"], value=0)]

    validator = GeometryValidator(tolerance=0.05)
    val_res = validator.validate(engine_result, constraints, is_3d=False)
    assert not val_res.is_valid
    assert any("Perpendicularity violated" in err for err in val_res.errors)


def test_validator_detects_degenerate_pyramid():
    """Validator should reject a 3D pyramid with collapsed coplanar apex."""
    engine_result = {
        "coordinates": {
            "S": [0.5, 0.5, 0.0],  # Apex on same plane as base
            "A": [0.0, 0.0, 0.0],
            "B": [1.0, 0.0, 0.0],
            "C": [1.0, 1.0, 0.0],
            "D": [0.0, 1.0, 0.0],
        },
        "solids": [{"type": "pyramid", "apex": "S", "base": ["A", "B", "C", "D"]}],
        "drawing_phases": [],
    }
    validator = GeometryValidator()
    val_res = validator.validate(engine_result, [], is_3d=True)
    assert not val_res.is_valid
    assert any("coplanar with base" in err for err in val_res.errors)


# ============================================================================
# 3. VISUALIZATIONSPEC & CONFIGURATION TESTS
# ============================================================================

def test_visualization_spec_show_axes_and_presentation_config():
    """Tests VisualizationSpec separation of geometry vs presentation config."""
    geometry_data = {
        "problem": "Hình chóp tam giác S.ABC",
        "coordinates": {
            "S": [0.0, 0.0, 4.0],
            "A": [0.0, 0.0, 0.0],
            "B": [3.0, 0.0, 0.0],
            "C": [1.5, 2.5, 0.0],
        },
        "solids": [{"type": "tetrahedron", "apex": "S", "base": ["A", "B", "C"], "points": ["S", "A", "B", "C"]}],
        "solution": {"steps": ["Bước 1: Dựng đáy ABC", "Bước 2: Dựng đỉnh S"]},
        "is_3d": True,
        "show_axes": True,
        "quality": "1080p",
    }

    spec = build_visualization_spec(geometry_data)

    # Verify presentation config
    assert spec.config.show_axes is True
    assert spec.config.is_3d is True
    assert spec.config.quality == "1080p"
    assert spec.show_axes is True

    # Verify mathematical geometry preserved
    assert len(spec.geometry) >= 4
    point_s = next(g for g in spec.geometry if g.label == "S")
    assert point_s.properties["coordinates"] == [0.0, 0.0, 4.0]

    # Verify prompt includes show_axes directive
    prompt = spec.to_prompt()
    assert "show_axes=True" in prompt


def test_visualization_spec_backward_compatibility():
    """Tests backward compatibility with default show_axes and output_config."""
    spec = build_visualization_spec(
        problem_text="Tính diện tích tam giác",
        coordinates={"A": [0, 0], "B": [4, 0], "C": [0, 3]},
        is_3d=False,
    )
    assert spec.config.show_axes is False
    assert spec.show_axes is False
    assert spec.output_config.format == "mp4"


# ============================================================================
# 4. MANIM CLIENT & LIFECYCLE TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_manim_client_successful_lifecycle():
    """Tests successful lifecycle transitions: queued -> rendering -> completed."""
    client = ManimClient(base_url="http://mock-manim:8001")
    spec = build_visualization_spec("Test problem")

    with patch("httpx.AsyncClient.post") as mock_post, patch("httpx.AsyncClient.get") as mock_get:
        # 1. Submit job -> returns queued
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"job_id": "test-uuid-123", "status": "queued"},
        )
        resp = await client.submit_render_job(spec)
        assert resp.status == "queued"
        assert resp.job_id == "test-uuid-123"

        # 2. Status polling -> generating -> rendering -> completed
        call_count = 0

        def mock_status():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {"job_id": "test-uuid-123", "status": "generating"}
            elif call_count == 2:
                return {"job_id": "test-uuid-123", "status": "rendering"}
            else:
                return {
                    "job_id": "test-uuid-123",
                    "status": "completed",
                    "video_url": "https://cdn.example.com/video.mp4",
                }

        mock_get.return_value = MagicMock(
            status_code=200,
            json=mock_status,
        )

        completed_resp = await client.poll_job_completion("test-uuid-123", timeout=10.0, poll_interval=0.01)
        assert completed_resp.status == "completed"
        assert completed_resp.video_url == "https://cdn.example.com/video.mp4"
        assert completed_resp.is_terminal() is True


@pytest.mark.asyncio
async def test_manim_client_unavailable_structured_error():
    """When Manim server is unreachable, returns terminal failed with MANIM_UNAVAILABLE."""
    import httpx
    client = ManimClient(base_url="http://unreachable-host:9999")
    spec = build_visualization_spec("Test problem")

    with patch("httpx.AsyncClient.post", side_effect=httpx.ConnectError("Connection refused")):
        resp = await client.submit_render_job(spec)
        assert resp.status == "failed"
        assert resp.get_error_code() == ErrorCode.MANIM_UNAVAILABLE
        assert "không khả dụng" in (resp.get_error_message() or "")


@pytest.mark.asyncio
async def test_manim_client_polling_timeout_terminal_failed():
    """When polling times out, returns terminal failed with MANIM_TIMEOUT (no hanging)."""
    client = ManimClient(base_url="http://mock-manim:8001")

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"job_id": "slow-job", "status": "rendering"},
        )

        resp = await client.poll_job_completion("slow-job", timeout=0.05, poll_interval=0.01)
        assert resp.status == "failed"
        assert resp.get_error_code() == ErrorCode.MANIM_TIMEOUT
        assert resp.is_terminal() is True


@pytest.mark.asyncio
async def test_manim_client_404_job_not_found():
    """When job status returns HTTP 404, returns JOB_NOT_FOUND error code."""
    client = ManimClient(base_url="http://mock-manim:8001")

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=404,
            text="Not Found",
        )

        resp = await client.get_job_status("nonexistent-job")
        assert resp.status == "failed"
        assert resp.get_error_code() == ErrorCode.JOB_NOT_FOUND


@pytest.mark.asyncio
async def test_manim_client_render_failed_structured_error():
    """When render job fails on server, returns MANIM_RENDER_FAILED error code."""
    client = ManimClient(base_url="http://mock-manim:8001")

    with patch("httpx.AsyncClient.get") as mock_get:
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "job_id": "failed-job",
                "status": "failed",
                "error": "Manim compilation syntax error at line 42",
            },
        )

        resp = await client.get_job_status("failed-job")
        assert resp.status == "failed"
        assert resp.get_error_code() == ErrorCode.MANIM_RENDER_FAILED
        assert "Manim compilation" in (resp.get_error_message() or "")
