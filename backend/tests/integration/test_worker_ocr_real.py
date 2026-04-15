"""Celery OCR task against a public image URL (opt-in)."""

from __future__ import annotations

import os

import pytest


@pytest.mark.real_worker_ocr
def test_run_ocr_from_url_celery_task():
    if os.getenv("RUN_REAL_WORKER_OCR", "").lower() not in ("1", "true", "yes"):
        pytest.skip("Set RUN_REAL_WORKER_OCR=1 to run OCR worker integration")

    if not (os.getenv("CELERY_BROKER_URL") or os.getenv("REDIS_URL")):
        pytest.skip("CELERY_BROKER_URL or REDIS_URL required for Celery")

    from worker.ocr_tasks import run_ocr_from_url

    url = os.getenv(
        "TEST_OCR_IMAGE_URL",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/280px-PNG_transparency_demonstration_1.png",
    )
    # .run() executes the task body in-process (same code path as the worker).
    text = run_ocr_from_url.run(url)
    assert isinstance(text, str)
