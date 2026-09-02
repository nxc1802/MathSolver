"""Deterministic Geometry Validation Engine.

Validates solved coordinates against geometric invariants and DSL constraints
before visualization or external rendering dispatch.
"""
from __future__ import annotations

import logging
import math
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from .models import Constraint

logger = logging.getLogger(__name__)


class GeometryStatus(str, Enum):
    """Geometry validation outcome status."""
    VALID = "valid"
    DEGRADED = "degraded"
    FAILED = "failed"


class StructuredError:
    """Machine-readable validation error for LLM repair feedback."""

    def __init__(
        self,
        error_type: str,
        constraint: str,
        expected: str = "",
        actual: str = "",
        instruction: str = "Correct the DSL to satisfy this constraint.",
    ):
        self.error_type = error_type
        self.constraint = constraint
        self.expected = expected
        self.actual = actual
        self.instruction = instruction

    def to_dict(self) -> Dict[str, str]:
        return {
            "error_type": self.error_type,
            "constraint": self.constraint,
            "expected": self.expected,
            "actual": self.actual,
            "instruction": self.instruction,
        }


class ValidationResult:
    def __init__(
        self,
        is_valid: bool = True,
        errors: Optional[List[str]] = None,
        warnings: Optional[List[str]] = None,
        checked_count: int = 0,
        status: GeometryStatus = GeometryStatus.VALID,
        structured_errors: Optional[List[StructuredError]] = None,
    ):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.checked_count = checked_count
        self.status = status
        self.structured_errors = structured_errors or []

    @property
    def error_summary(self) -> str:
        if not self.errors:
            return ""
        return "; ".join(self.errors[:5])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "status": self.status.value,
            "errors": self.errors,
            "warnings": self.warnings,
            "checked_count": self.checked_count,
            "error_summary": self.error_summary,
        }

    def to_structured_feedback(self) -> Dict[str, Any]:
        """Returns structured feedback JSON for LLM repair loops."""
        return {
            "status": self.status.value,
            "error_count": len(self.errors),
            "details": [e.to_dict() for e in self.structured_errors[:5]],
            "instruction": "Correct the DSL to satisfy all constraints listed above.",
        }


class GeometryValidator:
    """
    Validates geometric invariants and constraint satisfaction on solved coordinates.
    """

    def __init__(self, tolerance: float = 0.05):
        self.tolerance = tolerance

    def _vec(self, coords: Dict[str, List[float]], pid: str) -> Optional[np.ndarray]:
        if pid not in coords:
            return None
        c = coords[pid]
        if len(c) == 2:
            return np.array([float(c[0]), float(c[1]), 0.0], dtype=float)
        elif len(c) >= 3:
            return np.array([float(c[0]), float(c[1]), float(c[2])], dtype=float)
        return None

    def validate(
        self,
        engine_result: Dict[str, Any],
        constraints: Optional[List[Constraint]] = None,
        is_3d: bool = False,
    ) -> ValidationResult:
        if not engine_result or not isinstance(engine_result, dict):
            return ValidationResult(is_valid=False, errors=["Empty or invalid engine result dictionary."])

        coords: Dict[str, List[float]] = engine_result.get("coordinates", {})
        if not coords or not isinstance(coords, dict):
            return ValidationResult(is_valid=False, errors=["Coordinates map is empty or missing."])

        errors: List[str] = []
        warnings: List[str] = []
        checked = 0

        # 1. Check all coordinates are finite numbers
        for pid, pt in coords.items():
            checked += 1
            if not isinstance(pt, (list, tuple)) or len(pt) < 2:
                errors.append(f"Point '{pid}' has invalid coordinate format: {pt}")
                continue
            for val in pt:
                if val is None or math.isnan(val) or math.isinf(val):
                    errors.append(f"Point '{pid}' contains non-finite coordinate value: {val}")

        if errors:
            return ValidationResult(is_valid=False, errors=errors, warnings=warnings, checked_count=checked)

        # 2. Check for distinct point collapse / degeneracy
        point_ids = list(coords.keys())
        for i in range(len(point_ids)):
            for j in range(i + 1, len(point_ids)):
                p1_id, p2_id = point_ids[i], point_ids[j]
                v1 = self._vec(coords, p1_id)
                v2 = self._vec(coords, p2_id)
                if v1 is not None and v2 is not None:
                    dist = float(np.linalg.norm(v1 - v2))
                    if dist < 1e-4:
                        warnings.append(f"Points '{p1_id}' and '{p2_id}' are nearly coincident (dist={dist:.2e}).")

        # 3. Validate drawing phases segments non-zero length
        drawing_phases = engine_result.get("drawing_phases", [])
        for phase in drawing_phases:
            for seg in phase.get("segments", []):
                if len(seg) == 2:
                    p1, p2 = seg[0], seg[1]
                    v1, v2 = self._vec(coords, p1), self._vec(coords, p2)
                    checked += 1
                    if v1 is None or v2 is None:
                        errors.append(f"Segment references missing point '{p1}' or '{p2}'.")
                    else:
                        length = float(np.linalg.norm(v2 - v1))
                        if length < 1e-5:
                            errors.append(f"Degenerate zero-length segment between '{p1}' and '{p2}'.")

        # 4. Validate 3D solids topology if present
        solids = engine_result.get("solids", [])
        for s in solids:
            s_type = s.get("type")
            checked += 1
            if s_type == "pyramid":
                apex = s.get("apex")
                base = s.get("base", [])
                v_apex = self._vec(coords, apex) if apex else None
                if v_apex is None:
                    errors.append(f"Pyramid apex '{apex}' not found in coordinates.")
                if len(base) < 3:
                    errors.append(f"Pyramid base must have >= 3 points, got: {base}")
                else:
                    base_vecs = [self._vec(coords, bp) for bp in base]
                    if any(bv is None for bv in base_vecs):
                        errors.append(f"Pyramid base contains missing points: {base}")
                    elif v_apex is not None:
                        # Check apex is not coplanar with base
                        v0 = base_vecs[0]
                        v1 = base_vecs[1]
                        v2 = base_vecs[2]
                        normal = np.cross(v1 - v0, v2 - v0)
                        norm_mag = float(np.linalg.norm(normal))
                        if norm_mag > 1e-5:
                            altitude = abs(float(np.dot(v_apex - v0, normal))) / norm_mag
                            if altitude < 1e-3:
                                errors.append(f"Pyramid apex '{apex}' is coplanar with base (altitude={altitude:.2e}).")
            elif s_type in ("prism", "cube", "cuboid", "frustum"):
                b1 = s.get("base1", [])
                b2 = s.get("base2", [])
                if len(b1) != len(b2) or len(b1) < 3:
                    errors.append(f"Solid '{s_type}' requires equal base sizes >= 3, got base1={len(b1)}, base2={len(b2)}.")
                else:
                    b1_vecs = [self._vec(coords, p) for p in b1]
                    b2_vecs = [self._vec(coords, p) for p in b2]
                    if any(v is None for v in b1_vecs + b2_vecs):
                        errors.append(f"Solid '{s_type}' contains missing points in bases.")
                    else:
                        # Height between bases > 0
                        h_dist = float(np.linalg.norm(b2_vecs[0] - b1_vecs[0]))
                        if h_dist < 1e-3:
                            errors.append(f"Solid '{s_type}' has collapsed zero height between bases.")

        # 5. Validate specific DSL constraints if provided
        if constraints:
            for c in constraints:
                c_type = c.type
                targets = c.targets
                val = c.value
                checked += 1

                if c_type == "length" and len(targets) == 2:
                    p1, p2 = targets[0], targets[1]
                    v1, v2 = self._vec(coords, p1), self._vec(coords, p2)
                    if v1 is not None and v2 is not None:
                        expected_len = float(val)
                        actual_len = float(np.linalg.norm(v2 - v1))
                        denom = max(expected_len, 1.0)
                        rel_err = abs(actual_len - expected_len) / denom
                        if rel_err > self.tolerance:
                            errors.append(
                                f"Length constraint violated: |{p1}{p2}| expected {expected_len:.2f}, got {actual_len:.2f} (err={rel_err:.1%})"
                            )

                elif c_type == "length_equal" and len(targets) == 4:
                    pA, pB, pC, pD = targets[0], targets[1], targets[2], targets[3]
                    va, vb, vc, vd = self._vec(coords, pA), self._vec(coords, pB), self._vec(coords, pC), self._vec(coords, pD)
                    if all(v is not None for v in [va, vb, vc, vd]):
                        len1 = float(np.linalg.norm(vb - va))
                        len2 = float(np.linalg.norm(vd - vc))
                        denom = max(len1, len2, 1.0)
                        rel_err = abs(len1 - len2) / denom
                        if rel_err > self.tolerance:
                            errors.append(
                                f"Equal length violated: |{pA}{pB}|={len1:.2f} vs |{pC}{pD}|={len2:.2f} (err={rel_err:.1%})"
                            )

                elif c_type == "perpendicular" and len(targets) == 4:
                    pA, pB, pC, pD = targets[0], targets[1], targets[2], targets[3]
                    va, vb, vc, vd = self._vec(coords, pA), self._vec(coords, pB), self._vec(coords, pC), self._vec(coords, pD)
                    if all(v is not None for v in [va, vb, vc, vd]):
                        v1 = vb - va
                        v2 = vd - vc
                        mag1, mag2 = float(np.linalg.norm(v1)), float(np.linalg.norm(v2))
                        if mag1 > 1e-4 and mag2 > 1e-4:
                            cos_theta = abs(float(np.dot(v1, v2)) / (mag1 * mag2))
                            if cos_theta > self.tolerance:
                                errors.append(f"Perpendicularity violated: {pA}{pB} not perpendicular to {pC}{pD} (cos={cos_theta:.3f})")

                elif c_type == "parallel" and len(targets) == 4:
                    pA, pB, pC, pD = targets[0], targets[1], targets[2], targets[3]
                    va, vb, vc, vd = self._vec(coords, pA), self._vec(coords, pB), self._vec(coords, pC), self._vec(coords, pD)
                    if all(v is not None for v in [va, vb, vc, vd]):
                        v1 = vb - va
                        v2 = vd - vc
                        mag1, mag2 = float(np.linalg.norm(v1)), float(np.linalg.norm(v2))
                        if mag1 > 1e-4 and mag2 > 1e-4:
                            sin_theta = float(np.linalg.norm(np.cross(v1, v2))) / (mag1 * mag2)
                            if sin_theta > self.tolerance:
                                errors.append(f"Parallelism violated: {pA}{pB} not parallel to {pC}{pD} (sin={sin_theta:.3f})")

                elif c_type == "perp_plane" and len(targets) >= 4:
                    pL1, pL2 = targets[0], targets[1]
                    plane_pts = targets[2:]
                    vL1, vL2 = self._vec(coords, pL1), self._vec(coords, pL2)
                    if vL1 is not None and vL2 is not None:
                        v_line = vL2 - vL1
                        l_mag = float(np.linalg.norm(v_line))
                        if l_mag > 1e-4:
                            p0 = self._vec(coords, plane_pts[0])
                            if p0 is not None:
                                for p_other in plane_pts[1:]:
                                    p_v = self._vec(coords, p_other)
                                    if p_v is not None:
                                        v_plane = p_v - p0
                                        p_mag = float(np.linalg.norm(v_plane))
                                        if p_mag > 1e-4:
                                            cos_t = abs(float(np.dot(v_line, v_plane)) / (l_mag * p_mag))
                                            if cos_t > self.tolerance:
                                                errors.append(
                                                    f"Perpendicular plane violated: {pL1}{pL2} not perpendicular to {plane_pts[0]}{p_other} (cos={cos_t:.3f})"
                                                )

                elif c_type == "midpoint" and len(targets) == 3:
                    pM, pA, pB = targets[0], targets[1], targets[2]
                    vM, vA, vB = self._vec(coords, pM), self._vec(coords, pA), self._vec(coords, pB)
                    if all(v is not None for v in [vM, vA, vB]):
                        expected_mid = (vA + vB) / 2.0
                        denom = max(float(np.linalg.norm(vB - vA)), 1.0)
                        err = float(np.linalg.norm(vM - expected_mid)) / denom
                        if err > self.tolerance:
                            errors.append(f"Midpoint constraint violated: '{pM}' is not midpoint of '{pA}{pB}' (err={err:.1%})")

                elif c_type == "section" and len(targets) == 3:
                    pE, pA, pC = targets[0], targets[1], targets[2]
                    vE, vA, vC = self._vec(coords, pE), self._vec(coords, pA), self._vec(coords, pC)
                    if all(v is not None for v in [vE, vA, vC]):
                        k = float(val)
                        expected_pt = vA + k * (vC - vA)
                        denom = max(float(np.linalg.norm(vC - vA)), 1.0)
                        err = float(np.linalg.norm(vE - expected_pt)) / denom
                        if err > self.tolerance:
                            errors.append(f"Section constraint violated: '{pE}' != {pA} + {k}({pC}-{pA}) (err={err:.1%})")

                elif c_type == "center" and len(targets) >= 3:
                    pO = targets[0]
                    v_poly = targets[1:]
                    vO = self._vec(coords, pO)
                    poly_vecs = [self._vec(coords, p) for p in v_poly]
                    if vO is not None and all(v is not None for v in poly_vecs):
                        mean_center = np.mean(poly_vecs, axis=0)
                        denom = max(float(np.linalg.norm(poly_vecs[1] - poly_vecs[0])), 1.0) if len(poly_vecs) > 1 else 1.0
                        err = float(np.linalg.norm(vO - mean_center)) / denom
                        if err > self.tolerance:
                            errors.append(f"Center constraint violated: '{pO}' is not center of {v_poly} (err={err:.1%})")

                elif c_type == "coplanar" and len(targets) >= 4:
                    pA, pB, pC, pD = targets[0], targets[1], targets[2], targets[3]
                    va, vb, vc, vd = self._vec(coords, pA), self._vec(coords, pB), self._vec(coords, pC), self._vec(coords, pD)
                    if all(v is not None for v in [va, vb, vc, vd]):
                        v1 = vb - va
                        v2 = vc - va
                        v3 = vd - va
                        cross = np.cross(v1, v2)
                        cross_mag = float(np.linalg.norm(cross))
                        if cross_mag > 1e-4:
                            dist = abs(float(np.dot(v3, cross))) / cross_mag
                            denom = max(float(np.linalg.norm(v3)), 1.0)
                            if dist / denom > self.tolerance:
                                errors.append(f"Coplanar constraint violated for {targets[:4]} (dist={dist:.2e})")

                elif c_type in ("point_on_plane", "point_on") and len(targets) >= 3:
                    if c_type == "point_on_plane" and len(targets) >= 4:
                        pP, pA, pB, pC = targets[0], targets[1], targets[2], targets[3]
                        vp, va, vb, vc = self._vec(coords, pP), self._vec(coords, pA), self._vec(coords, pB), self._vec(coords, pC)
                        if all(v is not None for v in [vp, va, vb, vc]):
                            normal = np.cross(vb - va, vc - va)
                            n_mag = float(np.linalg.norm(normal))
                            if n_mag > 1e-4:
                                dist = abs(float(np.dot(vp - va, normal))) / n_mag
                                denom = max(float(np.linalg.norm(vp - va)), 1.0)
                                if dist / denom > self.tolerance:
                                    errors.append(f"Point on plane violated: '{pP}' not on plane({pA},{pB},{pC}) (dist={dist:.2e})")
                    elif c_type == "point_on" and len(targets) == 3:
                        pP, pA, pB = targets[0], targets[1], targets[2]
                        vp, va, vb = self._vec(coords, pP), self._vec(coords, pA), self._vec(coords, pB)
                        if all(v is not None for v in [vp, va, vb]):
                            v_line = vb - va
                            l_mag = float(np.linalg.norm(v_line))
                            if l_mag > 1e-4:
                                dist = float(np.linalg.norm(np.cross(vp - va, v_line))) / l_mag
                                denom = max(l_mag, 1.0)
                                if dist / denom > self.tolerance:
                                    errors.append(f"Point on line/segment violated: '{pP}' not on '{pA}{pB}' (dist={dist:.2e})")

                elif c_type == "angle" and len(targets) >= 1:
                    v_name = targets[0]
                    p1_name = targets[1] if len(targets) > 1 else None
                    p2_name = targets[2] if len(targets) > 2 else None
                    if p1_name and p2_name:
                        pV, p1, p2 = self._vec(coords, v_name), self._vec(coords, p1_name), self._vec(coords, p2_name)
                        if all(v is not None for v in [pV, p1, p2]):
                            v1 = p1 - pV
                            v2 = p2 - pV
                            mag1, mag2 = float(np.linalg.norm(v1)), float(np.linalg.norm(v2))
                            if mag1 > 1e-4 and mag2 > 1e-4:
                                cos_val = float(np.dot(v1, v2)) / (mag1 * mag2)
                                cos_val = max(-1.0, min(1.0, cos_val))
                                actual_deg = float(np.rad2deg(np.arccos(cos_val)))
                                target_deg = float(val)
                                if abs(actual_deg - target_deg) > 4.0:
                                    errors.append(
                                        f"Angle constraint violated at '{v_name}': expected {target_deg:.1f}°, got {actual_deg:.1f}°"
                                    )

        is_valid = len(errors) == 0
        status = GeometryStatus.VALID if is_valid else GeometryStatus.FAILED

        # Build structured errors for LLM repair feedback
        structured_errors: List[StructuredError] = []
        for err_msg in errors:
            # Parse error messages into structured format
            if "Length constraint violated" in err_msg:
                structured_errors.append(StructuredError(
                    error_type="constraint_violation",
                    constraint=err_msg.split(":")[0] if ":" in err_msg else err_msg,
                    expected=err_msg,
                    actual="",
                    instruction="Correct the DSL length values to match the constraint.",
                ))
            elif "Perpendicularity violated" in err_msg:
                structured_errors.append(StructuredError(
                    error_type="constraint_violation",
                    constraint=err_msg.split(":")[0] if ":" in err_msg else err_msg,
                    expected="dot(v1, v2) = 0",
                    actual=err_msg,
                    instruction="Correct the DSL to ensure perpendicularity constraint is satisfied.",
                ))
            elif "Parallelism violated" in err_msg:
                structured_errors.append(StructuredError(
                    error_type="constraint_violation",
                    constraint=err_msg.split(":")[0] if ":" in err_msg else err_msg,
                    expected="cross(v1, v2) = 0",
                    actual=err_msg,
                    instruction="Correct the DSL to ensure parallelism constraint is satisfied.",
                ))
            else:
                structured_errors.append(StructuredError(
                    error_type="validation_error",
                    constraint=err_msg,
                    instruction="Correct the DSL to resolve this validation error.",
                ))

        if not is_valid:
            logger.warning(f"[GeometryValidator] Validation FAILED with {len(errors)} errors: {errors[:3]}")
        else:
            logger.info(f"[GeometryValidator] Validation PASSED ({checked} checks performed).")

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            checked_count=checked,
            status=status,
            structured_errors=structured_errors,
        )
