"""Inbox V2 Router: Conversations, Messages, WebChat, AI Suggestions, Connector Pull
Full tenant_guard isolation. WebSocket broadcasts. AI usage enforcement.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import PlainTextResponse
from typing import Optional

from core.config import db, PUBLIC_BASE_URL
from core.tenant_guard import (
    resolve_tenant, get_current_user, get_optional_user, serialize_doc,
    new_id, now_utc, find_one_scoped, find_many_scoped, count_scoped,
    insert_scoped, update_scoped, log_audit
)
from ai_provider import generate_inbox_reply

router = APIRouter(prefix="/api/v2/inbox", tags=["inbox"])


async def _check_ai_limit(tenant_id, tenant):
    month_key = now_utc().strftime("%Y-%m")
    counter = await db.usage_counters.find_one({"tenant_id": tenant_id, "month_key": month_key}, {"_id": 0})
    if not counter:
        limit = tenant.get("plan_limits", {}).get("monthly_ai_replies", 50)
        counter = {"id": new_id(), "tenant_id": tenant_id, "month_key": month_key,
                    "ai_replies_used": 0, "ai_replies_limit": limit, "updated_at": now_utc().isoformat()}
        await db.usage_counters.insert_one(counter)
    used = counter.get("ai_replies_used", 0)
    limit = counter.get("ai_replies_limit", tenant.get("plan_limits", {}).get("monthly_ai_replies", 50))
    if used >= limit:
        raise HTTPException(status_code=402, detail={"code": "AI_LIMIT_EXCEEDED",
            "message": f"AI reply limit reached ({used}/{limit}). Upgrade your plan.", "used": used, "limit": limit})
    return used, limit

async def _increment_ai_usage(tenant_id):
    month_key = now_utc().strftime("%Y-%m")
    await db.usage_counters.update_one({"tenant_id": tenant_id, "month_key": month_key},
        {"$inc": {"ai_replies_used": 1}, "$set": {"updated_at": now_utc().isoformat()}}, upsert=True)
    await db.tenants.update_one({"id": tenant_id}, {"$inc": {"usage_counters.ai_replies_this_month": 1}})


@router.get("/tenants/{tenant_slug}/conversations")
async def list_conversations(tenant_slug: str, status: Optional[str] = None,
                              channel: Optional[str] = None, page: int = 1, limit: int = 30,
                              user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if status:
        query["status"] = status.upper()
    if channel:
        query["channel_type"] = channel.upper()
    skip_val = (page - 1) * limit
    convs = await find_many_scoped("conversations", tenant["id"], query,
                                    sort=[("last_message_at", -1)], skip=skip_val, limit=limit)
    total = await count_scoped("conversations", tenant["id"], query)
    for conv in convs:
        last_msg = await db.messages.find_one(
            {"tenant_id": tenant["id"], "conversation_id": conv["id"]},
            {"_id": 0}, sort=[("created_at", -1)])
        conv["last_message_preview"] = serialize_doc(last_msg).get("body", "")[:80] if last_msg else ""
        conv["message_count"] = await db.messages.count_documents(
            {"tenant_id": tenant["id"], "conversation_id": conv["id"]})
        if conv.get("contact_id"):
            conv["contact"] = await find_one_scoped("contacts", tenant["id"], {"id": conv["contact_id"]})
    return {"data": convs, "total": total, "page": page}

@router.get("/tenants/{tenant_slug}/conversations/{conv_id}")
async def get_conversation(tenant_slug: str, conv_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    conv = await find_one_scoped("conversations", tenant["id"], {"id": conv_id})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await find_many_scoped("messages", tenant["id"],
                                       {"conversation_id": conv_id}, sort=[("created_at", 1)], limit=500)
    contact = None
    if conv.get("contact_id"):
        contact = await find_one_scoped("contacts", tenant["id"], {"id": conv["contact_id"]})
    return {"conversation": conv, "messages": messages, "contact": contact}

@router.post("/tenants/{tenant_slug}/conversations/{conv_id}/assign")
async def assign_conversation(tenant_slug: str, conv_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    updated = await update_scoped("conversations", tenant["id"], conv_id, {"assigned_user_id": data.get("userId", "")})
    if not updated:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await log_audit(tenant["id"], "conversation_assigned", "conversation", conv_id, user.get("id", ""))
    return updated

@router.post("/tenants/{tenant_slug}/conversations/{conv_id}/close")
async def close_conversation(tenant_slug: str, conv_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    updated = await update_scoped("conversations", tenant["id"], conv_id, {"status": "CLOSED"})
    await log_audit(tenant["id"], "conversation_closed", "conversation", conv_id, user.get("id", ""))
    return updated

@router.post("/tenants/{tenant_slug}/conversations/{conv_id}/reopen")
async def reopen_conversation(tenant_slug: str, conv_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    updated = await update_scoped("conversations", tenant["id"], conv_id, {"status": "OPEN"})
    await log_audit(tenant["id"], "conversation_reopened", "conversation", conv_id, user.get("id", ""))
    return updated

@router.post("/tenants/{tenant_slug}/conversations/{conv_id}/messages")
async def send_agent_message(tenant_slug: str, conv_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    conv = await find_one_scoped("conversations", tenant["id"], {"id": conv_id})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    body = data.get("text", data.get("body", "")).strip()
    if not body:
        raise HTTPException(status_code=400, detail="Message body required")
    msg = await insert_scoped("messages", tenant["id"], {
        "conversation_id": conv_id, "direction": "OUT", "body": body,
        "last_updated_by": user.get("name", "Agent"),
        "meta": {"sender_type": "agent", "sender_id": user.get("id", "")},
    })
    await update_scoped("conversations", tenant["id"], conv_id, {"last_message_at": now_utc().isoformat()})
    await log_audit(tenant["id"], "agent_message_sent", "message", msg["id"], user.get("id", ""))
    try:
        from server import ws_manager
        await ws_manager.broadcast_tenant(tenant["id"], "message", "message", "created", msg)
    except:
        pass
    return msg

@router.post("/tenants/{tenant_slug}/conversations/{conv_id}/ai-suggest")
async def ai_suggest_inbox(tenant_slug: str, conv_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    conv = await find_one_scoped("conversations", tenant["id"], {"id": conv_id})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    used, limit = await _check_ai_limit(tenant["id"], tenant)
    last_in = await db.messages.find_one(
        {"tenant_id": tenant["id"], "conversation_id": conv_id, "direction": "IN"},
        {"_id": 0}, sort=[("created_at", -1)])
    message_text = serialize_doc(last_in).get("body", "") if last_in else ""
    result = generate_inbox_reply(message_text, tenant.get("name", "Our Hotel"))
    await _increment_ai_usage(tenant["id"])
    await log_audit(tenant["id"], "ai_suggestion_generated", "conversation", conv_id, user.get("id", ""),
                    {"intent": result["intent"], "usage": f"{used+1}/{limit}"})
    result["usage"] = {"used": used + 1, "limit": limit}
    return result

# ============ WEBCHAT ============
@router.get("/webchat/widget.js")
async def webchat_widget_js(tenantSlug: str = ""):
    js = f"""(function(){{var d=document;var s=d.createElement('div');s.id='omnihub-chat';s.innerHTML='<div style="position:fixed;bottom:20px;right:20px;z-index:9999"><a href="{PUBLIC_BASE_URL}/g/'+encodeURIComponent('{tenantSlug}')+'/chat" target="_blank" style="display:flex;align-items:center;justify-content:center;width:60px;height:60px;border-radius:50%;background:#4f46e5;color:white;text-decoration:none;box-shadow:0 4px 20px rgba(0,0,0,0.3);font-size:24px" title="Chat with us">&#128172;</a></div>';d.body.appendChild(s)}})();"""
    return PlainTextResponse(content=js, media_type="application/javascript")

@router.post("/webchat/start")
async def webchat_start(data: dict):
    tenant_slug = data.get("tenantSlug", "")
    visitor_name = data.get("visitorName", "Guest")
    tenant = await resolve_tenant(tenant_slug)
    conv = await insert_scoped("conversations", tenant["id"], {
        "channel_type": "WEBCHAT", "contact_id": None, "status": "OPEN",
        "assigned_user_id": None, "guest_name": visitor_name,
        "last_message_at": now_utc().isoformat(), "needs_attention": False,
    })
    try:
        from server import ws_manager
        await ws_manager.broadcast_tenant(tenant["id"], "conversation", "conversation", "created", conv)
    except:
        pass
    return {"conversationId": conv["id"], "tenantId": tenant["id"]}

@router.post("/webchat/{conv_id}/messages")
async def webchat_guest_message(conv_id: str, data: dict):
    body = data.get("text", data.get("body", "")).strip()
    if not body:
        raise HTTPException(status_code=400, detail="Message body required")
    conv = await db.conversations.find_one({"id": conv_id}, {"_id": 0})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    tid = conv["tenant_id"]
    msg = await insert_scoped("messages", tid, {
        "conversation_id": conv_id, "direction": "IN", "body": body,
        "meta": {"sender_type": "guest", "sender_name": data.get("senderName", "Guest")},
    })
    await update_scoped("conversations", tid, conv_id, {"last_message_at": now_utc().isoformat(),
        "guest_name": data.get("senderName", conv.get("guest_name", "Guest"))})
    urgent = ["urgent", "emergency", "complaint", "terrible", "acil", "sikayet"]
    if any(w in body.lower() for w in urgent):
        await db.conversations.update_one({"id": conv_id}, {"$set": {"needs_attention": True}})
    try:
        from server import ws_manager
        await ws_manager.broadcast_tenant(tid, "message", "message", "created", msg)
    except:
        pass
    return msg

# ============ CONNECTOR PULL ============
@router.post("/tenants/{tenant_slug}/connectors/pull-now")
async def pull_connectors_now(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    from connectors.registry import get_connector_instance
    from ai_provider import classify_sentiment
    results = {"messages_created": 0, "reviews_created": 0, "errors": []}
    creds = await db.connector_credentials.find({"tenant_id": tid, "enabled": True}, {"_id": 0}).to_list(20)
    for cred in creds:
        ctype = cred.get("connector_type", "")
        if ctype == "WEBCHAT":
            continue
        connector = get_connector_instance(ctype)
        if not connector:
            continue
        try:
            updates = await connector.fetch_updates(tid, {})
            for upd in updates:
                etype = upd.get("type", "message")
                eid = upd.get("external_id", "")
                if etype == "message":
                    existing = await db.messages.find_one({"tenant_id": tid, "meta.external_id": eid})
                    if not existing:
                        name = upd.get("from_name", "")
                        contact = None
                        if name:
                            ec = await db.contacts.find_one({"tenant_id": tid, "name": name})
                            if ec:
                                contact = serialize_doc(ec)
                            else:
                                contact = await insert_scoped("contacts", tid, {
                                    "name": name, "phone": upd.get("from_phone", ""), "email": "",
                                    "tags": [ctype.lower()], "source_channels": [ctype],
                                    "consent_marketing": False, "consent_data": True,
                                })
                        conv = await insert_scoped("conversations", tid, {
                            "channel_type": ctype, "contact_id": contact["id"] if contact else None,
                            "status": "OPEN", "guest_name": name,
                            "last_message_at": now_utc().isoformat(),
                        })
                        await insert_scoped("messages", tid, {
                            "conversation_id": conv["id"], "direction": "IN",
                            "body": upd.get("body", ""),
                            "meta": {"external_id": eid, "channel": ctype, "is_stub": True},
                        })
                        results["messages_created"] += 1
                elif etype == "review":
                    existing = await db.reviews.find_one({"tenant_id": tid, "external_id": eid})
                    if not existing:
                        sentiment = classify_sentiment(upd.get("text", ""))
                        await insert_scoped("reviews", tid, {
                            "source_type": upd.get("source_type", ctype), "external_id": eid,
                            "author_name": upd.get("author_name", ""), "rating": upd.get("rating", 3),
                            "text": upd.get("text", ""), "sentiment": sentiment, "replied": False,
                            "meta": {"is_stub": True, "language": upd.get("language", "en")},
                        })
                        results["reviews_created"] += 1
            await db.connector_credentials.update_one({"tenant_id": tid, "connector_type": ctype},
                {"$set": {"last_sync_at": now_utc().isoformat(), "status": "synced"}})
        except Exception as e:
            results["errors"].append({"connector": ctype, "error": str(e)})
    await log_audit(tid, "connectors_pull_now", "connectors", "", user.get("id", ""), results)
    return results
