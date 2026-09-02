"""Normalize Supabase `jobs` rows for polling / WebSocket clients (stable `job_id` + JSON `result`)."""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _coerce_result(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            logger.warning("job_poll: result is non-JSON string, returning raw")
            return {"raw": value}
    return value


from app.models.job_state import JobStateMachine, JobStatus, STAGE_PROGRESS_MAP, JobStage


def normalize_job_row_for_client(row: dict[str, Any]) -> dict[str, Any]:
    """
    Build a JSON-serializable dict that conforms to P1 Job State Machine:
    - ``job_id`` (alias of DB ``id``)
    - ``status`` normalized (e.g. 'processing', 'completed', 'failed', 'queued')
    - ``stage`` extracted from row or inferred (e.g. 'ocr', 'parsing', 'geometry', 'solving', 'rendering')
    - ``progress`` integer 0-100
    - ``result`` object/array
    All other columns are passed through cleanly.
    """
    out = dict(row)
    jid = out.get("id")
    if jid is not None:
        out["job_id"] = str(jid)
    
    st_raw = out.get("status")
    normalized_status = JobStateMachine.normalize_status(st_raw)
    out["status"] = normalized_status.value

    # Extract or infer stage
    stage_raw = out.get("stage")
    normalized_stage = JobStateMachine.normalize_stage(stage_raw)
    if not normalized_stage and normalized_status == JobStatus.PROCESSING:
        if st_raw in ("ocr", "parsing", "geometry", "solving", "rendering"):
            normalized_stage = JobStage(st_raw)
    
    out["stage"] = normalized_stage.value if normalized_stage else None

    # Calculate or normalize progress
    if "progress" in out and out["progress"] is not None:
        try:
            out["progress"] = int(out["progress"])
        except (ValueError, TypeError):
            out["progress"] = STAGE_PROGRESS_MAP.get(normalized_stage, 50) if normalized_stage else (100 if normalized_status == JobStatus.COMPLETED else 0)
    else:
        if normalized_status == JobStatus.COMPLETED:
            out["progress"] = 100
        elif normalized_status == JobStatus.QUEUED:
            out["progress"] = 5
        elif normalized_stage and normalized_stage in STAGE_PROGRESS_MAP:
            out["progress"] = STAGE_PROGRESS_MAP[normalized_stage]
        elif normalized_status == JobStatus.PROCESSING:
            out["progress"] = 50
        else:
            out["progress"] = 0

    if "result" in out:
        out["result"] = _coerce_result(out.get("result"))
    if out.get("user_id") is not None:
        out["user_id"] = str(out["user_id"])
    if out.get("session_id") is not None:
        out["session_id"] = str(out["session_id"])
    return out

