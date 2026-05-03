"""Pytest fixtures for OmniHub backend.

Provides:
  - `client` (AsyncClient) for hitting the FastAPI app in-process
  - `auth_headers` for an authenticated admin token (requires running mongo)

Tests that only touch pure modules (cache, iyzico HMAC) don't need fixtures.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
