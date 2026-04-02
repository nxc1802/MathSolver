"""WebSocket connection registry and job status notifications (avoid circular imports with main)."""

from __future__ import annotations

import logging
from typing import Dict, List

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

active_connections: Dict[str, List[WebSocket]] = {}


async def notify_status(job_id: str, data: dict) -> None:
    if job_id not in active_connections:
        return
    for connection in list(active_connections[job_id]):
        try:
            await connection.send_json(data)
        except Exception as e:
            logger.error("WS error sending to %s: %s", job_id, e)


def register_websocket_routes(app) -> None:
    """Attach websocket endpoint to the FastAPI app."""

    @app.websocket("/ws/{job_id}")
    async def websocket_endpoint(websocket: WebSocket, job_id: str) -> None:
        await websocket.accept()
        if job_id not in active_connections:
            active_connections[job_id] = []
        active_connections[job_id].append(websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            active_connections[job_id].remove(websocket)
            if not active_connections[job_id]:
                del active_connections[job_id]
