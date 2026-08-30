"""End-to-End Test for Manim Video Generation Module Integration."""
import asyncio
import json
import logging
import sys

from manim_client.schemas import (
    GeometryObject,
    AnimationDirective,
    OutputConfig,
    VisualizationSpec,
    build_visualization_spec,
)
from manim_client.client import ManimClient
from agents.orchestrator import Orchestrator

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
logger = logging.getLogger(__name__)


async def test_visualization_spec_building():
    logger.info("================================================================================")
    logger.info("🧪 TEST 1: VisualizationSpec Building & Prompt Serialization")
    logger.info("================================================================================")

    coords_3d = {
        "S": [0.0, 0.0, 15.0],
        "A": [-5.0, -5.0, 0.0],
        "B": [5.0, -5.0, 0.0],
        "C": [5.0, 5.0, 0.0],
        "D": [-5.0, 5.0, 0.0],
        "O": [0.0, 0.0, 0.0],
    }
    engine_mock = {
        "solids": [{"type": "pyramid", "apex": "S", "base": ["A", "B", "C", "D"], "points": ["S", "A", "B", "C", "D"]}],
        "drawing_phases": [
            {"phase": 1, "label": "Hình cơ bản", "points": ["A", "B", "C", "D"], "segments": [["A", "B"], ["B", "C"], ["C", "D"], ["D", "A"]]},
            {"phase": 2, "label": "Điểm và đoạn phụ", "points": ["S", "O"], "segments": [["S", "A"], ["S", "B"], ["S", "C"], ["S", "D"]]},
        ],
    }
    steps = [
        "Bước 1: Tính diện tích đáy ABCD là hình vuông: S = 10^2 = 100.",
        "Bước 2: Xác định chiều cao SO = 15.",
        "Bước 3: Áp dụng công thức thể tích khối chóp V = (1/3) * 100 * 15 = 500.",
    ]

    spec = build_visualization_spec(
        problem_text="Cho hình chóp S.ABCD có đáy ABCD là hình vuông cạnh 10, SO=15. Tính thể tích khối chóp.",
        solution_steps=steps,
        coordinates=coords_3d,
        engine_result=engine_mock,
        is_3d=True,
    )

    prompt = spec.to_prompt()
    logger.info(f"✅ Spec built successfully with {len(spec.geometry)} geometry objects and {len(spec.animations)} animation beats.")
    logger.info(f"Generated Spec Prompt preview:\n{prompt[:300]}...\n")
    assert len(spec.geometry) >= 6, "Missing geometry points"
    assert len(spec.animations) >= 3, "Missing animation beats"
    assert spec.output_config.quality == "720p"
    return spec


async def test_manim_client_offline_resilience(spec: VisualizationSpec):
    logger.info("================================================================================")
    logger.info("🧪 TEST 2: ManimClient Resilience & Contract Handling")
    logger.info("================================================================================")

    # Test with standard config
    client = ManimClient()
    resp = await client.submit_render_job(spec)
    logger.info(f"Manim service response: job_id={resp.job_id}, status={resp.status}, error={resp.error}")
    assert resp.status in ("queued", "generating", "rendering", "completed", "failed"), "Invalid status"
    logger.info("✅ ManimClient handled external API submission gracefully without throwing unhandled exceptions.")


async def test_e2e_orchestrator_integration():
    logger.info("================================================================================")
    logger.info("🧪 TEST 3: Full E2E Pipeline (OCR/Problem -> Solver -> VisualizationSpec -> Manim)")
    logger.info("================================================================================")

    problem = "Cho hình chóp S.ABCD có đáy ABCD là hình vuông cạnh 10. Chiều cao SO vuông góc với đáy tại tâm O, SO=15. Tính thể tích khối chóp S.ABCD."
    orchestrator = Orchestrator()

    res = await orchestrator.run(
        text=problem,
        job_id="test_manim_e2e",
        generate_video=True,
    )

    logger.info(f"Pipeline Result Status: {res.get('status')}")
    logger.info(f"Answer: {res.get('solution', {}).get('answer')}")
    viz = res.get("visualization")
    logger.info(f"Visualization Section Present: {viz is not None}")
    if viz:
        logger.info(f"  - Job ID: {viz.get('job_id')}")
        logger.info(f"  - Status: {viz.get('status')}")
        logger.info(f"  - Spec Problem: {viz.get('spec', {}).get('problem')}")
        logger.info(f"  - Animation beats: {len(viz.get('spec', {}).get('animations', []))}")
        logger.info(f"  - Geometry objects: {len(viz.get('spec', {}).get('geometry', []))}")

    assert res.get("status") == "success"
    assert viz is not None
    assert viz.get("spec") is not None
    logger.info("✅ E2E Manim Integration Test Succeeded 100%!")


async def main():
    spec = await test_visualization_spec_building()
    await test_manim_client_offline_resilience(spec)
    await test_e2e_orchestrator_integration()
    logger.info("\n🎉 ALL MANIM INTEGRATION TESTS PASSED!")


if __name__ == "__main__":
    asyncio.run(main())
