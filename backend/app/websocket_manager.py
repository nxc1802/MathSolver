"""WebSocket connection registry and job status notifications (avoid circular imports with main)."""

from __future__ import annotations

import logging
from typing import Dict, List

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

active_connections: Dict[str, List[WebSocket]] = {}


from app.models.job_state import JobStateMachine, STAGE_PROGRESS_MAP, JobStatus


async def notify_status(job_id: str, data: dict) -> None:
    if job_id not in active_connections:
        return
    
    # Normalize payload
    payload = dict(data)
    payload["job_id"] = str(job_id)
    if "status" in payload:
        norm_status = JobStateMachine.normalize_status(payload.get("status"))
        norm_stage = JobStateMachine.normalize_stage(payload.get("stage"))
        if not norm_stage and payload.get("status") in ("ocr", "parsing", "geometry", "solving", "rendering"):
            norm_stage = JobStateMachine.normalize_stage(payload.get("status"))

        payload["status"] = norm_status.value
        payload["stage"] = norm_stage.value if norm_stage else None
        
        if "progress" not in payload or payload["progress"] is None:
            if norm_status == JobStatus.COMPLETED:
                payload["progress"] = 100
            elif norm_stage and norm_stage in STAGE_PROGRESS_MAP:
                payload["progress"] = STAGE_PROGRESS_MAP[norm_stage]
            elif norm_status == JobStatus.QUEUED:
                payload["progress"] = 5
            elif norm_status == JobStatus.PROCESSING:
                payload["progress"] = 50

    for connection in list(active_connections[job_id]):
        try:
            await connection.send_json(payload)
        except Exception as e:
            logger.warning("WS error sending to %s: %s (removing dead connection)", job_id, e)
            try:
                active_connections[job_id].remove(connection)
            except (ValueError, KeyError):
                pass
    if job_id in active_connections and not active_connections[job_id]:
        del active_connections[job_id]



def register_websocket_routes(app) -> None:
    """Attach websocket endpoint to the FastAPI app."""

    @app.websocket("/ws/{job_id}")
    async def websocket_endpoint(websocket: WebSocket, job_id: str) -> None:
        await websocket.accept()
        if job_id not in active_connections:
            active_connections[job_id] = []
        active_connections[job_id].append(websocket)

        # Send immediate ACK so client immediately transitions from 'connecting' to 'processing'
        try:
            await websocket.send_json({
                "status": "processing",
                "job_id": job_id,
                "message": "Đang xử lý bài toán..."
            })
        except Exception:
            pass

        try:
            while True:
                msg = await websocket.receive_text()
                if msg == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            if job_id in active_connections and websocket in active_connections[job_id]:
                active_connections[job_id].remove(websocket)
                if not active_connections[job_id]:
                    del active_connections[job_id]
