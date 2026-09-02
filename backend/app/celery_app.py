"""Celery Application configuration for asynchronous background worker jobs."""

from __future__ import annotations

import logging
import os
from celery import Celery

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL") or "redis://localhost:6379/0"

celery_app = Celery(
    "mathsolver_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["app.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=900,  # 15 minutes max
    task_soft_time_limit=840,
    worker_prefetch_multiplier=1,
    worker_concurrency=int(os.getenv("CELERY_CONCURRENCY", "4")),
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)


def is_celery_available() -> bool:
    """
    Check if Celery / Redis broker is configured and reachable.
    Returns False when running in minimal dev/test environments without Redis.
    """
    disable_celery = os.getenv("DISABLE_CELERY", "0").lower() in ("1", "true", "yes")
    if disable_celery:
        return False
    try:
        import redis
        client = redis.from_url(REDIS_URL, socket_connect_timeout=0.5, socket_timeout=0.5)
        client.ping()
        return True
    except Exception:
        return False
