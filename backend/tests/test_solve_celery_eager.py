"""Smoke: solve Celery task with eager mode and mocked DB + orchestrator."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from worker.celery_app import celery_app


@pytest.fixture
def celery_eager_on():
    prev_eager = celery_app.conf.task_always_eager
    prev_prop = celery_app.conf.task_eager_propagates
    celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
    yield
    celery_app.conf.update(
        task_always_eager=prev_eager, task_eager_propagates=prev_prop
    )


def _fake_supabase():
    supabase = MagicMock()

    def table(name):
        m = MagicMock()
        if name == "messages":
            m.select.return_value.eq.return_value.order.return_value.execute.return_value.data = []
            m.insert.return_value.execute.return_value = MagicMock()
        elif name == "jobs":
            m.update.return_value.eq.return_value.execute.return_value = MagicMock()
        return m

    supabase.table.side_effect = table
    return supabase


def test_process_solve_session_job_eager_smoke(monkeypatch, celery_eager_on):
    from app import websocket_manager
    from app.jobs import solve_session_job
    from worker.tasks import process_solve_session_job

    orch = MagicMock()
    orch.run = AsyncMock(
        return_value={
            "status": "success",
            "semantic_analysis": "done",
            "coordinates": {},
            "geometry_dsl": None,
            "polygon_order": [],
            "drawing_phases": [],
            "circles": [],
            "lines": [],
            "rays": [],
            "solution": "x",
            "is_3d": False,
        }
    )
    monkeypatch.setattr(solve_session_job, "get_job_orchestrator", lambda: orch)
    monkeypatch.setattr(solve_session_job, "get_supabase", _fake_supabase)
    monkeypatch.setattr(solve_session_job, "publish_job_ws_event", lambda _jid, _data: False)
    monkeypatch.setattr(websocket_manager, "notify_status", AsyncMock())

    r = process_solve_session_job.apply_async(
        args=["job-eager-1", "session-1", "user-1", "1+1", None],
        queue="solve",
    )
    assert r.successful()
