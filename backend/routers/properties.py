"""Properties V2 Router: Multi-property support under one tenant.
Full tenant_guard isolation. Audit logged.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
import re

from core.config import db
from core.tenant_guard import (
    resolve_tenant, get_current_user, serialize_doc,
    new_id, now_utc, find_one_scoped, find_many_scoped, count_scoped,
    insert_scoped, update_scoped, log_audit
)

router = APIRouter(prefix="/api/v2/properties", tags=["properties"])


def _validate_slug(slug: str) -> str:
    slug = slug.strip().lower()
    if not re.match(r'^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$', slug):
        raise HTTPException(status_code=400, detail="Slug must be 3-50 chars, lowercase alphanumeric and hyphens")
    return slug


@router.get("/tenants/{tenant_slug}/properties")
async def list_properties(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    props = await find_many_scoped("properties", tenant["id"], {},
                                    sort=[("created_at", 1)], limit=100)
    return props


@router.post("/tenants/{tenant_slug}/properties")
async def create_property(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    name = data.get("name", "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="Property name required")

    slug = _validate_slug(data.get("slug", ""))

    # Check slug uniqueness within tenant
    existing = await find_one_scoped("properties", tid, {"slug": slug})
    if existing:
        raise HTTPException(status_code=409, detail=f"Property slug '{slug}' already exists for this tenant")

    prop = await insert_scoped("properties", tid, {
        "name": name,
        "slug": slug,
        "timezone": data.get("timezone", "Europe/Istanbul"),
        "address": data.get("address", ""),
        "phone": data.get("phone", ""),
        "email": data.get("email", ""),
        "is_active": True,
        "last_updated_by": user.get("name", ""),
    })

    await log_audit(tid, "PROPERTY_CREATED", "property", prop["id"], user.get("id", ""),
                    {"name": name, "slug": slug})
    return prop


@router.get("/tenants/{tenant_slug}/properties/{property_id}")
async def get_property(tenant_slug: str, property_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    prop = await find_one_scoped("properties", tenant["id"], {"id": property_id})
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")
    return prop


@router.patch("/tenants/{tenant_slug}/properties/{property_id}")
async def update_property(tenant_slug: str, property_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    prop = await find_one_scoped("properties", tid, {"id": property_id})
    if not prop:
        raise HTTPException(status_code=404, detail="Property not found")

    allowed = ["name", "timezone", "address", "phone", "email"]
    update = {k: v for k, v in data.items() if k in allowed and v is not None}

    if "slug" in data:
        new_slug = _validate_slug(data["slug"])
        existing = await find_one_scoped("properties", tid, {"slug": new_slug})
        if existing and existing["id"] != property_id:
            raise HTTPException(status_code=409, detail=f"Slug '{new_slug}' already in use")
        update["slug"] = new_slug

    update["last_updated_by"] = user.get("name", "")
    updated = await update_scoped("properties", tid, property_id, update)
    await log_audit(tid, "PROPERTY_UPDATED", "property", property_id, user.get("id", ""),
                    {"fields": list(update.keys())})
    return updated


@router.post("/tenants/{tenant_slug}/properties/{property_id}/deactivate")
async def deactivate_property(tenant_slug: str, property_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    updated = await update_scoped("properties", tenant["id"], property_id,
                                   {"is_active": False, "last_updated_by": user.get("name", "")})
    if not updated:
        raise HTTPException(status_code=404, detail="Property not found")
    await log_audit(tenant["id"], "PROPERTY_DEACTIVATED", "property", property_id, user.get("id", ""))
    return updated


@router.post("/tenants/{tenant_slug}/properties/{property_id}/activate")
async def activate_property(tenant_slug: str, property_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    updated = await update_scoped("properties", tenant["id"], property_id,
                                   {"is_active": True, "last_updated_by": user.get("name", "")})
    if not updated:
        raise HTTPException(status_code=404, detail="Property not found")
    await log_audit(tenant["id"], "PROPERTY_ACTIVATED", "property", property_id, user.get("id", ""))
    return updated


# ---- Helper: get default property for tenant ----
async def get_default_property(tenant_id: str):
    """Return the first (oldest) property for a tenant, or None"""
    props = await find_many_scoped("properties", tenant_id, {"is_active": True},
                                    sort=[("created_at", 1)], limit=1)
    return props[0] if props else None
