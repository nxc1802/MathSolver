import os
from celery import Celery

BROKER_URL = os.getenv("CELERY_BROKER_URL", os.getenv("REDIS_URL", "redis://localhost:6379/0"))
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", os.getenv("REDIS_URL", "redis://localhost:6379/1"))

celery_app = Celery(
    "math_solver",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["worker.tasks"]
)

# Fix for SSL if using rediss://
if BROKER_URL.startswith("rediss://"):
    celery_app.conf.broker_use_ssl = {
        'ssl_cert_reqs': 'none'
    }
if RESULT_BACKEND.startswith("rediss://"):
    celery_app.conf.redis_backend_use_ssl = {
        'ssl_cert_reqs': 'none'
    }

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
