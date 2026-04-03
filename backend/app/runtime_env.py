"""Default process env vars (Paddle/OpenMP). Call as early as possible after load_dotenv."""

from __future__ import annotations

import os


def apply_runtime_env_defaults() -> None:
    # Quiets Paddle OMP warnings and avoids OpenMP thread oversubscription
    os.environ.setdefault("OMP_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
