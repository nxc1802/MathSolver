"""In-process orchestrator smoke (2 queries) — same stack as API without HTTP."""

from __future__ import annotations

import os
import uuid

import pytest

from tests.cases.pipeline_cases import QUERIES


def _openrouter_configured() -> bool:
    return bool(os.getenv("OPENROUTER_API_KEY_1") or os.getenv("OPENROUTER_API_KEY"))


@pytest.mark.orchestrator_local
@pytest.mark.real_agents
@pytest.mark.asyncio
async def test_orchestrator_two_queries_smoke():
    if not _openrouter_configured():
        pytest.skip("OPENROUTER_API_KEY_1 or OPENROUTER_API_KEY not set")

    from agents.orchestrator import Orchestrator

    orch = Orchestrator()
    # Avoid Q1-style rectangles first: LLM sometimes returns prose instead of DSL.
    stable_ids = ("Q5", "Q2")
    by_id = {q["id"]: q for q in QUERIES}
    for qid in stable_ids:
        q = by_id[qid]
        jid = str(uuid.uuid4())
        result = await orch.run(text=q["text"], job_id=jid)
        assert "error" not in result, f"{qid}: {result.get('error')}"
        assert result.get("coordinates"), f"No coordinates for {qid}"
