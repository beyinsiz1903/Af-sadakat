"""Async TTL cache layer for OmniHub.

Drop-in interface compatible with Redis (get/setex/delete) so we can later
swap to redis.asyncio with one line. For now uses an in-process async dict
with TTL — eliminates the ~700ms MongoDB Atlas RTT for hot analytics paths.

Usage:
    from core.cache import cached_or_fetch

    @router.get("/foo")
    async def foo(tenant_slug: str):
        return await cached_or_fetch(
            f"foo:{tenant_slug}",
            ttl=60,
            fetcher=lambda: _build_foo(tenant_slug),
        )
"""
import asyncio
import json
import logging
import time
from typing import Any, Awaitable, Callable, Optional

logger = logging.getLogger("omnihub.cache")

_store: dict[str, tuple[float, str]] = {}
_lock = asyncio.Lock()
_singleflight: dict[str, asyncio.Future] = {}

_hits = 0
_misses = 0


async def get(key: str) -> Optional[Any]:
    global _hits, _misses
    entry = _store.get(key)
    if entry is None:
        _misses += 1
        return None
    expires_at, payload = entry
    if expires_at < time.monotonic():
        _store.pop(key, None)
        _misses += 1
        return None
    _hits += 1
    try:
        return json.loads(payload)
    except (ValueError, TypeError):
        _store.pop(key, None)
        return None


async def setex(key: str, ttl: int, value: Any) -> None:
    try:
        payload = json.dumps(value, default=str)
    except (TypeError, ValueError) as e:
        logger.warning("cache: cannot serialize key=%s err=%s", key, e)
        return
    _store[key] = (time.monotonic() + ttl, payload)


async def delete(*keys: str) -> int:
    removed = 0
    for k in keys:
        if _store.pop(k, None) is not None:
            removed += 1
    return removed


async def delete_prefix(prefix: str) -> int:
    """Invalidate all keys starting with prefix (used after writes)."""
    targets = [k for k in list(_store.keys()) if k.startswith(prefix)]
    for k in targets:
        _store.pop(k, None)
    return len(targets)


async def clear() -> None:
    _store.clear()


def stats() -> dict:
    total = _hits + _misses
    return {
        "hits": _hits,
        "misses": _misses,
        "hit_rate": round(_hits / total * 100, 2) if total else 0.0,
        "size": len(_store),
    }


async def cached_or_fetch(
    key: str,
    ttl: int,
    fetcher: Callable[[], Awaitable[Any]],
) -> Any:
    """Get from cache or run fetcher; concurrent calls for the same key
    share one underlying fetch (single-flight) to prevent thundering herd."""
    cached = await get(key)
    if cached is not None:
        return cached

    # Single-flight: if another coroutine is already fetching, await its result.
    async with _lock:
        existing = _singleflight.get(key)
        if existing is not None:
            future = existing
            owner = False
        else:
            future = asyncio.get_event_loop().create_future()
            _singleflight[key] = future
            owner = True

    if not owner:
        return await future

    try:
        value = await fetcher()
        await setex(key, ttl, value)
        if not future.done():
            future.set_result(value)
        return value
    except BaseException as e:
        # Catch BaseException (incl. CancelledError) so waiters never hang.
        if not future.done():
            future.set_exception(e if isinstance(e, Exception) else RuntimeError("fetcher cancelled"))
        raise
    finally:
        async with _lock:
            _singleflight.pop(key, None)
