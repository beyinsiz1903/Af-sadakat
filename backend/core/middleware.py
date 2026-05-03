"""Property middleware + Request ID middleware + observability helpers.
Sprint 6: Production hardening infrastructure.
"""
import uuid
import time
import re
import logging
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

import jwt as _jwt
from core.config import db, JWT_SECRET

logger = logging.getLogger("omnihub.middleware")


# ============ TENANT ISOLATION MIDDLEWARE ============
# Fail-closed: any /api/.../tenants/{slug}/... endpoint REQUIRES a valid bearer
# token whose tenant_id matches the slug's tenant.
# Cache: 60s TTL with negative-cache to avoid stale slug->tid mappings on rename/delete.
_slug_to_tid_cache: dict = {}
_CACHE_TTL_SECONDS = 60

def invalidate_tenant_cache(slug: str | None = None):
    """Invalidate slug->tenant_id cache (call after tenant rename/delete)."""
    if slug is None:
        _slug_to_tid_cache.clear()
    else:
        _slug_to_tid_cache.pop(slug, None)

class TenantIsolationMiddleware(BaseHTTPMiddleware):
    """Block cross-tenant access by validating JWT tenant_id against URL slug.
    Fail-closed: returns 401/403 unless a valid token's tenant_id matches the slug.
    """
    SKIP_PREFIXES = (
        "/api/auth/", "/api/g/", "/api/guest/", "/api/health", "/api/system/",
        "/api/seed", "/api/demo/", "/api/r/", "/api/rbac/", "/api/plans",
        "/api/integrations/syroce", "/api/admin/integrations/",
        "/api/billing/webhook", "/api/v2/payments/pay/", "/api/v2/payments/webhook/",
        "/api/v2/payments/config", "/api/v2/storage/config", "/api/v2/pms/providers",
        "/api/v2/webhooks/", "/api/v2/integrations/meta/oauth/",
        "/api/v2/uploads/g/", "/api/v2/uploads/files/", "/api/payments/mock/",
        "/api/compliance/retention-cleanup", "/sso/", "/docs", "/openapi.json", "/redoc",
    )
    GUEST_PATH_RE = re.compile(r"/g/[^/]+/")
    SLUG_RE = re.compile(r"/tenants/([a-zA-Z0-9][a-zA-Z0-9_\-]*)(?:/|$)")

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in self.SKIP_PREFIXES):
            return await call_next(request)
        if self.GUEST_PATH_RE.search(path):
            return await call_next(request)
        m = self.SLUG_RE.search(path)
        if not m:
            return await call_next(request)

        slug = m.group(1).lower()
        auth = request.headers.get("authorization", "")
        if not auth.lower().startswith("bearer "):
            return JSONResponse({"detail": "Authentication required"}, status_code=401)
        token = auth[7:].strip()
        try:
            payload = _jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except Exception:
            return JSONResponse({"detail": "Invalid or expired token"}, status_code=401)
        token_tid = payload.get("tenant_id")
        if not token_tid:
            return JSONResponse({"detail": "Token missing tenant_id"}, status_code=401)

        # Resolve slug->tenant_id with TTL cache (fail-closed on lookup failure)
        now = time.time()
        cached = _slug_to_tid_cache.get(slug)
        target_tid = None
        if cached and (now - cached[1]) < _CACHE_TTL_SECONDS:
            target_tid = cached[0]
        else:
            try:
                doc = await db.tenants.find_one({"slug": slug}, {"id": 1, "_id": 0})
            except Exception as e:
                logger.error("Tenant lookup failed for slug=%s: %s", slug, e)
                return JSONResponse({"detail": "Tenant lookup unavailable"}, status_code=503)
            if not doc:
                _slug_to_tid_cache[slug] = (None, now)
                return JSONResponse({"detail": "Tenant not found"}, status_code=404)
            target_tid = doc["id"]
            _slug_to_tid_cache[slug] = (target_tid, now)

        if target_tid is None:
            return JSONResponse({"detail": "Tenant not found"}, status_code=404)
        if token_tid != target_tid:
            logger.warning("Cross-tenant access denied: user_tid=%s target_slug=%s target_tid=%s path=%s",
                          token_tid, slug, target_tid, path)
            return JSONResponse({"detail": "Cross-tenant access denied"}, status_code=403)
        return await call_next(request)

# ============ REQUEST ID MIDDLEWARE ============
class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique request_id to every request for tracing."""
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
        request.state.request_id = request_id
        start = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000, 1)
        response.headers["X-Request-Id"] = request_id
        # Structured log line
        tenant_id = getattr(request.state, "tenant_id", "-")
        property_id = getattr(request.state, "property_id", "-")
        logger.info(
            '{"request_id":"%s","method":"%s","path":"%s","status":%d,'
            '"duration_ms":%.1f,"tenant_id":"%s","property_id":"%s"}',
            request_id, request.method, request.url.path,
            response.status_code, duration_ms, tenant_id, property_id
        )
        return response


# ============ GLOBAL EXCEPTION HANDLER ============
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions, return clean JSON, log internally."""
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(
        "Unhandled exception request_id=%s path=%s: %s",
        request_id, request.url.path, str(exc), exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )


# ============ PROPERTY HEADER RESOLUTION ============
async def resolve_property_header(request: Request, tenant_id: str):
    """Read X-Property-Id header, validate it belongs to tenant, return property_id.
    If header missing, returns default property (first created, active).
    Sets request.state.property_id for logging.
    """
    prop_id = request.headers.get("X-Property-Id", "")
    if prop_id:
        prop = await db.properties.find_one(
            {"id": prop_id, "tenant_id": tenant_id}, {"_id": 0}
        )
        if not prop:
            raise HTTPException(
                status_code=400,
                detail=f"Property {prop_id} not found or does not belong to this tenant"
            )
        if not prop.get("is_active", True):
            raise HTTPException(status_code=400, detail="Property is inactive")
        request.state.property_id = prop_id
        return prop_id
    # Fallback: default property (oldest active)
    default = await db.properties.find_one(
        {"tenant_id": tenant_id, "is_active": True},
        {"_id": 0},
        sort=[("created_at", 1)]
    )
    pid = default["id"] if default else ""
    request.state.property_id = pid
    return pid


# ============ RATE LIMITER (generic) ============
_rate_buckets = defaultdict(list)

def check_rate_limit(key: str, max_requests: int, window_seconds: int):
    """Simple in-memory sliding window rate limiter."""
    now = time.time()
    bucket = _rate_buckets[key]
    _rate_buckets[key] = [t for t in bucket if now - t < window_seconds]
    if len(_rate_buckets[key]) >= max_requests:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
    _rate_buckets[key].append(now)


def rate_limit_ip(request: Request, max_requests: int = 30, window: int = 60):
    """Rate limit by client IP."""
    ip = request.client.host if request.client else "unknown"
    check_rate_limit(f"ip:{ip}:{request.url.path}", max_requests, window)


# ============ PII MASKING ============
def mask_pii(text: str) -> str:
    """Mask emails and phones in log strings."""
    text = re.sub(r'[\w.+-]+@[\w-]+\.[\w.-]+', '***@***.***', text)
    text = re.sub(r'\+?\d{10,15}', '****', text)
    return text


# ============ CONFIRMATION CODE GENERATOR ============
import secrets
import string

_B32_CHARS = string.ascii_uppercase + string.digits
_B32_CHARS = _B32_CHARS.replace("O", "").replace("I", "").replace("L", "")  # remove ambiguous

def generate_confirmation_code(property_prefix: str = "GHI") -> str:
    """Generate human-readable confirmation code: PREFIX-YYYYMM-XXXXXX"""
    from datetime import datetime, timezone
    month_str = datetime.now(timezone.utc).strftime("%Y%m")
    random_part = ''.join(secrets.choice(_B32_CHARS) for _ in range(6))
    return f"{property_prefix}-{month_str}-{random_part}"


async def generate_unique_confirmation_code(tenant_id: str, property_prefix: str = "GHI", max_retries: int = 5) -> str:
    """Generate a confirmation code and ensure uniqueness via DB check."""
    for _ in range(max_retries):
        code = generate_confirmation_code(property_prefix)
        existing = await db.reservations.find_one(
            {"tenant_id": tenant_id, "confirmation_code": code}
        )
        if not existing:
            return code
    # Fallback: append extra random chars
    code = generate_confirmation_code(property_prefix) + secrets.token_hex(2).upper()
    return code
