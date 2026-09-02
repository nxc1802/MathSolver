"""
End-to-End and Regression Test Suite for MathSolver Pipeline.

Verifies:
1. DSL Parser + Geometry Engine + Geometry Validator integration.
2. Canonical 3D solids (Pyramid, Cube, Prism, Cone) coordinate solving & invariants.
3. GeometryStatus propagation (VALID, DEGRADED, FAILED).
4. Machine-readable structured error feedback for LLM repair loops.
5. Evaluation framework components and metrics calculation.
"""

from __future__ import annotations

import pytest
from eval.benchmark import BenchmarkDataset, BenchmarkSample
from eval.metrics import compute_cer, compute_wer, latex_match
from eval.runner import EvalRunner
from solver.dsl_parser import DSLParser
from solver.engine import GeometryEngine
from solver.validator import GeometryStatus, GeometryValidator, StructuredError, ValidationResult


def test_metric_calculations():
    """Verify CER, WER, and LaTeX matching functions."""
    # CER
    assert compute_cer("SA = 6", "SA = 6") == 0.0
    assert compute_cer("SA = 6", "SA = 8") == pytest.approx(1 / 6)
    assert compute_cer("", "") == 0.0

    # WER
    assert compute_wer("Cho hình vuông ABCD", "Cho hình vuông ABCD") == 0.0
    assert compute_wer("Cho hình vuông ABCD", "Cho hình chữ nhật ABCD") == pytest.approx(2 / 4)

    # LaTeX matching
    assert latex_match("\\frac{1}{3} \\cdot S \\cdot h", "\\frac{1}{3} * S * h")
    assert latex_match("S_{ABCD}", "S_{ABCD}")


def test_validator_structured_feedback():
    """Verify that ValidationResult properly generates structured error feedback."""
    err = StructuredError(
        error_type="constraint_violation",
        constraint="Length constraint violated",
        expected="AB = 4",
        actual="AB = 5",
        instruction="Correct the DSL length values.",
    )
    res = ValidationResult(
        is_valid=False,
        errors=["Length constraint violated: |AB| expected 4.00, got 5.00"],
        status=GeometryStatus.FAILED,
        structured_errors=[err],
    )
    fb = res.to_structured_feedback()
    assert fb["status"] == "failed"
    assert fb["error_count"] == 1
    assert len(fb["details"]) == 1
    assert fb["details"][0]["error_type"] == "constraint_violation"
    assert fb["details"][0]["constraint"] == "Length constraint violated"


def test_regression_pyramid_solving_and_validation():
    """Tests S.ABCD square pyramid DSL parse -> engine solve -> validator pass."""
    dsl = """
    PYRAMID(S_ABCD)
    SQUARE(ABCD)
    LENGTH(AB, 4)
    LENGTH(SA, 6)
    PERPENDICULAR_PLANE(SA, ABCD)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)
    assert is_3d is True
    assert len(points) >= 5

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None
    coords = result.get("coordinates", {})
    assert len(coords) >= 5
    assert "S" in coords and "A" in coords

    validator = GeometryValidator()
    val_res = validator.validate(result, constraints, is_3d)
    assert val_res.is_valid is True
    assert val_res.status == GeometryStatus.VALID


def test_regression_cube_solving_and_validation():
    """Tests Cube ABCD.A1B1C1D1 DSL parse -> engine solve -> validator pass."""
    dsl = """
    CUBE(ABCD_A1B1C1D1)
    LENGTH(AB, 5)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)
    assert is_3d is True

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None
    coords = result.get("coordinates", {})
    assert len(coords) >= 8

    validator = GeometryValidator()
    val_res = validator.validate(result, constraints, is_3d)
    assert val_res.is_valid is True
    assert val_res.status == GeometryStatus.VALID


def test_regression_triangular_prism_solving_and_validation():
    """Tests Right Triangular Prism ABC.A1B1C1 solving & validation."""
    dsl = """
    PRISM(ABC_A1B1C1)
    POINT(A, 0, 0, 0)
    POINT(B, 3, 0, 0)
    POINT(C, 0, 4, 0)
    POINT(A1, 0, 0, 6)
    POINT(B1, 3, 0, 6)
    POINT(C1, 0, 4, 6)
    LENGTH(AA1, 6)
    PERPENDICULAR_PLANE(AA1, ABC)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)
    assert is_3d is True

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None
    coords = result.get("coordinates", {})
    assert len(coords) >= 6

    validator = GeometryValidator()
    val_res = validator.validate(result, constraints, is_3d)
    assert val_res.is_valid is True
    assert val_res.status == GeometryStatus.VALID


def test_regression_cone_solving():
    """Tests Cone with apex S and base center O."""
    dsl = "CONE(S_O, 3, 4)"
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)
    assert is_3d is True

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None
    coords = result.get("coordinates", {})
    assert "S" in coords and "O" in coords


def test_regression_2d_rectangle_solving_and_validation():
    """Tests 2D Rectangle ABCD solving & validation."""
    dsl = """
    RECTANGLE(ABCD)
    LENGTH(AB, 6)
    LENGTH(BC, 8)
    """
    parser = DSLParser()
    points, constraints, is_3d = parser.parse(dsl)
    assert is_3d is False

    engine = GeometryEngine()
    result = engine.solve(points, constraints, is_3d)
    assert result is not None
    coords = result.get("coordinates", {})
    assert len(coords) == 4

    validator = GeometryValidator()
    val_res = validator.validate(result, constraints, is_3d)
    assert val_res.is_valid is True
    assert val_res.status == GeometryStatus.VALID


def test_eval_runner_on_benchmark():
    """Tests EvalRunner deterministic pass over benchmark dataset."""
    dataset = BenchmarkDataset.load_all_standard()
    assert len(dataset) >= 5

    runner = EvalRunner()
    metrics = runner.evaluate_dsl_deterministic(dataset)
    assert metrics.total_samples >= 5
    assert metrics.dsl_valid_rate == 1.0
    assert metrics.solvability_rate == 1.0
    assert metrics.validation_pass_rate == 1.0
    assert metrics.degradation_rate == 0.0
