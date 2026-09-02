"""
Evaluation Metrics for MathSolver Pipeline.

Defines metric calculators across all pipeline stages:
- OCR: Character Error Rate (CER), Word Error Rate (WER), LaTeX Exact Match, Confidence Calibration
- Parser: JSON Validity, DSL Validity, Geometry Solvability, Validation Pass Rate
- Solver: Final Answer Accuracy, SymPy Verification Rate
- End-to-End: E2E Accuracy, Latency, Token / LLM Usage, OCR Correction Rate, Geometry Degradation Rate
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Computes standard Levenshtein edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def compute_cer(reference: str, hypothesis: str) -> float:
    """Character Error Rate (CER)."""
    if not reference and not hypothesis:
        return 0.0
    if not reference:
        return 1.0
    dist = _levenshtein_distance(reference, hypothesis)
    return float(dist / max(len(reference), 1))


def compute_wer(reference: str, hypothesis: str) -> float:
    """Word Error Rate (WER)."""
    ref_words = reference.strip().split()
    hyp_words = hypothesis.strip().split()
    if not ref_words and not hyp_words:
        return 0.0
    if not ref_words:
        return 1.0

    # Word-level edit distance
    n, m = len(ref_words), len(hyp_words)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        dp[i][0] = i
    for j in range(m + 1):
        dp[0][j] = j

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + 1)

    return float(dp[n][m] / max(n, 1))


def normalize_latex(formula: str) -> str:
    """Normalizes LaTeX whitespace and common variations for comparison."""
    if not formula:
        return ""
    f = formula.strip()
    f = re.sub(r"\s+", "", f)
    f = f.replace("\\cdot", "*").replace("\\times", "*")
    f = re.sub(r"\\left|\\right", "", f)
    return f


def latex_match(ref: str, hyp: str) -> bool:
    """Checks whether two LaTeX expressions match after normalization."""
    return normalize_latex(ref) == normalize_latex(hyp)


@dataclass
class OCRMetrics:
    """Aggregated OCR metrics across evaluated samples."""
    total_samples: int = 0
    avg_cer: float = 0.0
    avg_wer: float = 0.0
    latex_exact_match_rate: float = 0.0
    vlm_trigger_rate: float = 0.0
    vlm_correction_rate: float = 0.0
    confidence_calibration_bins: Dict[str, Dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_samples": self.total_samples,
            "avg_cer": round(self.avg_cer, 4),
            "avg_wer": round(self.avg_wer, 4),
            "latex_exact_match_rate": round(self.latex_exact_match_rate, 4),
            "vlm_trigger_rate": round(self.vlm_trigger_rate, 4),
            "vlm_correction_rate": round(self.vlm_correction_rate, 4),
            "confidence_calibration": self.confidence_calibration_bins,
        }


@dataclass
class ParserMetrics:
    """Aggregated Parser metrics."""
    total_samples: int = 0
    json_valid_rate: float = 0.0
    dsl_valid_rate: float = 0.0
    solvability_rate: float = 0.0
    validation_pass_rate: float = 0.0
    degradation_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_samples": self.total_samples,
            "json_valid_rate": round(self.json_valid_rate, 4),
            "dsl_valid_rate": round(self.dsl_valid_rate, 4),
            "solvability_rate": round(self.solvability_rate, 4),
            "validation_pass_rate": round(self.validation_pass_rate, 4),
            "degradation_rate": round(self.degradation_rate, 4),
        }


@dataclass
class SolverMetrics:
    """Aggregated Solver metrics."""
    total_samples: int = 0
    answer_exact_match_rate: float = 0.0
    sympy_verification_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_samples": self.total_samples,
            "answer_exact_match_rate": round(self.answer_exact_match_rate, 4),
            "sympy_verification_rate": round(self.sympy_verification_rate, 4),
        }


@dataclass
class PipelineEvalSummary:
    """Complete End-to-End Evaluation Report."""
    ocr: OCRMetrics = field(default_factory=OCRMetrics)
    parser: ParserMetrics = field(default_factory=ParserMetrics)
    solver: SolverMetrics = field(default_factory=SolverMetrics)
    e2e_success_rate: float = 0.0
    avg_latency_ms: float = 0.0
    total_samples: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_samples": self.total_samples,
            "e2e_success_rate": round(self.e2e_success_rate, 4),
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "ocr_metrics": self.ocr.to_dict(),
            "parser_metrics": self.parser.to_dict(),
            "solver_metrics": self.solver.to_dict(),
        }
