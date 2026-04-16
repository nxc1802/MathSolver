#!/usr/bin/env python3
"""Docker build: load geometry_render only (no Orchestrator / no LLM / no OCR)."""

from __future__ import annotations

import logging
import os
import subprocess
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
logger = logging.getLogger("prewarm_render_worker")


def main() -> None:
    from geometry_render.renderer import RendererAgent

    logger.info("Loading RendererAgent (geometry_render only)...")
    RendererAgent()
    try:
        r = subprocess.run(
            ["manim", "--version"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if r.returncode == 0:
            logger.info("manim --version: %s", (r.stdout or r.stderr or "").strip()[:200])
        else:
            logger.warning("manim --version failed rc=%s", r.returncode)
    except FileNotFoundError:
        logger.warning("manim CLI not found on PATH (skipping version check).")
    except subprocess.TimeoutExpired:
        logger.warning("manim --version timed out.")

    logger.info("Render worker prewarm finished successfully.")


if __name__ == "__main__":
    main()
