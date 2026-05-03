"""Smoke test against the live backend (requires server running on :8000)."""
import os
import pytest
import httpx

BASE = os.environ.get("OMNIHUB_BASE", "http://localhost:8000")


@pytest.mark.asyncio
async def test_health_ok():
    async with httpx.AsyncClient(timeout=5.0) as c:
        try:
            r = await c.get(f"{BASE}/api/health")
        except httpx.ConnectError:
            pytest.skip("backend not running")
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_login_invalid_credentials_429_or_401():
    async with httpx.AsyncClient(timeout=5.0) as c:
        try:
            r = await c.post(f"{BASE}/api/auth/login",
                             json={"email": "nobody@example.com", "password": "x"})
        except httpx.ConnectError:
            pytest.skip("backend not running")
    assert r.status_code in (401, 429)
