"""Default process env vars (Paddle/OpenMP). Call as early as possible after load_dotenv."""

from __future__ import annotations

import os


def apply_runtime_env_defaults() -> None:
    # Paddle respects OMP_NUM_THREADS at import; setdefault loses if platform already set 2+
    os.environ["OMP_NUM_THREADS"] = "1"
    os.environ["MKL_NUM_THREADS"] = "1"
    os.environ["OPENBLAS_NUM_THREADS"] = "1"
