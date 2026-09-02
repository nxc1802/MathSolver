"""Smoke tests for individual agents against real LLM / rules (opt-in via markers)."""

from __future__ import annotations

import os

import pytest

from agents.geometry_parser_agent import GeometryParserAgent
from agents.deepmath_solver_agent import DeepMathSolverAgent
from agents.knowledge_agent import KnowledgeAgent
from solver.dsl_parser import DSLParser


def _api_configured() -> bool:
    return bool(
        os.getenv("GOOGLE_API_KEY")
        or os.getenv("GEMINI_API_KEY")
        or os.getenv("OPENROUTER_API_KEY_1")
        or os.getenv("OPENROUTER_API_KEY")
    )


@pytest.mark.real_agents
@pytest.mark.asyncio
async def test_geometry_parser_agent_real():
    if not _api_configured():
        pytest.skip("No API key configured")
    agent = GeometryParserAgent()
    out = await agent.process("Cho hình vuông ABCD có cạnh bằng 4.")
    assert isinstance(out, dict)
    assert out.get("type") in (None, "square", "rectangle", "general")
    assert "geometry_dsl" in out
    dsl = out.get("geometry_dsl", "")
    if dsl:
        parser = DSLParser()
        try:
            points, _constraints, _is_3d = parser.parse(dsl)
        except Exception as e:
            pytest.fail(f"GeometryParserAgent DSL not parseable: {e}\n---\n{dsl[:800]}")
        assert len(points) >= 1, "Expected at least one point from Geometry DSL"


@pytest.mark.real_agents
@pytest.mark.asyncio
async def test_deepmath_solver_agent_real():
    if not _api_configured():
        pytest.skip("No API key configured")
    agent = DeepMathSolverAgent()
    sol = await agent.solve(
        problem_text="Cho hình vuông ABCD có cạnh bằng 4. Tính diện tích.",
        target_question="Tính diện tích hình vuông ABCD.",
        semantic_data={
            "type": "square",
            "values": {"AB": 4},
            "target_question": "Tính diện tích hình vuông ABCD.",
        },
        geometry_context={
            "coordinates": {
                "A": [0.0, 0.0, 0.0],
                "B": [4.0, 0.0, 0.0],
                "C": [4.0, 4.0, 0.0],
                "D": [0.0, 4.0, 0.0],
            }
        },
    )
    assert isinstance(sol, dict)
    assert "steps" in sol
    assert sol.get("answer") is not None or len(sol.get("steps") or []) > 0


def test_knowledge_agent_augment_semantic_data():
    """Rule-based augmentation; no API key required."""
    agent = KnowledgeAgent()
    data = {
        "type": "general",
        "values": {"AB": 5},
        "input_text": "Cho hình vuông ABCD có cạnh bằng 5.",
    }
    out = agent.augment_semantic_data(dict(data))
    assert out.get("type") == "square"
    assert out.get("values", {}).get("AB") == 5
