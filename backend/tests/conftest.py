"""Load backend/.env for all pytest runs so integration tests see credentials."""

from __future__ import annotations

import os

import pytest


def pytest_configure(config: pytest.Config) -> None:
    try:
        from dotenv import load_dotenv

        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        load_dotenv(os.path.join(root, ".env"), override=False)
    except Exception:
        pass
