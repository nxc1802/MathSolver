import os
from celery import Celery
from dotenv import load_dotenv

from app.url_utils import sanitize_env

# Load environment variables early
load_dotenv()

from app.runtime_env import apply_runtime_env_defaults

apply_runtime_env_defaults()

from app.logging_setup import setup_application_logging

setup_application_logging()


def _celery_include_modules() -> list[str]:
    """
    Load only task modules for queues this process consumes (see CELERY_WORKER_QUEUES).
    OCR-only Spaces must not import worker.tasks (Manim / Supabase render path).
    """
    raw = (os.getenv("CELERY_WORKER_QUEUES") or "").strip().lower()
    if not raw:
        return ["worker.tasks", "worker.ocr_tasks"]
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        mod = None
        if p == "render":
            mod = "worker.tasks"
        elif p == "ocr":
            mod = "worker.ocr_tasks"
        if mod and mod not in seen:
            seen.add(mod)
            out.append(mod)
    return out if out else ["worker.tasks", "worker.ocr_tasks"]


_broker_raw = os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL") or "redis://localhost:6379/0"
_backend_raw = os.getenv("CELERY_RESULT_BACKEND") or os.getenv("REDIS_URL") or "redis://localhost:6379/1"

BROKER_URL = sanitize_env(_broker_raw) or _broker_raw.strip()
RESULT_BACKEND = sanitize_env(_backend_raw) or _backend_raw.strip()

celery_app = Celery(
    "math_solver",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=_celery_include_modules(),
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
    task_routes={
        "worker.tasks.render_geometry_video": {"queue": "render"},
        "worker.ocr_tasks.run_ocr_from_url": {"queue": "ocr"},
    },
)
