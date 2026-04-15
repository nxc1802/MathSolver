"""Smoke tests for individual agents against real LLM / rules (opt-in via markers)."""

from __future__ import annotations

import os

import pytest

from agents.geometry_agent import GeometryAgent
from agents.knowledge_agent import KnowledgeAgent
from agents.parser_agent import ParserAgent
from agents.solver_agent import SolverAgent
from solver.dsl_parser import DSLParser


def _openrouter_configured() -> bool:
    return bool(os.getenv("OPENROUTER_API_KEY_1") or os.getenv("OPENROUTER_API_KEY"))


@pytest.mark.real_agents
@pytest.mark.asyncio
async def test_parser_agent_real():
    if not _openrouter_configured():
        pytest.skip("OPENROUTER_API_KEY_1 or OPENROUTER_API_KEY not set")
    agent = ParserAgent()
    out = await agent.process("Cho hình vuông ABCD có cạnh bằng 4.")
    assert isinstance(out, dict)
    assert out.get("type") in (None, "square", "rectangle", "general")
    assert "entities" in out


@pytest.mark.real_agents
@pytest.mark.asyncio
async def test_geometry_agent_real():
    if not _openrouter_configured():
        pytest.skip("OPENROUTER_API_KEY_1 or OPENROUTER_API_KEY not set")
    agent = GeometryAgent()
    semantic = {
        "type": "square",
        "values": {"side": 4},
        "entities": ["A", "B", "C", "D"],
        "analysis": "Hình vuông ABCD cạnh 4",
        "input_text": "Cho hình vuông ABCD cạnh 4",
        "target_question": None,
    }
    dsl = await agent.generate_dsl(semantic, previous_dsl=None)
    assert isinstance(dsl, str) and len(dsl) > 10
    parser = DSLParser()
    try:
        points, _constraints, _is_3d = parser.parse(dsl)
    except Exception as e:
        pytest.fail(f"GeometryAgent output is not parseable DSL: {e}\n---\n{dsl[:800]}")
    assert len(points) >= 1, "Expected at least one point from Geometry DSL"


@pytest.mark.real_agents
@pytest.mark.asyncio
async def test_solver_agent_real():
    if not _openrouter_configured():
        pytest.skip("OPENROUTER_API_KEY_1 or OPENROUTER_API_KEY not set")
    agent = SolverAgent()
    semantic = {
        "target_question": "Tính diện tích hình vuông ABCD.",
        "input_text": "Hình vuông cạnh 4",
    }
    engine_result = {
        "coordinates": {
            "A": [0.0, 0.0, 0.0],
            "B": [4.0, 0.0, 0.0],
            "C": [4.0, 4.0, 0.0],
            "D": [0.0, 4.0, 0.0],
        }
    }
    sol = await agent.solve(semantic, engine_result)
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
