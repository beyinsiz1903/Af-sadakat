"""Syroce PMS bi-directional integration:

- POST /api/admin/integrations/syroce/provision  : tenant + PMS config upsert
- GET  /sso/syroce?token=<JWT>                   : single sign-on landing
- Outbound webhook helper: fire_syroce_event(tenant_id, event, data)
"""
import asyncio
import logging
from typing import Optional, List

import httpx
import jwt as _jwt
from fastapi import APIRouter, HTTPException, Header, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field, field_validator

from core.config import (
    db, SYROCE_JWT_SECRET, AFSADAKAT_ADMIN_TOKEN, SYROCE_INTEGRATION_ENABLED,
)
from core.tenant_guard import serialize_doc, new_id, now_utc
from routers.auth import create_token, hash_password

logger = logging.getLogger("omnihub.syroce")

router = APIRouter(tags=["syroce"])


# ============ Provisioning ============

class SyroceProvisionRequest(BaseModel):
    external_tenant_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=200)
    email: str = Field(min_length=3, max_length=200)
    phone: str = Field(default="", max_length=64)
    hotel_id: int
    pms_callback_url: str = Field(min_length=8, max_length=500)
    pms_api_key: str = Field(min_length=8, max_length=500)

    @field_validator("pms_callback_url")
    @classmethod
    def _v_url(cls, v: str) -> str:
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("pms_callback_url must start with http(s)://")
        return v.rstrip("/")


def _slugify(name: str, suffix: str) -> str:
    import re
    base = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:32] or "syroce"
    return f"{base}-{suffix[-8:]}"


def _check_admin(token: Optional[str]):
    if not SYROCE_INTEGRATION_ENABLED:
        raise HTTPException(status_code=503, detail="Syroce integration disabled")
    if not AFSADAKAT_ADMIN_TOKEN:
        raise HTTPException(status_code=500, detail="AFSADAKAT_ADMIN_TOKEN not configured")
    if not token or not token.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    if token.split(" ", 1)[1].strip() != AFSADAKAT_ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token")


@router.post("/api/admin/integrations/syroce/provision")
async def syroce_provision(
    payload: SyroceProvisionRequest,
    authorization: Optional[str] = Header(default=None),
):
    _check_admin(authorization)

    ext_id = payload.external_tenant_id

    # Idempotent upsert by external_tenant_id
    tenant = await db.tenants.find_one({"external_tenant_id": ext_id})
    if tenant:
        await db.tenants.update_one(
            {"id": tenant["id"]},
            {"$set": {
                "name": payload.name,
                "updated_at": now_utc().isoformat(),
                "external_provider": "syroce",
                "external_hotel_id": payload.hotel_id,
            }},
        )
        tenant_id = tenant["id"]
        slug = tenant.get("slug")
        created = False
    else:
        tenant_id = new_id()
        slug = _slugify(payload.name, tenant_id)
        # ensure slug uniqueness
        while await db.tenants.find_one({"slug": slug}):
            slug = f"{slug}-{new_id()[:4]}"
        await db.tenants.insert_one({
            "id": tenant_id,
            "slug": slug,
            "name": payload.name,
            "business_type": "hotel",
            "plan": "basic",
            "hotel_enabled": True,
            "restaurant_enabled": False,
            "agency_enabled": False,
            "clinic_enabled": False,
            "external_tenant_id": ext_id,
            "external_provider": "syroce",
            "external_hotel_id": payload.hotel_id,
            "contact_email": payload.email,
            "contact_phone": payload.phone,
            "plan_limits": {"max_users": 25, "max_rooms": 100, "max_tables": 50,
                             "monthly_ai_replies": 500},
            "usage_counters": {"users": 0, "rooms": 0, "tables": 0,
                                "ai_replies_this_month": 0},
            "loyalty_rules": {"enabled": True, "points_per_request": 10,
                               "points_per_order": 5, "points_per_currency_unit": 1},
            "created_at": now_utc().isoformat(),
            "updated_at": now_utc().isoformat(),
        })
        created = True

    # Upsert PMS config (provider=syroce; api_url=callback, api_key=pms_api_key)
    await db.pms_configs.delete_many({"tenant_id": tenant_id})
    await db.pms_configs.insert_one({
        "id": new_id(),
        "tenant_id": tenant_id,
        "provider": "syroce",
        "api_url": payload.pms_callback_url,
        "api_key": payload.pms_api_key,
        "hotel_id": str(payload.hotel_id),
        "external_tenant_id": ext_id,
        "sync_rooms": True, "sync_guests": True, "sync_reservations": True,
        "auto_post_charges": True,
        "status": "configured",
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat(),
    })

    logger.info(
        f"Syroce provision {'created' if created else 'updated'}: "
        f"ext={ext_id} tenant={tenant_id} slug={slug}"
    )
    return {"ok": True, "ext_tenant_id": ext_id, "tenant_id": tenant_id,
            "slug": slug, "created": created}


# ============ SSO ============

ROLE_MAP = {"admin": "admin", "manager": "manager"}


def _redirect_html(token: str, slug: str, target: str = "/dashboard") -> str:
    """Embed token + tenant info into localStorage then redirect.

    Frontend SPA reads `token` and `tenant` from localStorage on boot.
    """
    safe_target = target if target.startswith("/") else "/dashboard"
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Yönlendiriliyor…</title></head>
<body style="font-family:system-ui;background:#0a0a0a;color:#fff;display:flex;align-items:center;justify-content:center;height:100vh;margin:0">
<div style="text-align:center">
  <div style="width:42px;height:42px;border:3px solid #444;border-top-color:#10b981;border-radius:50%;animation:s 0.9s linear infinite;margin:0 auto 14px"></div>
  <p>Syroce ile oturum açılıyor…</p>
</div>
<style>@keyframes s{{to{{transform:rotate(360deg)}}}}</style>
<script>
  try {{
    localStorage.setItem('token', {token!r});
    localStorage.setItem('tenant_slug', {slug!r});
  }} catch (e) {{}}
  window.location.replace({safe_target!r});
</script>
</body></html>"""


@router.get("/sso/syroce")
async def sso_syroce(token: str, request: Request):
    if not SYROCE_INTEGRATION_ENABLED:
        raise HTTPException(status_code=503, detail="Syroce integration disabled")
    if not SYROCE_JWT_SECRET:
        raise HTTPException(status_code=500, detail="SYROCE_JWT_SECRET not configured")
    if not token:
        raise HTTPException(status_code=400, detail="token required")
    try:
        claims = _jwt.decode(
            token, SYROCE_JWT_SECRET, algorithms=["HS256"],
            audience="afsadakat", issuer="syroce-pms", leeway=10,
        )
    except _jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="SSO token expired")
    except _jwt.InvalidTokenError as e:
        logger.warning(f"Invalid SSO token: {e}")
        raise HTTPException(status_code=401, detail="Invalid SSO token")

    sub = claims.get("sub")
    user_id = claims.get("user_id")
    username = claims.get("username") or ""
    email = claims.get("email") or f"{user_id}@syroce.local"
    name = claims.get("name") or username or email
    role_in = (claims.get("role") or "").lower()
    role = ROLE_MAP.get(role_in, "staff")

    if not sub or not user_id:
        raise HTTPException(status_code=400, detail="Token missing required claims")

    tenant = await db.tenants.find_one({"external_tenant_id": sub})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not provisioned for this Syroce account")
    tenant_id = tenant["id"]

    # Upsert user by external_user_id
    user = await db.users.find_one({"tenant_id": tenant_id, "external_user_id": str(user_id)})
    if user:
        await db.users.update_one(
            {"id": user["id"]},
            {"$set": {"name": name, "email": email, "role": role, "active": True,
                       "updated_at": now_utc().isoformat()}},
        )
        u_id = user["id"]
    else:
        u_id = new_id()
        await db.users.insert_one({
            "id": u_id,
            "tenant_id": tenant_id,
            "external_user_id": str(user_id),
            "external_provider": "syroce",
            "email": email,
            "password_hash": hash_password(new_id() + new_id()),
            "name": name,
            "role": role,
            "active": True,
            "created_at": now_utc().isoformat(),
        })

    jwt_token = create_token(u_id, tenant_id, role)
    logger.info(f"Syroce SSO success: tenant={tenant_id} user={u_id} role={role}")
    target = "/dashboard"
    return HTMLResponse(content=_redirect_html(jwt_token, tenant.get("slug", ""), target))


# ============ Outbound webhook (Af-sadakat -> Syroce) ============

WEBHOOK_BACKOFF: List[float] = [1.0, 4.0, 16.0, 64.0, 256.0]


async def _send_webhook(callback_url: str, api_key: str, body: dict) -> bool:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    url = f"{callback_url.rstrip('/')}/api/integrations/afsadakat/webhook"
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            r = await client.post(url, json=body, headers=headers)
            return 200 <= r.status_code < 300
        except Exception as e:
            logger.warning(f"Syroce webhook attempt failed: {e}")
            return False


async def _deliver_with_retry(callback_url: str, api_key: str, body: dict,
                              tenant_id: str, event: str):
    for i, delay in enumerate(WEBHOOK_BACKOFF):
        if await _send_webhook(callback_url, api_key, body):
            logger.info(f"Syroce webhook delivered: tenant={tenant_id} event={event} attempt={i+1}")
            return
        await asyncio.sleep(delay)
    # All retries failed
    logger.error(f"Syroce webhook failed after retries: tenant={tenant_id} event={event}")
    try:
        await db.webhook_failures.insert_one({
            "id": new_id(),
            "tenant_id": tenant_id,
            "provider": "syroce",
            "event": event,
            "body": body,
            "created_at": now_utc().isoformat(),
        })
    except Exception:
        pass


async def fire_syroce_event(tenant_id: str, event: str, data: dict):
    """Fire-and-forget outbound webhook to a tenant's Syroce instance.

    No-op if SYROCE_INTEGRATION_ENABLED is false or tenant has no Syroce
    pms_config. Schedules retries in the background; never blocks the caller.
    """
    if not SYROCE_INTEGRATION_ENABLED:
        return
    cfg = await db.pms_configs.find_one(
        {"tenant_id": tenant_id, "provider": "syroce"}, {"_id": 0}
    )
    if not cfg or not cfg.get("api_url") or not cfg.get("api_key"):
        return
    body = {"event": event, "data": data}
    try:
        asyncio.create_task(_deliver_with_retry(
            cfg["api_url"], cfg["api_key"], body, tenant_id, event
        ))
    except RuntimeError:
        # No running loop (e.g. called from sync context) — best effort skip
        logger.debug("fire_syroce_event called without running loop; skipping")
