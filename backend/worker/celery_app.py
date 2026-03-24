import os
from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# For Upstash (rediss://), we need to ensure SSL settings if needed
celery_app = Celery(
    "math_solver",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["worker.tasks"]
)

# Fix for Upstash SSL context if using rediss://
if REDIS_URL.startswith("rediss://"):
    celery_app.conf.broker_use_ssl = {
        'ssl_cert_reqs': 'none' # Upstash handles SSL, this avoids local cert issues
    }
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
