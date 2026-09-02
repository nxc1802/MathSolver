"""
Pipeline Evaluation Runner.

Runs evaluation suites over benchmark datasets and computes structured performance metrics.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from eval.benchmark import BenchmarkDataset, BenchmarkSample
from eval.metrics import (
    OCRMetrics,
    ParserMetrics,
    PipelineEvalSummary,
    SolverMetrics,
    compute_cer,
    compute_wer,
)
from solver.dsl_parser import DSLParser
from solver.engine import GeometryEngine
from solver.validator import GeometryStatus, GeometryValidator

logger = logging.getLogger(__name__)


class EvalRunner:
    """Runs pipeline evaluation over benchmark datasets."""

    def __init__(
        self,
        dsl_parser: Optional[DSLParser] = None,
        geometry_engine: Optional[GeometryEngine] = None,
        geometry_validator: Optional[GeometryValidator] = None,
    ):
        self.dsl_parser = dsl_parser or DSLParser()
        self.geometry_engine = geometry_engine or GeometryEngine()
        self.geometry_validator = geometry_validator or GeometryValidator()

    def evaluate_dsl_deterministic(self, dataset: BenchmarkDataset) -> ParserMetrics:
        """
        Evaluates DSL parsing, solving, and geometric invariant validation
        deterministically without LLM calls.
        """
        total = len(dataset)
        if total == 0:
            return ParserMetrics()

        valid_dsl_count = 0
        solvable_count = 0
        validated_count = 0
        degraded_count = 0

        for sample in dataset:
            dsl = sample.expected_dsl or ""
            if not dsl:
                continue

            try:
                points, constraints, is_3d = self.dsl_parser.parse(dsl)
                valid_dsl_count += 1

                engine_res = self.geometry_engine.solve(points, constraints, is_3d)
                if engine_res and engine_res.get("coordinates"):
                    solvable_count += 1
                    val_res = self.geometry_validator.validate(engine_res, constraints, is_3d)
                    if val_res.is_valid:
                        validated_count += 1
                    else:
                        degraded_count += 1
            except Exception as e:
                logger.debug(f"[EvalRunner] Sample {sample.id} evaluation error: {e}")

        return ParserMetrics(
            total_samples=total,
            json_valid_rate=1.0,
            dsl_valid_rate=valid_dsl_count / total,
            solvability_rate=solvable_count / total,
            validation_pass_rate=validated_count / total,
            degradation_rate=degraded_count / total,
        )

    async def evaluate_full_pipeline(
        self,
        dataset: BenchmarkDataset,
        orchestrator: Any = None,
    ) -> PipelineEvalSummary:
        """
        Executes end-to-end evaluation using Orchestrator across benchmark samples.
        """
        from agents.orchestrator import Orchestrator

        orch = orchestrator or Orchestrator()
        total = len(dataset)
        if total == 0:
            return PipelineEvalSummary()

        e2e_successes = 0
        total_latency_ms = 0.0
        parser_metrics = ParserMetrics(total_samples=total)
        solver_metrics = SolverMetrics(total_samples=total)
        ocr_metrics = OCRMetrics(total_samples=total)

        valid_dsl_count = 0
        solvable_count = 0
        validated_count = 0
        degraded_count = 0
        correct_answer_count = 0

        for sample in dataset:
            t0 = time.time()
            try:
                result = await orch.run(
                    text=sample.problem_text,
                    image_url=sample.image_url,
                    generate_video=False,
                )
                latency = (time.time() - t0) * 1000
                total_latency_ms += latency

                if result.get("status") == "success":
                    e2e_successes += 1

                # Check geometry status
                geo_status = result.get("geometry_status")
                if result.get("geometry_dsl"):
                    valid_dsl_count += 1
                if result.get("coordinates"):
                    solvable_count += 1
                if geo_status == GeometryStatus.VALID.value:
                    validated_count += 1
                elif geo_status == GeometryStatus.DEGRADED.value:
                    degraded_count += 1

                # Check answer if expected_answer is present
                if sample.expected_answer:
                    actual_ans = str((result.get("solution") or {}).get("answer", ""))
                    if sample.expected_answer.strip() in actual_ans or actual_ans.strip() in sample.expected_answer:
                        correct_answer_count += 1

            except Exception as e:
                logger.error(f"[EvalRunner] Full pipeline run failed on sample {sample.id}: {e}")

        parser_metrics.dsl_valid_rate = valid_dsl_count / total
        parser_metrics.solvability_rate = solvable_count / total
        parser_metrics.validation_pass_rate = validated_count / total
        parser_metrics.degradation_rate = degraded_count / total
        solver_metrics.answer_exact_match_rate = correct_answer_count / max(total, 1)

        return PipelineEvalSummary(
            ocr=ocr_metrics,
            parser=parser_metrics,
            solver=solver_metrics,
            e2e_success_rate=e2e_successes / total,
            avg_latency_ms=total_latency_ms / max(total, 1),
            total_samples=total,
        )
