"""Meta (Facebook / Instagram / WhatsApp) Graph API provider.
All outbound calls to Meta go through this layer.
Tokens are per-tenant, stored encrypted in connector_credentials.
"""
import os
import hmac
import hashlib
import logging
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

import httpx

from core.config import db
from core.tenant_guard import serialize_doc, new_id, now_utc
from security import encrypt_field, decrypt_field

logger = logging.getLogger("omnihub.meta")

META_GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v21.0")
META_GRAPH_BASE = f"https://graph.facebook.com/{META_GRAPH_VERSION}"
META_OAUTH_BASE = "https://www.facebook.com/{version}/dialog/oauth".format(version=META_GRAPH_VERSION)
HTTP_TIMEOUT = 15.0

# Required scopes for full integration
DEFAULT_SCOPES = [
    "pages_show_list", "pages_read_engagement", "pages_manage_metadata",
    "pages_messaging", "pages_manage_posts",
    "instagram_basic", "instagram_manage_messages", "instagram_manage_comments",
    "business_management",
]


# ============ HELPERS ============

async def get_meta_credentials(tenant_id: str) -> Optional[Dict]:
    """Load & decrypt META connector credentials for a tenant."""
    cred = await db.connector_credentials.find_one(
        {"tenant_id": tenant_id, "connector_type": "META"}, {"_id": 0}
    )
    if not cred:
        return None
    # Decrypt secrets
    for field in ["meta_app_secret", "access_token"]:
        if cred.get(field):
            cred[field] = decrypt_field(cred[field])
    return serialize_doc(cred)


async def _update_cred_field(tenant_id: str, updates: Dict):
    """Update connector credential fields."""
    updates["updated_at"] = now_utc().isoformat()
    await db.connector_credentials.update_one(
        {"tenant_id": tenant_id, "connector_type": "META"},
        {"$set": updates}
    )


async def _set_error(tenant_id: str, error_msg: str):
    await _update_cred_field(tenant_id, {"status": "ERROR", "last_error": error_msg})


async def _graph_get(path: str, token: str, params: Optional[Dict] = None) -> Dict:
    """GET request to Graph API."""
    url = f"{META_GRAPH_BASE}/{path}"
    p = params or {}
    p["access_token"] = token
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(url, params=p)
        data = resp.json()
        if resp.status_code != 200 or "error" in data:
            raise MetaAPIError(data.get("error", {}).get("message", f"HTTP {resp.status_code}"), data)
        return data


async def _graph_post(path: str, token: str, payload: Optional[Dict] = None,
                      params: Optional[Dict] = None) -> Dict:
    """POST request to Graph API."""
    url = f"{META_GRAPH_BASE}/{path}"
    p = params or {}
    p["access_token"] = token
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.post(url, params=p, json=payload or {})
        data = resp.json()
        if resp.status_code not in (200, 201) or "error" in data:
            raise MetaAPIError(data.get("error", {}).get("message", f"HTTP {resp.status_code}"), data)
        return data


class MetaAPIError(Exception):
    def __init__(self, message: str, raw: Optional[Dict] = None):
        super().__init__(message)
        self.raw = raw or {}


# ============ OAUTH ============

def build_oauth_url(app_id: str, redirect_uri: str, state: str,
                    scopes: Optional[List[str]] = None) -> str:
    """Build Meta OAuth dialog URL."""
    scope_str = ",".join(scopes or DEFAULT_SCOPES)
    return (
        f"https://www.facebook.com/{META_GRAPH_VERSION}/dialog/oauth"
        f"?client_id={app_id}"
        f"&redirect_uri={redirect_uri}"
        f"&state={state}"
        f"&scope={scope_str}"
        f"&response_type=code"
    )


async def exchange_code_for_token(app_id: str, app_secret: str,
                                   redirect_uri: str, code: str) -> Dict:
    """Exchange authorization code for short-lived token."""
    url = f"{META_GRAPH_BASE}/oauth/access_token"
    params = {
        "client_id": app_id,
        "client_secret": app_secret,
        "redirect_uri": redirect_uri,
        "code": code,
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(url, params=params)
        data = resp.json()
        if "access_token" not in data:
            raise MetaAPIError(data.get("error", {}).get("message", "Token exchange failed"), data)
        return data


async def get_long_lived_token(app_id: str, app_secret: str,
                                short_token: str) -> Dict:
    """Exchange short-lived token for long-lived (60 day) token."""
    url = f"{META_GRAPH_BASE}/oauth/access_token"
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_token,
    }
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        resp = await client.get(url, params=params)
        data = resp.json()
        if "access_token" not in data:
            raise MetaAPIError("Long-lived token exchange failed", data)
        return data


# ============ ASSET DISCOVERY ============

async def list_pages(token: str) -> List[Dict]:
    """List Facebook pages the user manages."""
    data = await _graph_get("me/accounts", token, {"fields": "id,name,access_token,category"})
    return data.get("data", [])


async def list_ig_accounts_for_page(page_id: str, page_token: str) -> Optional[Dict]:
    """Get Instagram Business Account connected to a FB page."""
    data = await _graph_get(f"{page_id}", page_token,
                             {"fields": "instagram_business_account{id,username,name,profile_picture_url}"})
    return data.get("instagram_business_account")


async def list_whatsapp_business_accounts(token: str) -> List[Dict]:
    """List WhatsApp Business Accounts. Requires business_management scope."""
    try:
        data = await _graph_get("me/businesses", token, {"fields": "id,name"})
        businesses = data.get("data", [])
        waba_list = []
        for biz in businesses:
            try:
                waba_data = await _graph_get(f"{biz['id']}/owned_whatsapp_business_accounts",
                                              token, {"fields": "id,name,phone_numbers{id,display_phone_number,verified_name}"})
                for waba in waba_data.get("data", []):
                    waba["business_id"] = biz["id"]
                    waba_list.append(waba)
            except MetaAPIError:
                continue
        return waba_list
    except MetaAPIError:
        return []


# ============ WEBHOOK SUBSCRIPTION ============

async def subscribe_page_webhooks(page_id: str, page_token: str,
                                   fields: Optional[List[str]] = None) -> bool:
    """Subscribe a page to webhook events."""
    subscribed_fields = fields or ["messages", "messaging_postbacks", "feed"]
    try:
        await _graph_post(f"{page_id}/subscribed_apps", page_token,
                          {"subscribed_fields": ",".join(subscribed_fields)})
        return True
    except MetaAPIError as e:
        logger.error(f"Failed to subscribe page {page_id}: {e}")
        return False


async def unsubscribe_page_webhooks(page_id: str, page_token: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            resp = await client.delete(
                f"{META_GRAPH_BASE}/{page_id}/subscribed_apps",
                params={"access_token": page_token}
            )
            return resp.status_code == 200
    except Exception as e:
        logger.error(f"Failed to unsubscribe page {page_id}: {e}")
        return False


# ============ SEND MESSAGES ============

async def send_facebook_message(page_id: str, page_token: str,
                                 recipient_id: str, text: str) -> Dict:
    """Send message via Facebook Page Messaging."""
    return await _graph_post(f"{page_id}/messages", page_token, {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
        "messaging_type": "RESPONSE",
    })


async def send_instagram_message(ig_id: str, token: str,
                                  recipient_id: str, text: str) -> Dict:
    """Send Instagram DM."""
    return await _graph_post(f"{ig_id}/messages", token, {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
    })


async def send_whatsapp_message(phone_number_id: str, token: str,
                                 to: str, text: str) -> Dict:
    """Send WhatsApp free-form text message (within 24h window)."""
    return await _graph_post(f"{phone_number_id}/messages", token, {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    })


async def send_whatsapp_template(phone_number_id: str, token: str,
                                  to: str, template_name: str,
                                  language_code: str = "en",
                                  components: Optional[List] = None) -> Dict:
    """Send WhatsApp template message (outside 24h window)."""
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
        },
    }
    if components:
        payload["template"]["components"] = components
    return await _graph_post(f"{phone_number_id}/messages", token, payload)


# ============ COMMENTS ============

async def reply_to_comment(comment_id: str, token: str, message: str) -> Dict:
    """Reply to a Facebook/Instagram comment."""
    return await _graph_post(f"{comment_id}/replies", token, {
        "message": message,
    })


async def get_comment_details(comment_id: str, token: str) -> Dict:
    """Get comment details."""
    return await _graph_get(comment_id, token, {
        "fields": "id,message,from,created_time,permalink_url,attachment"
    })


# ============ TOKEN REFRESH ============

async def refresh_long_lived_token(app_id: str, app_secret: str,
                                    current_token: str) -> Optional[Dict]:
    """Refresh a long-lived token. Returns new token data or None."""
    try:
        return await get_long_lived_token(app_id, app_secret, current_token)
    except MetaAPIError as e:
        logger.error(f"Token refresh failed: {e}")
        return None


# ============ WEBHOOK SIGNATURE VERIFICATION ============

def verify_webhook_signature(payload_body: bytes, signature_header: str,
                              app_secret: str) -> bool:
    """Verify X-Hub-Signature-256 from Meta webhook."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        app_secret.encode(), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)
