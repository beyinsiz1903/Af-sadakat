"""Meta Webhook Router.
Public endpoints - NO tenant_guard auth.
Handles: WhatsApp Cloud API, Instagram Messaging, Facebook Messaging, Comments.
Each tenant has its own webhook URL: /api/v2/webhooks/meta/{tenantSlug}
"""
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List

from fastapi import APIRouter, HTTPException, Request, Query

from core.config import db
from core.tenant_guard import serialize_doc, new_id, now_utc
from core.middleware import rate_limit_ip
from security import decrypt_field
from ai_provider import classify_sentiment

logger = logging.getLogger("omnihub.meta_webhooks")

router = APIRouter(prefix="/api/v2/webhooks/meta", tags=["meta-webhooks"])


# ============ HELPERS ============

def _deterministic_id(tenant_id: str, channel: str, meta_id: str) -> str:
    """Create deterministic external_id for deduplication."""
    return f"meta:{tenant_id}:{channel}:{meta_id}"


async def _resolve_tenant_by_slug(slug: str) -> Optional[Dict]:
    """Find tenant by slug without auth."""
    tenant = await db.tenants.find_one({"slug": slug}, {"_id": 0})
    return serialize_doc(tenant) if tenant else None


async def _get_meta_cred(tenant_id: str) -> Optional[Dict]:
    """Get meta credentials with decrypted secrets."""
    cred = await db.connector_credentials.find_one(
        {"tenant_id": tenant_id, "connector_type": "META"}, {"_id": 0}
    )
    if not cred:
        return None
    for field in ["meta_app_secret", "access_token"]:
        if cred.get(field):
            cred[field] = decrypt_field(cred[field])
    return serialize_doc(cred)


def _verify_signature(body: bytes, signature: str, app_secret: str) -> bool:
    """Verify X-Hub-Signature-256."""
    if not signature or not signature.startswith("sha256="):
        return False
    expected = "sha256=" + hmac.new(
        app_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _upsert_conversation(tenant_id: str, channel_type: str,
                                contact_external_id: str, asset_id: str,
                                contact_name: str = "",
                                extra: Optional[Dict] = None) -> Dict:
    """Find or create conversation for a Meta contact."""
    query = {
        "tenant_id": tenant_id,
        "channel_type": channel_type,
        "external.provider": "META",
        "external.contact_id": contact_external_id,
        "external.asset_id": asset_id,
    }
    conv = await db.conversations.find_one(query, {"_id": 0})
    if conv:
        await db.conversations.update_one(
            {"id": conv["id"]},
            {"$set": {"last_message_at": now_utc().isoformat()}}
        )
        return serialize_doc(conv)

    # Resolve default property
    prop = await db.properties.find_one({"tenant_id": tenant_id, "is_active": True}, {"_id": 0})
    property_id = prop["id"] if prop else ""

    conv_data = {
        "id": new_id(),
        "tenant_id": tenant_id,
        "channel_type": channel_type,
        "contact_id": None,
        "property_id": property_id,
        "status": "OPEN",
        "assigned_user_id": None,
        "guest_name": contact_name,
        "last_message_at": now_utc().isoformat(),
        "needs_attention": False,
        "external": {
            "provider": "META",
            "contact_id": contact_external_id,
            "asset_id": asset_id,
            "asset_type": channel_type,
            **(extra or {}),
        },
        "created_at": now_utc().isoformat(),
    }
    await db.conversations.insert_one(conv_data)

    # Broadcast
    try:
        from server import ws_manager
        await ws_manager.broadcast_tenant(tenant_id, "conversation", "conversation", "created",
                                           serialize_doc(conv_data))
    except Exception:
        pass

    return conv_data


async def _insert_message(tenant_id: str, conversation_id: str,
                           external_id: str, body: str,
                           direction: str = "IN",
                           meta: Optional[Dict] = None) -> Optional[Dict]:
    """Insert message with deduplication by external_id."""
    # Check dedup
    existing = await db.messages.find_one({"external_id": external_id}, {"_id": 0})
    if existing:
        return None  # Already processed

    msg = {
        "id": new_id(),
        "tenant_id": tenant_id,
        "conversation_id": conversation_id,
        "direction": direction,
        "body": body,
        "external_id": external_id,
        "meta": meta or {},
        "created_at": now_utc().isoformat(),
    }
    await db.messages.insert_one(msg)

    # Broadcast
    try:
        from server import ws_manager
        await ws_manager.broadcast_tenant(tenant_id, "message", "message", "created",
                                           serialize_doc(msg))
    except Exception:
        pass

    return msg


async def _upsert_comment_as_review(tenant_id: str, source_type: str,
                                     comment_id: str, text: str,
                                     author_name: str, created_time: str,
                                     asset_id: str, post_id: str = "",
                                     permalink: str = "") -> Optional[Dict]:
    """Upsert a comment into reviews collection."""
    external_id = f"meta:{tenant_id}:comment:{comment_id}"
    existing = await db.reviews.find_one({"external_id": external_id}, {"_id": 0})
    if existing:
        return None  # Already exists

    sentiment = classify_sentiment(text)

    review = {
        "id": new_id(),
        "tenant_id": tenant_id,
        "source_type": source_type,
        "external_id": external_id,
        "author_name": author_name,
        "text": text,
        "rating": None,
        "sentiment": sentiment,
        "language": "auto",
        "permalink": permalink,
        "replied": False,
        "resolved": False,
        "extra": {"comment_id": comment_id, "asset_id": asset_id, "post_id": post_id},
        "created_at": created_time or now_utc().isoformat(),
    }
    await db.reviews.insert_one(review)

    # Broadcast
    try:
        from server import ws_manager
        await ws_manager.broadcast_tenant(tenant_id, "review", "review", "created",
                                           serialize_doc(review))
    except Exception:
        pass

    return review


# ============ WEBHOOK VERIFICATION (GET) ============

@router.get("/{tenant_slug}")
async def webhook_verify(tenant_slug: str, request: Request):
    """Meta webhook verification challenge."""
    mode = request.query_params.get("hub.mode", "")
    token = request.query_params.get("hub.verify_token", "")
    challenge = request.query_params.get("hub.challenge", "")

    if mode != "subscribe":
        raise HTTPException(status_code=403, detail="Invalid mode")

    tenant = await _resolve_tenant_by_slug(tenant_slug)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    cred = await db.connector_credentials.find_one(
        {"tenant_id": tenant["id"], "connector_type": "META"}, {"_id": 0}
    )
    if not cred:
        raise HTTPException(status_code=404, detail="Meta not configured")

    stored_token = cred.get("meta_verify_token", "")
    if token != stored_token:
        raise HTTPException(status_code=403, detail="Invalid verify token")

    logger.info(f"Webhook verified for tenant {tenant_slug}")
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(content=challenge)


# ============ WEBHOOK EVENT HANDLER (POST) ============

@router.post("/{tenant_slug}")
async def webhook_event(tenant_slug: str, request: Request):
    """Receive Meta webhook events."""
    rate_limit_ip(request, 120, 60)

    tenant = await _resolve_tenant_by_slug(tenant_slug)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tid = tenant["id"]
    cred = await _get_meta_cred(tid)
    if not cred:
        raise HTTPException(status_code=404, detail="Meta not configured")

    # Verify signature
    body_bytes = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    app_secret = cred.get("meta_app_secret", "")

    if app_secret and not _verify_signature(body_bytes, signature, app_secret):
        logger.warning(f"Invalid webhook signature for tenant {tenant_slug}")
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        payload = json.loads(body_bytes)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    obj = payload.get("object", "")
    entries = payload.get("entry", [])

    messages_created = 0
    comments_created = 0

    for entry in entries:
        entry_id = entry.get("id", "")  # page_id or waba_id

        # ---- WhatsApp Cloud API ----
        if obj == "whatsapp_business_account":
            for change in entry.get("changes", []):
                value = change.get("value", {})
                if change.get("field") == "messages":
                    phone_number_id = value.get("metadata", {}).get("phone_number_id", "")
                    for msg in value.get("messages", []):
                        contact_info = value.get("contacts", [{}])[0] if value.get("contacts") else {}
                        contact_name = contact_info.get("profile", {}).get("name", "")
                        from_number = msg.get("from", "")
                        msg_id = msg.get("id", "")
                        msg_type = msg.get("type", "text")
                        text = msg.get("text", {}).get("body", "") if msg_type == "text" else f"[{msg_type}]"

                        conv = await _upsert_conversation(
                            tid, "WHATSAPP", from_number, phone_number_id,
                            contact_name, {"wa_phone_number_id": phone_number_id, "wa_from_number": from_number}
                        )
                        ext_id = _deterministic_id(tid, "whatsapp", msg_id)
                        result = await _insert_message(
                            tid, conv["id"], ext_id, text, "IN",
                            {"sender_type": "guest", "sender_name": contact_name,
                             "wa_msg_id": msg_id, "wa_msg_type": msg_type, "provider": "META"}
                        )
                        if result:
                            messages_created += 1

        # ---- Facebook Page / Instagram Messaging + Comments ----
        elif obj in ("page", "instagram"):
            # Messaging events
            for messaging_event in entry.get("messaging", []):
                sender_id = messaging_event.get("sender", {}).get("id", "")
                recipient_id = messaging_event.get("recipient", {}).get("id", "")
                message_data = messaging_event.get("message", {})
                msg_id = message_data.get("mid", "")
                text = message_data.get("text", "")
                timestamp_ms = messaging_event.get("timestamp", 0)

                if not text or not sender_id:
                    continue

                # Determine channel
                channel = "FACEBOOK" if obj == "page" else "INSTAGRAM"

                # The recipient_id is the page/IG ID (our asset)
                asset_id = recipient_id

                conv = await _upsert_conversation(
                    tid, channel, sender_id, asset_id, "",
                    {"psid": sender_id} if channel == "FACEBOOK" else {"ig_thread_id": sender_id}
                )
                ext_id = _deterministic_id(tid, channel.lower(), msg_id)
                result = await _insert_message(
                    tid, conv["id"], ext_id, text, "IN",
                    {"sender_type": "guest", "sender_id": sender_id,
                     "mid": msg_id, "provider": "META", "channel": channel}
                )
                if result:
                    messages_created += 1

            # Comment events (feed changes)
            for change in entry.get("changes", []):
                field = change.get("field", "")
                value = change.get("value", {})

                if field in ("feed", "comments"):
                    item = value.get("item", "")
                    verb = value.get("verb", "")

                    if item == "comment" and verb in ("add", "edited"):
                        comment_id = value.get("comment_id", "")
                        post_id = value.get("post_id", "")
                        parent_id = value.get("parent_id", "")
                        message_text = value.get("message", "")
                        sender_name = value.get("from", {}).get("name", "Unknown")
                        created_time = value.get("created_time", now_utc().isoformat())
                        permalink = value.get("permalink_url", "")

                        source_type = "FACEBOOK_COMMENT" if obj == "page" else "INSTAGRAM_COMMENT"

                        result = await _upsert_comment_as_review(
                            tid, source_type, comment_id, message_text,
                            sender_name, created_time, entry_id, post_id, permalink
                        )
                        if result:
                            comments_created += 1

                # Instagram-specific comment events
                if field == "mentions" or field == "comments":
                    if isinstance(value, dict) and value.get("text"):
                        comment_id = value.get("id", value.get("comment_id", ""))
                        if comment_id:
                            result = await _upsert_comment_as_review(
                                tid, "INSTAGRAM_COMMENT", comment_id,
                                value.get("text", ""),
                                value.get("from", {}).get("username", "Unknown"),
                                now_utc().isoformat(), entry_id
                            )
                            if result:
                                comments_created += 1

    # Audit log
    if messages_created > 0 or comments_created > 0:
        await db.audit_log.insert_one({
            "id": new_id(),
            "tenant_id": tid,
            "action": "META_WEBHOOK_PROCESSED",
            "entity_type": "webhook",
            "entity_id": "meta",
            "user_id": "system",
            "details": {"messages": messages_created, "comments": comments_created},
            "created_at": now_utc().isoformat(),
        })

    return {"status": "ok", "messages_created": messages_created, "comments_created": comments_created}
