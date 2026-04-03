"""Logging theo một biến LOG_LEVEL: debug | info | warning | error."""

from __future__ import annotations

import logging
import os
from typing import Final

_SETUP_DONE = False

PIPELINE_LOGGER_NAME: Final = "app.pipeline"
CACHE_LOGGER_NAME: Final = "app.cache"
STEPS_LOGGER_NAME: Final = "app.steps"
ACCESS_LOGGER_NAME: Final = "app.access"


def _normalize_level() -> str:
    raw = os.getenv("LOG_LEVEL", "info").strip().lower()
    if raw in ("debug", "info", "warning", "error"):
        return raw
    return "info"


def setup_application_logging() -> None:
    """Idempotent; gọi khi khởi động process (uvicorn, celery, worker_health)."""
    global _SETUP_DONE
    if _SETUP_DONE:
        return
    _SETUP_DONE = True

    mode = _normalize_level()

    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "error": logging.ERROR,
    }
    root_level = level_map[mode]

    fmt_named = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    fmt_short = "%(asctime)s | %(levelname)-8s | %(message)s"

    logging.basicConfig(
        level=root_level,
        format=fmt_named if mode == "debug" else fmt_short,
        datefmt="%H:%M:%S",
        force=True,
    )

    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    # HTTP/2 stack (httpx/httpcore) — khi LOG_LEVEL=debug root=DEBUG sẽ tràn log hpack; không cần cho debug app
    for _name in ("hpack", "h2", "hyperframe", "urllib3"):
        logging.getLogger(_name).setLevel(logging.WARNING)

    if mode == "debug":
        logging.getLogger("agents").setLevel(logging.DEBUG)
        logging.getLogger("solver").setLevel(logging.DEBUG)
        logging.getLogger("app.routers").setLevel(logging.DEBUG)
        logging.getLogger(CACHE_LOGGER_NAME).setLevel(logging.DEBUG)
        logging.getLogger(STEPS_LOGGER_NAME).setLevel(logging.DEBUG)
        logging.getLogger(PIPELINE_LOGGER_NAME).setLevel(logging.INFO)
        logging.getLogger(ACCESS_LOGGER_NAME).setLevel(logging.INFO)
        logging.getLogger("app.main").setLevel(logging.INFO)
        logging.getLogger("worker").setLevel(logging.INFO)
    elif mode == "info":
        # Chỉ HTTP access (app.access) + startup; ẩn chi tiết agents/orchestrator/pipeline SUCCESS
        logging.getLogger("agents").setLevel(logging.WARNING)
        logging.getLogger("solver").setLevel(logging.WARNING)
        logging.getLogger("app.routers").setLevel(logging.WARNING)
        logging.getLogger(CACHE_LOGGER_NAME).setLevel(logging.WARNING)
        logging.getLogger(STEPS_LOGGER_NAME).setLevel(logging.WARNING)
        logging.getLogger(PIPELINE_LOGGER_NAME).setLevel(logging.WARNING)
        logging.getLogger(ACCESS_LOGGER_NAME).setLevel(logging.INFO)
        logging.getLogger("app.main").setLevel(logging.INFO)
        logging.getLogger("worker").setLevel(logging.WARNING)
    elif mode == "warning":
        logging.getLogger("agents").setLevel(logging.WARNING)
        logging.getLogger("solver").setLevel(logging.WARNING)
        logging.getLogger("app.routers").setLevel(logging.WARNING)
        logging.getLogger(CACHE_LOGGER_NAME).setLevel(logging.WARNING)
        logging.getLogger(STEPS_LOGGER_NAME).setLevel(logging.WARNING)
        logging.getLogger(PIPELINE_LOGGER_NAME).setLevel(logging.WARNING)
        logging.getLogger(ACCESS_LOGGER_NAME).setLevel(logging.WARNING)
        logging.getLogger("app.main").setLevel(logging.WARNING)
        logging.getLogger("worker").setLevel(logging.WARNING)
    else:  # error
        logging.getLogger("agents").setLevel(logging.ERROR)
        logging.getLogger("solver").setLevel(logging.ERROR)
        logging.getLogger("app.routers").setLevel(logging.ERROR)
        logging.getLogger(CACHE_LOGGER_NAME).setLevel(logging.ERROR)
        logging.getLogger(STEPS_LOGGER_NAME).setLevel(logging.ERROR)
        logging.getLogger(PIPELINE_LOGGER_NAME).setLevel(logging.ERROR)
        logging.getLogger(ACCESS_LOGGER_NAME).setLevel(logging.ERROR)
        logging.getLogger("app.main").setLevel(logging.ERROR)
        logging.getLogger("worker").setLevel(logging.ERROR)

    logging.getLogger(__name__).debug(
        "LOG_LEVEL=%s root=%s", mode, logging.getLevelName(root_level)
    )


def get_log_level() -> str:
    return _normalize_level()


def is_debug_level() -> bool:
    return _normalize_level() == "debug"
