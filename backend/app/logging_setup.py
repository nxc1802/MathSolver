"""Application logging: APP_LOG_MODE=debug|production (default: production)."""

from __future__ import annotations

import logging
import os
from typing import Final

_SETUP_DONE = False

# Production: chỉ cần dòng kết quả trên logger này (SUCCESS/FAIL + operation)
PIPELINE_LOGGER_NAME: Final = "app.pipeline"
CACHE_LOGGER_NAME: Final = "app.cache"
STEPS_LOGGER_NAME: Final = "app.steps"


def setup_application_logging() -> None:
    """Idempotent; call once at process entry (uvicorn main, celery worker)."""
    global _SETUP_DONE
    if _SETUP_DONE:
        return
    _SETUP_DONE = True

    mode = os.getenv("APP_LOG_MODE", "production").strip().lower()
    if mode not in ("debug", "production"):
        mode = "production"

    default_level = os.getenv("LOG_LEVEL", "DEBUG" if mode == "debug" else "INFO").upper()
    root_level = getattr(logging, default_level, logging.INFO)

    fmt_full = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    fmt_short = "%(asctime)s | %(levelname)-8s | %(message)s"

    logging.basicConfig(
        level=root_level,
        format=fmt_full if mode == "debug" else fmt_short,
        datefmt="%H:%M:%S",
        force=True,
    )

    # Third-party: giảm ồn
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)

    if mode == "production":
        # Chi tiết agents/solver/routers -> WARNING; pipeline chỉ SUCCESS/FAIL
        logging.getLogger("agents").setLevel(logging.WARNING)
        logging.getLogger("solver").setLevel(logging.WARNING)
        logging.getLogger("app.routers").setLevel(logging.WARNING)
        logging.getLogger(CACHE_LOGGER_NAME).setLevel(logging.WARNING)
        logging.getLogger(STEPS_LOGGER_NAME).setLevel(logging.WARNING)
        logging.getLogger(PIPELINE_LOGGER_NAME).setLevel(logging.INFO)
        logging.getLogger("app.main").setLevel(logging.INFO)
        logging.getLogger("worker").setLevel(logging.WARNING)
    else:
        logging.getLogger("app").setLevel(logging.DEBUG)
        logging.getLogger("agents").setLevel(logging.DEBUG)
        logging.getLogger("solver").setLevel(logging.DEBUG)
        logging.getLogger(CACHE_LOGGER_NAME).setLevel(logging.DEBUG)
        logging.getLogger(STEPS_LOGGER_NAME).setLevel(logging.DEBUG)

    logging.getLogger(__name__).debug(
        "Logging mode=%s root_level=%s", mode, logging.getLevelName(root_level)
    )


def get_app_log_mode() -> str:
    return os.getenv("APP_LOG_MODE", "production").strip().lower()
