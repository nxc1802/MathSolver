import os
from celery import Celery
from dotenv import load_dotenv

from app.url_utils import sanitize_env

# Load environment variables early
load_dotenv()

from app.logging_setup import setup_application_logging

setup_application_logging()

_broker_raw = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or "redis://localhost:6379/0"
_backend_raw = os.getenv("CELERY_RESULT_BACKEND") or os.getenv("REDIS_URL") or "redis://localhost:6379/1"

BROKER_URL = sanitize_env(_broker_raw) or _broker_raw.strip()
RESULT_BACKEND = sanitize_env(_backend_raw) or _backend_raw.strip()

celery_app = Celery(
    "math_solver",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["worker.tasks"],
)

# Fix for SSL if using rediss://
if BROKER_URL.startswith("rediss://"):
    celery_app.conf.broker_use_ssl = {
        "ssl_cert_reqs": "none",
    }
if RESULT_BACKEND.startswith("rediss://"):
    celery_app.conf.redis_backend_use_ssl = {
        "ssl_cert_reqs": "none",
    }

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)
