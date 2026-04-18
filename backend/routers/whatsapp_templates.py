"""WhatsApp Template management & sending.
Templates must be pre-approved in Meta Business Manager. This router stores
template metadata locally so agents can pick them in the inbox UI when the
24-hour conversation window has expired.
"""
import logging
import re
from typing import List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, Field, field_validator

from core.config import db
from core.tenant_guard import (
    resolve_tenant, serialize_doc, now_utc,
    find_one_scoped, find_many_scoped, insert_scoped, delete_scoped,
    log_audit, get_current_user,
)

logger = logging.getLogger("omnihub.whatsapp_templates")
router = APIRouter(prefix="/api/v2/whatsapp", tags=["whatsapp"])

ALLOWED_CATEGORIES = {"UTILITY", "MARKETING", "AUTHENTICATION"}
ADMIN_ROLES = {"admin", "owner", "manager", "agent"}
NAME_RE = re.compile(r"^[a-z0-9_]{1,64}$")
LANG_RE = re.compile(r"^[a-z]{2}(_[A-Z]{2})?$")


def _ensure_tenant_member(user: dict, tenant: dict, allow_roles: Optional[set] = None):
    """Reject if the authenticated user does not belong to the requested tenant
    or lacks required role."""
    if user.get("tenant_id") != tenant.get("id"):
        raise HTTPException(status_code=403, detail="Forbidden: tenant mismatch")
    if allow_roles:
        role = (user.get("role") or "").lower()
        if role not in allow_roles:
            raise HTTPException(status_code=403, detail="Forbidden: insufficient role")


class TemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    language: str = Field(default="en", min_length=2, max_length=8)
    category: str = Field(default="UTILITY")
    body_preview: str = Field(default="", max_length=1024)
    param_count: int = Field(default=0, ge=0, le=10)
    status: str = Field(default="APPROVED", max_length=24)

    @field_validator("name")
    @classmethod
    def _v_name(cls, v: str) -> str:
        v = v.strip().lower()
        if not NAME_RE.match(v):
            raise ValueError("name must match ^[a-z0-9_]{1,64}$")
        return v

    @field_validator("language")
    @classmethod
    def _v_lang(cls, v: str) -> str:
        if not LANG_RE.match(v):
            raise ValueError("language must be like 'en' or 'pt_BR'")
        return v

    @field_validator("category")
    @classmethod
    def _v_cat(cls, v: str) -> str:
        v = v.upper()
        if v not in ALLOWED_CATEGORIES:
            raise ValueError(f"category must be one of {sorted(ALLOWED_CATEGORIES)}")
        return v


class TemplateSend(BaseModel):
    template_name: str = Field(min_length=1, max_length=64)
    language: str = Field(default="en", min_length=2, max_length=8)
    parameters: List[str] = Field(default_factory=list, max_length=10)

    @field_validator("template_name")
    @classmethod
    def _v_tname(cls, v: str) -> str:
        v = v.strip().lower()
        if not NAME_RE.match(v):
            raise ValueError("template_name must match ^[a-z0-9_]{1,64}$")
        return v

    @field_validator("language")
    @classmethod
    def _v_tlang(cls, v: str) -> str:
        if not LANG_RE.match(v):
            raise ValueError("language must be like 'en' or 'pt_BR'")
        return v

    @field_validator("parameters")
    @classmethod
    def _v_params(cls, v: List[str]) -> List[str]:
        cleaned = []
        for p in v:
            if not isinstance(p, str):
                raise ValueError("each parameter must be a string")
            s = p.strip()
            if not s or len(s) > 1024:
                raise ValueError("parameters must be 1..1024 chars")
            cleaned.append(s)
        return cleaned


@router.get("/tenants/{tenant_slug}/templates")
async def list_templates(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    _ensure_tenant_member(user, tenant)
    items = await find_many_scoped(
        "wa_templates", tenant["id"], {}, sort=[("created_at", -1)], limit=200
    )
    return [serialize_doc(t) for t in items]


@router.post("/tenants/{tenant_slug}/templates")
async def create_template(tenant_slug: str, payload: TemplateCreate,
                          user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    _ensure_tenant_member(user, tenant, ADMIN_ROLES)
    created = await insert_scoped("wa_templates", tenant["id"], payload.model_dump())
    await log_audit(tenant["id"], "WA_TEMPLATE_CREATED", "wa_template",
                    created["id"], user.get("id", ""))
    return created


@router.delete("/tenants/{tenant_slug}/templates/{template_id}")
async def delete_template(tenant_slug: str, template_id: str,
                          user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    _ensure_tenant_member(user, tenant, ADMIN_ROLES)
    ok = await delete_scoped("wa_templates", tenant["id"], template_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Template not found")
    await log_audit(tenant["id"], "WA_TEMPLATE_DELETED", "wa_template",
                    template_id, user.get("id", ""))
    return {"deleted": True}


@router.post("/tenants/{tenant_slug}/conversations/{conv_id}/send-template")
async def send_template_message(
    tenant_slug: str,
    conv_id: str,
    payload: TemplateSend,
    user=Depends(get_current_user),
):
    """Send a WhatsApp template to reopen the 24-hour window."""
    tenant = await resolve_tenant(tenant_slug)
    _ensure_tenant_member(user, tenant, ADMIN_ROLES)
    conv = await find_one_scoped("conversations", tenant["id"], {"id": conv_id})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.get("channel_type") != "WHATSAPP":
        raise HTTPException(status_code=400, detail="Templates only valid for WhatsApp")

    external = conv.get("external", {})
    wa_phone_id = external.get("wa_phone_number_id", external.get("asset_id", ""))
    wa_to = external.get("wa_from_number", external.get("contact_id", ""))
    if not wa_phone_id or not wa_to:
        raise HTTPException(status_code=400, detail="Conversation missing WhatsApp routing info")

    components = []
    if payload.parameters:
        components.append({
            "type": "body",
            "parameters": [{"type": "text", "text": p} for p in payload.parameters],
        })

    send_result = None
    try:
        from services.meta_provider import (
            get_meta_credentials, send_whatsapp_template, MetaAPIError,
        )
        cred = await get_meta_credentials(tenant["id"])
        if not cred or not cred.get("access_token"):
            raise HTTPException(status_code=400, detail="Meta credentials not configured")
        send_result = await send_whatsapp_template(
            wa_phone_id, cred["access_token"], wa_to,
            payload.template_name, payload.language, components or None,
        )
    except HTTPException:
        raise
    except MetaAPIError as e:
        logger.error(f"WA template send failed (tenant={tenant['id']}): {e}")
        raise HTTPException(status_code=502, detail="WhatsApp template send failed")
    except Exception as e:
        logger.exception(f"WA template send error (tenant={tenant['id']}): {e}")
        raise HTTPException(status_code=502, detail="WhatsApp template send failed")

    body_preview = f"[Template] {payload.template_name}"
    if payload.parameters:
        body_preview += f" ({', '.join(payload.parameters)})"

    msg = await insert_scoped("messages", tenant["id"], {
        "conversation_id": conv_id, "direction": "OUT", "body": body_preview,
        "last_updated_by": user.get("name", "Agent"),
        "meta": {
            "sender_type": "agent", "sender_id": user.get("id", ""),
            "provider": "META", "kind": "template",
            "template_name": payload.template_name,
            "template_language": payload.language,
            "template_parameters": payload.parameters,
            "meta_send_result": send_result,
        },
    })
    await db.conversations.update_one(
        {"id": conv_id, "tenant_id": tenant["id"]},
        {"$set": {"last_message_at": now_utc().isoformat()}},
    )
    await log_audit(tenant["id"], "WA_TEMPLATE_SENT", "message",
                    msg["id"], user.get("id", ""))

    try:
        from core.legacy_helpers import ws_manager
        await ws_manager.broadcast_tenant(
            tenant["id"], "message", "message", "created", msg
        )
    except Exception:
        pass

    return msg


# ---------- WhatsApp media proxy ----------
# Resolves a wa_media_id via Graph API to a signed URL, then streams the binary
# back through our server so agents can view inbound WhatsApp media without
# leaking access tokens or signed Meta URLs to the browser.

MEDIA_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{4,128}$")


@router.get("/tenants/{tenant_slug}/media/{media_id}")
async def proxy_whatsapp_media(tenant_slug: str, media_id: str,
                                user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    _ensure_tenant_member(user, tenant)
    if not MEDIA_ID_RE.match(media_id):
        raise HTTPException(status_code=400, detail="Invalid media id")
    try:
        from services.meta_provider import get_meta_credentials, _graph_get
        cred = await get_meta_credentials(tenant["id"])
        if not cred or not cred.get("access_token"):
            raise HTTPException(status_code=400, detail="Meta credentials not configured")
        token = cred["access_token"]
        info = await _graph_get(media_id, token, {"fields": "url,mime_type"})
        signed_url = info.get("url")
        mime = info.get("mime_type") or "application/octet-stream"
        if not signed_url:
            raise HTTPException(status_code=404, detail="Media URL not available")
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(signed_url, headers={"Authorization": f"Bearer {token}"})
            if r.status_code != 200:
                raise HTTPException(status_code=502, detail="Media fetch failed")
            return Response(
                content=r.content, media_type=mime,
                headers={"Cache-Control": "private, max-age=300"},
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"WA media proxy error: {e}")
        raise HTTPException(status_code=502, detail="Media fetch failed")
