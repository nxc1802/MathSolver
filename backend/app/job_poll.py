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


def normalize_job_row_for_client(row: dict[str, Any]) -> dict[str, Any]:
    """
    Build a JSON-serializable dict that always includes:
    - ``job_id`` (alias of DB ``id``) for clients that expect it on poll bodies
    - ``status`` as str
    - ``result`` as object/array when stored as JSON string
    All other columns are passed through (UUID/datetime become JSON-safe via FastAPI encoder).
    """
    out = dict(row)
    jid = out.get("id")
    if jid is not None:
        out["job_id"] = str(jid)
    st = out.get("status")
    if st is not None:
        out["status"] = str(st)
    if "result" in out:
        out["result"] = _coerce_result(out.get("result"))
    if out.get("user_id") is not None:
        out["user_id"] = str(out["user_id"])
    if out.get("session_id") is not None:
        out["session_id"] = str(out["session_id"])
    return out
