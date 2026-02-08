"""Meta Integration Admin Router.
OAuth flow, asset discovery, enable/disable, pull-now.
All endpoints require tenant_guard authentication.
"""
import os
import secrets
import logging
import jwt as pyjwt
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import HTMLResponse

from core.config import db, JWT_SECRET, PUBLIC_BASE_URL
from core.tenant_guard import (
    resolve_tenant, get_current_user, serialize_doc,
    new_id, now_utc, find_one_scoped, find_many_scoped,
    insert_scoped, update_scoped, log_audit
)
from security import encrypt_field, decrypt_field
from services.meta_provider import (
    build_oauth_url, exchange_code_for_token, get_long_lived_token,
    list_pages, list_ig_accounts_for_page, list_whatsapp_business_accounts,
    subscribe_page_webhooks, unsubscribe_page_webhooks,
    MetaAPIError, get_meta_credentials
)

logger = logging.getLogger("omnihub.meta_integration")

router = APIRouter(prefix="/api/v2/integrations/meta", tags=["meta-integration"])

OAUTH_STATE_SECRET = os.getenv("JWT_SECRET", "omni-inbox-hub-secret-key-change-in-production")


# ============ STATUS ============

@router.get("/tenants/{tenant_slug}/status")
async def get_meta_status(tenant_slug: str, user=Depends(get_current_user)):
    """Get Meta integration status for this tenant."""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    cred = await db.connector_credentials.find_one(
        {"tenant_id": tid, "connector_type": "META"}, {"_id": 0}
    )

    if not cred:
        return {
            "status": "NOT_CONFIGURED",
            "connected": False,
            "assets": [],
            "webhook_url": f"{PUBLIC_BASE_URL}/api/v2/webhooks/meta/{tenant['slug']}",
        }

    cred = serialize_doc(cred)
    # Never expose secrets
    safe_cred = {
        "status": cred.get("status", "DISCONNECTED"),
        "connected": cred.get("status") == "CONNECTED",
        "meta_app_id": cred.get("meta_app_id", ""),
        "has_access_token": bool(cred.get("access_token")),
        "token_expires_at": cred.get("token_expires_at"),
        "scopes": cred.get("scopes", []),
        "last_error": cred.get("last_error"),
        "updated_at": cred.get("updated_at"),
    }

    # List assets
    assets_cursor = db.meta_assets.find({"tenant_id": tid}, {"_id": 0})
    assets = [serialize_doc(a) async for a in assets_cursor]

    safe_cred["assets"] = assets
    safe_cred["webhook_url"] = f"{PUBLIC_BASE_URL}/api/v2/webhooks/meta/{tenant['slug']}"
    safe_cred["verify_token"] = cred.get("meta_verify_token", "")

    return safe_cred


# ============ CONFIGURE CREDENTIALS ============

@router.post("/tenants/{tenant_slug}/configure")
async def configure_meta(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    """Store Meta app credentials (app_id, app_secret, verify_token)."""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    if user.get("role") not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Only Admin/Owner can configure integrations")

    app_id = data.get("meta_app_id", "").strip()
    app_secret = data.get("meta_app_secret", "").strip()
    verify_token = data.get("meta_verify_token", "").strip()

    if not verify_token:
        verify_token = secrets.token_urlsafe(24)

    redirect_uri = data.get("oauth_redirect_uri", "").strip()
    if not redirect_uri:
        redirect_uri = f"{PUBLIC_BASE_URL}/api/v2/integrations/meta/oauth/callback"

    existing = await db.connector_credentials.find_one(
        {"tenant_id": tid, "connector_type": "META"}, {"_id": 0}
    )

    update_data = {
        "tenant_id": tid,
        "connector_type": "META",
        "meta_app_id": app_id,
        "meta_app_secret": encrypt_field(app_secret) if app_secret else (existing or {}).get("meta_app_secret", ""),
        "meta_verify_token": verify_token,
        "oauth_redirect_uri": redirect_uri,
        "status": "DISCONNECTED" if not (existing or {}).get("access_token") else (existing or {}).get("status", "DISCONNECTED"),
        "updated_at": now_utc().isoformat(),
    }

    if existing:
        await db.connector_credentials.update_one(
            {"tenant_id": tid, "connector_type": "META"},
            {"$set": update_data}
        )
    else:
        update_data["id"] = new_id()
        update_data["access_token"] = ""
        update_data["token_expires_at"] = None
        update_data["scopes"] = []
        update_data["created_at"] = now_utc().isoformat()
        await db.connector_credentials.insert_one(update_data)

    await log_audit(tid, "META_CONFIGURED", "connector", "META", user.get("id", ""))

    return {
        "ok": True,
        "verify_token": verify_token,
        "webhook_url": f"{PUBLIC_BASE_URL}/api/v2/webhooks/meta/{tenant['slug']}",
        "redirect_uri": redirect_uri,
    }


# ============ OAUTH ============

@router.post("/tenants/{tenant_slug}/oauth/start")
async def oauth_start(tenant_slug: str, user=Depends(get_current_user)):
    """Generate Meta OAuth URL for this tenant."""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    cred = await get_meta_credentials(tid)
    if not cred or not cred.get("meta_app_id"):
        raise HTTPException(status_code=400, detail="Meta app not configured. Set app_id first.")

    # Create signed state JWT
    state_payload = {
        "tenant_id": tid,
        "tenant_slug": tenant["slug"],
        "nonce": secrets.token_hex(16),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    state = pyjwt.encode(state_payload, OAUTH_STATE_SECRET, algorithm="HS256")

    redirect_uri = cred.get("oauth_redirect_uri",
                             f"{PUBLIC_BASE_URL}/api/v2/integrations/meta/oauth/callback")

    url = build_oauth_url(
        app_id=cred["meta_app_id"],
        redirect_uri=redirect_uri,
        state=state,
    )

    return {"url": url, "state": state}


@router.get("/oauth/callback")
async def oauth_callback(code: str = "", state: str = "", error: str = ""):
    """Meta OAuth callback. Public endpoint (no tenant_guard)."""
    if error:
        return HTMLResponse(f"<html><body><h2>Authorization failed</h2><p>{error}</p></body></html>", status_code=400)

    if not code or not state:
        return HTMLResponse("<html><body><h2>Missing code or state</h2></body></html>", status_code=400)

    # Decode state
    try:
        payload = pyjwt.decode(state, OAUTH_STATE_SECRET, algorithms=["HS256"])
    except pyjwt.InvalidTokenError:
        return HTMLResponse("<html><body><h2>Invalid or expired state</h2></body></html>", status_code=400)

    tid = payload.get("tenant_id", "")
    _tenant_slug = payload.get("tenant_slug", "")

    cred = await get_meta_credentials(tid)
    if not cred:
        return HTMLResponse("<html><body><h2>Connector not configured</h2></body></html>", status_code=400)

    redirect_uri = cred.get("oauth_redirect_uri",
                             f"{PUBLIC_BASE_URL}/api/v2/integrations/meta/oauth/callback")

    try:
        # Exchange code for short-lived token
        token_data = await exchange_code_for_token(
            cred["meta_app_id"], cred["meta_app_secret"],
            redirect_uri, code
        )
        short_token = token_data["access_token"]

        # Exchange for long-lived token
        ll_data = await get_long_lived_token(
            cred["meta_app_id"], cred["meta_app_secret"], short_token
        )
        long_token = ll_data["access_token"]
        expires_in = ll_data.get("expires_in", 5184000)  # ~60 days default

        # Store encrypted
        await db.connector_credentials.update_one(
            {"tenant_id": tid, "connector_type": "META"},
            {"$set": {
                "access_token": encrypt_field(long_token),
                "token_expires_at": (now_utc() + timedelta(seconds=expires_in)).isoformat(),
                "status": "CONNECTED",
                "last_error": None,
                "updated_at": now_utc().isoformat(),
            }}
        )

        await log_audit(tid, "META_OAUTH_CONNECTED", "connector", "META", "oauth")

        # Auto-trigger asset discovery
        try:
            await _discover_assets_internal(tid, long_token)
        except Exception as e:
            logger.warning(f"Auto-discovery failed after OAuth: {e}")

        return HTMLResponse(
            """<html><body style="font-family:sans-serif;text-align:center;padding:40px">
            <h2 style="color:#22c55e">Meta Connected Successfully!</h2>
            <p>You can close this window and return to the dashboard.</p>
            <script>setTimeout(function(){window.close()},3000)</script>
            </body></html>"""
        )

    except MetaAPIError as e:
        logger.error(f"OAuth callback error: {e}")
        await db.connector_credentials.update_one(
            {"tenant_id": tid, "connector_type": "META"},
            {"$set": {"status": "ERROR", "last_error": str(e), "updated_at": now_utc().isoformat()}}
        )
        return HTMLResponse(
            f"<html><body><h2>Connection Failed</h2><p>{str(e)[:200]}</p></body></html>",
            status_code=500
        )


# ============ ASSET DISCOVERY ============

async def _discover_assets_internal(tenant_id: str, token: str) -> List[Dict]:
    """Internal: Discover FB pages, IG accounts, WA numbers."""
    discovered = []

    # Facebook Pages
    try:
        pages = await list_pages(token)
        for page in pages:
            asset = {
                "tenant_id": tenant_id,
                "asset_type": "FB_PAGE",
                "meta_id": page["id"],
                "display_name": page.get("name", f"Page {page['id']}"),
                "page_id": page["id"],
                "page_access_token": encrypt_field(page.get("access_token", "")),
                "extra": {"category": page.get("category", "")},
                "is_enabled": False,
                "updated_at": now_utc().isoformat(),
            }
            await db.meta_assets.update_one(
                {"tenant_id": tenant_id, "asset_type": "FB_PAGE", "meta_id": page["id"]},
                {"$set": asset, "$setOnInsert": {"id": new_id(), "created_at": now_utc().isoformat()}},
                upsert=True
            )
            discovered.append(asset)

            # Instagram Business Account for this page
            try:
                ig_data = await list_ig_accounts_for_page(page["id"], page.get("access_token", token))
                if ig_data:
                    ig_asset = {
                        "tenant_id": tenant_id,
                        "asset_type": "IG_ACCOUNT",
                        "meta_id": ig_data["id"],
                        "display_name": ig_data.get("username", ig_data.get("name", f"IG {ig_data['id']}")),
                        "page_id": page["id"],
                        "ig_user_id": ig_data["id"],
                        "extra": {
                            "username": ig_data.get("username", ""),
                            "profile_picture_url": ig_data.get("profile_picture_url", ""),
                        },
                        "is_enabled": False,
                        "updated_at": now_utc().isoformat(),
                    }
                    await db.meta_assets.update_one(
                        {"tenant_id": tenant_id, "asset_type": "IG_ACCOUNT", "meta_id": ig_data["id"]},
                        {"$set": ig_asset, "$setOnInsert": {"id": new_id(), "created_at": now_utc().isoformat()}},
                        upsert=True
                    )
                    discovered.append(ig_asset)
            except MetaAPIError:
                pass
    except MetaAPIError as e:
        logger.warning(f"Page discovery error: {e}")

    # WhatsApp Business Accounts
    try:
        waba_list = await list_whatsapp_business_accounts(token)
        for waba in waba_list:
            for phone in waba.get("phone_numbers", {}).get("data", []):
                wa_asset = {
                    "tenant_id": tenant_id,
                    "asset_type": "WA_PHONE_NUMBER",
                    "meta_id": phone["id"],
                    "display_name": phone.get("verified_name", phone.get("display_phone_number", "")),
                    "wa_business_account_id": waba["id"],
                    "extra": {
                        "display_phone_number": phone.get("display_phone_number", ""),
                        "waba_name": waba.get("name", ""),
                    },
                    "is_enabled": False,
                    "updated_at": now_utc().isoformat(),
                }
                await db.meta_assets.update_one(
                    {"tenant_id": tenant_id, "asset_type": "WA_PHONE_NUMBER", "meta_id": phone["id"]},
                    {"$set": wa_asset, "$setOnInsert": {"id": new_id(), "created_at": now_utc().isoformat()}},
                    upsert=True
                )
                discovered.append(wa_asset)
    except MetaAPIError as e:
        logger.warning(f"WhatsApp discovery error: {e}")

    return discovered


@router.post("/tenants/{tenant_slug}/discover-assets")
async def discover_assets(tenant_slug: str, user=Depends(get_current_user)):
    """Manually trigger asset discovery."""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    cred = await get_meta_credentials(tid)
    if not cred or not cred.get("access_token"):
        raise HTTPException(status_code=400, detail="Not connected. Complete OAuth first.")

    try:
        discovered = await _discover_assets_internal(tid, cred["access_token"])
        await log_audit(tid, "META_ASSETS_DISCOVERED", "connector", "META", user.get("id", ""),
                       {"count": len(discovered)})
        return {"discovered": len(discovered), "assets": [serialize_doc(a) for a in discovered]}
    except MetaAPIError as e:
        raise HTTPException(status_code=502, detail=f"Meta API error: {str(e)[:200]}")


# ============ ENABLE / DISABLE ASSETS ============

@router.put("/tenants/{tenant_slug}/assets")
async def update_assets(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    """Enable or disable Meta assets. Body: {assets: [{asset_type, meta_id, is_enabled}]}"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    if user.get("role") not in ["owner", "admin", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    cred = await get_meta_credentials(tid)
    token = cred.get("access_token", "") if cred else ""

    updates = data.get("assets", [])
    results = []

    for item in updates:
        asset_type = item.get("asset_type", "")
        meta_id = item.get("meta_id", "")
        is_enabled = item.get("is_enabled", False)

        asset = await db.meta_assets.find_one(
            {"tenant_id": tid, "asset_type": asset_type, "meta_id": meta_id},
            {"_id": 0}
        )
        if not asset:
            results.append({"meta_id": meta_id, "error": "Asset not found"})
            continue

        await db.meta_assets.update_one(
            {"tenant_id": tid, "asset_type": asset_type, "meta_id": meta_id},
            {"$set": {"is_enabled": is_enabled, "updated_at": now_utc().isoformat()}}
        )

        # Subscribe/unsubscribe page webhooks if FB_PAGE
        if asset_type == "FB_PAGE" and token:
            page_token = decrypt_field(asset.get("page_access_token", "")) or token
            if is_enabled:
                await subscribe_page_webhooks(meta_id, page_token)
            else:
                await unsubscribe_page_webhooks(meta_id, page_token)

        action = "META_ASSET_ENABLED" if is_enabled else "META_ASSET_DISABLED"
        await log_audit(tid, action, "meta_asset", meta_id, user.get("id", ""),
                       {"asset_type": asset_type})
        results.append({"meta_id": meta_id, "is_enabled": is_enabled, "ok": True})

    return {"results": results}


# ============ PULL NOW (Manual Sync) ============

@router.post("/tenants/{tenant_slug}/pull-now")
async def meta_pull_now(tenant_slug: str, user=Depends(get_current_user)):
    """Manual sync - verifies token, returns status. Real data comes via webhooks."""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    cred = await get_meta_credentials(tid)
    if not cred or not cred.get("access_token"):
        return {"status": "NOT_CONNECTED", "message": "Complete OAuth to connect Meta."}

    # Verify token still works
    try:
        from services.meta_provider import _graph_get
        me = await _graph_get("me", cred["access_token"], {"fields": "id,name"})
        await log_audit(tid, "META_PULL_NOW", "connector", "META", user.get("id", ""),
                       {"fb_user": me.get("name", "")})
        return {
            "status": "CONNECTED",
            "message": "Token valid. Inbound data arrives via webhooks in real-time.",
            "fb_user": me.get("name", ""),
        }
    except MetaAPIError as e:
        await db.connector_credentials.update_one(
            {"tenant_id": tid, "connector_type": "META"},
            {"$set": {"status": "ERROR", "last_error": str(e), "updated_at": now_utc().isoformat()}}
        )
        return {"status": "ERROR", "message": str(e)[:200]}


# ============ DISCONNECT ============

@router.post("/tenants/{tenant_slug}/disconnect")
async def disconnect_meta(tenant_slug: str, user=Depends(get_current_user)):
    """Disconnect Meta integration."""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    if user.get("role") not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Only Admin/Owner can disconnect")

    await db.connector_credentials.update_one(
        {"tenant_id": tid, "connector_type": "META"},
        {"$set": {
            "access_token": "",
            "status": "DISCONNECTED",
            "last_error": None,
            "updated_at": now_utc().isoformat(),
        }}
    )

    # Disable all assets
    await db.meta_assets.update_many(
        {"tenant_id": tid},
        {"$set": {"is_enabled": False, "updated_at": now_utc().isoformat()}}
    )

    await log_audit(tid, "META_DISCONNECTED", "connector", "META", user.get("id", ""))
    return {"ok": True}
