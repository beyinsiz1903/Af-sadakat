"""Cache layer tests — covers TTL, single-flight, prefix invalidation."""
import asyncio
import pytest

from core import cache


@pytest.mark.asyncio
async def test_setex_get_roundtrip():
    await cache.setex("test:roundtrip", 5, {"a": 1, "b": "x"})
    got = await cache.get("test:roundtrip")
    assert got == {"a": 1, "b": "x"}


@pytest.mark.asyncio
async def test_get_returns_none_for_missing():
    got = await cache.get("test:does-not-exist:xyz")
    assert got is None


@pytest.mark.asyncio
async def test_delete_prefix_removes_matching():
    await cache.setex("test:px:1", 30, 1)
    await cache.setex("test:px:2", 30, 2)
    await cache.setex("test:other", 30, 3)
    removed = await cache.delete_prefix("test:px:")
    assert removed >= 2
    assert await cache.get("test:px:1") is None
    assert await cache.get("test:other") == 3
    await cache.delete("test:other")


@pytest.mark.asyncio
async def test_cached_or_fetch_single_flight():
    calls = {"n": 0}

    async def fetcher():
        calls["n"] += 1
        await asyncio.sleep(0.05)
        return {"v": 42}

    results = await asyncio.gather(*[
        cache.cached_or_fetch("test:sf", 10, fetcher) for _ in range(5)
    ])
    assert all(r == {"v": 42} for r in results)
    assert calls["n"] == 1
    await cache.delete("test:sf")


def test_stats_shape():
    s = cache.stats()
    assert "backend" in s and "hits" in s and "misses" in s
