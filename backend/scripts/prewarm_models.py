#!/usr/bin/env python3
"""
Download and load all heavy models during Docker build (YOLO, PaddleOCR, Pix2Tex, agents).
Fails the image build if initialization fails.
"""

from __future__ import annotations

import logging
import os
import sys

# Ensure imports work when run as `python scripts/prewarm_models.py` from WORKDIR
_APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _APP_ROOT not in sys.path:
    sys.path.insert(0, _APP_ROOT)

os.chdir(_APP_ROOT)

from dotenv import load_dotenv

load_dotenv()

from app.runtime_env import apply_runtime_env_defaults

apply_runtime_env_defaults()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s | %(message)s")

logger = logging.getLogger("prewarm")


def main() -> None:
    from agents.orchestrator import Orchestrator

    logger.info("Constructing Orchestrator (full agent + model load)...")
    Orchestrator()
    logger.info("Prewarm finished successfully.")


if __name__ == "__main__":
    main()
