#!/usr/bin/env python3
"""Docker build: load OCR models only (no Orchestrator / no LLM). Used by Dockerfile.worker.ocr."""

from __future__ import annotations

import logging
import os
import sys

_APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

os.chdir(_APP_ROOT)

from dotenv import load_dotenv

load_dotenv()

from app.runtime_env import apply_runtime_env_defaults

apply_runtime_env_defaults()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s | %(message)s")
logger = logging.getLogger("prewarm_ocr_worker")


def main() -> None:
    from agents.ocr_agent import OCRAgent

    logger.info("Loading OCRAgent(skip_llm_refinement=True)...")
    OCRAgent(skip_llm_refinement=True)
    logger.info("OCR worker prewarm finished successfully.")


if __name__ == "__main__":
    main()
