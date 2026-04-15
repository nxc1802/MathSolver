"""Cross-process job status: Redis pub so API WebSocket bridge can call notify_status."""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

CHANNEL = "mathsolver:job_events"


def _redis_url() -> str | None:
    raw = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL")
    return raw.strip() if raw else None


def job_ws_redis_bridge_enabled() -> bool:
    return os.getenv("JOB_WS_REDIS_BRIDGE", "true").lower() not in ("0", "false", "no")


def job_ws_bridge_should_start() -> bool:
    """Start API-side subscriber only when bridge is on and Redis URL is configured."""
    return job_ws_redis_bridge_enabled() and bool(_redis_url())


def publish_job_ws_event(job_id: str, data: Dict[str, Any]) -> bool:
    """
    Publish job status to Redis for the API subscriber to forward to WebSocket clients.
    Returns True if publish was attempted (subscriber should deliver to WS).
    Returns False if caller should fall back to in-process notify_status only.
    """
    if not job_ws_redis_bridge_enabled():
        return False
    url = _redis_url()
    if not url:
        return False
    try:
        import redis

        r = redis.Redis.from_url(url, decode_responses=True)
        try:
            r.publish(CHANNEL, json.dumps({"job_id": job_id, "data": data}, default=str))
        finally:
            r.close()
        return True
    except Exception:
        logger.exception("publish_job_ws_event failed for job_id=%s", job_id)
        return False


async def job_ws_bridge_loop() -> None:
    """
    Subscribe to Redis job events and forward to in-process WebSocket clients.
    Run as a background task on API startup when bridge + Redis URL are enabled.
    """
    import asyncio
    import json

    import redis.asyncio as aioredis

    from app.websocket_manager import notify_status

    url = _redis_url()
    if not url:
        logger.warning("job_ws_bridge_loop: no REDIS_URL, exiting")
        return

    client = aioredis.from_url(url, decode_responses=True)
    pubsub = client.pubsub()
    await pubsub.subscribe(CHANNEL)
    logger.info("job_ws_bridge_loop subscribed to %s", CHANNEL)
    try:
        while True:
            try:
                msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=30.0)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("job_ws_bridge_loop get_message error")
                await asyncio.sleep(1.0)
                continue
            if not msg or msg.get("type") != "message":
                continue
            try:
                body = json.loads(msg["data"])
                jid = body.get("job_id")
                data = body.get("data")
                if jid and isinstance(data, dict):
                    await notify_status(jid, data)
            except Exception:
                logger.exception("job_ws_bridge_loop handle message failed")
    finally:
        await pubsub.unsubscribe(CHANNEL)
        await pubsub.close()
        await client.aclose()
