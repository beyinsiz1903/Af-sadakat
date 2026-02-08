"""AI Sales Router: Admin settings for room rates, discount rules, policies.
Plus manual AI chat endpoint for testing.
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Optional, Dict
import logging
import json
from functools import partial

from core.config import db, PUBLIC_BASE_URL
from core.tenant_guard import (
    resolve_tenant, get_current_user, serialize_doc,
    new_id, now_utc, find_one_scoped, find_many_scoped,
    insert_scoped, update_scoped, log_audit
)
from services.ai_sales_tools import TOOLS_SCHEMA, execute_tool
from services.ai_sales_state import (
    get_or_create_session, update_session, update_session_state,
    should_ai_respond, build_system_prompt, build_conversation_messages,
    increment_ai_usage
)
from services.openai_provider import call_chat_with_tools, get_ai_key

logger = logging.getLogger("omnihub.ai_sales")

router = APIRouter(prefix="/api/v2/ai-sales", tags=["ai-sales"])


# ============ ADMIN: AI Sales Settings ============

@router.get("/tenants/{tenant_slug}/settings")
async def get_ai_settings(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    # Get active property from header or first property
    properties = await find_many_scoped("properties", tid, {"is_active": True}, limit=100)
    results = []
    for prop in properties:
        pid = prop["id"]
        settings = await db.ai_sales_settings.find_one(
            {"tenant_id": tid, "property_id": pid}, {"_id": 0}
        )
        if not settings:
            settings = {"tenant_id": tid, "property_id": pid, "enabled": False,
                       "allowed_languages": ["TR", "EN"], "max_messages_without_human": 20,
                       "escalation_keywords": ["complaint", "manager", "lawyer", "sikayet", "mudur"]}
        settings["property_name"] = prop.get("name", "")
        results.append(serialize_doc(settings))
    return results


@router.put("/tenants/{tenant_slug}/properties/{property_id}/settings")
async def update_ai_settings(tenant_slug: str, property_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    if user.get("role") not in ["owner", "admin", "manager"]:
        raise HTTPException(status_code=403, detail="Only Manager/Admin can update AI settings")

    allowed_fields = ["enabled", "allowed_languages", "max_messages_without_human", "escalation_keywords"]
    update = {k: v for k, v in data.items() if k in allowed_fields}
    update["tenant_id"] = tid
    update["property_id"] = property_id
    update["updated_at"] = now_utc().isoformat()
    update["last_updated_by"] = user.get("name", "")

    await db.ai_sales_settings.update_one(
        {"tenant_id": tid, "property_id": property_id},
        {"$set": update},
        upsert=True
    )
    await log_audit(tid, "AI_SETTINGS_UPDATED", "ai_sales_settings", property_id, user.get("id", ""))
    return {"ok": True}


# ============ ADMIN: Room Rates ============

@router.get("/tenants/{tenant_slug}/properties/{property_id}/room-rates")
async def list_room_rates(tenant_slug: str, property_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    rates = await find_many_scoped("room_rates", tenant["id"],
                                    {"property_id": property_id}, limit=100)
    return rates


@router.post("/tenants/{tenant_slug}/properties/{property_id}/room-rates")
async def create_room_rate(tenant_slug: str, property_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    if user.get("role") not in ["owner", "admin", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    code = data.get("room_type_code", "").strip().lower()
    if not code:
        raise HTTPException(status_code=400, detail="room_type_code required")

    # Check uniqueness
    existing = await db.room_rates.find_one(
        {"tenant_id": tid, "property_id": property_id, "room_type_code": code},
        {"_id": 0}
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"Rate for '{code}' already exists")

    rate = await insert_scoped("room_rates", tid, {
        "property_id": property_id,
        "room_type_code": code,
        "room_type_name": data.get("room_type_name", code.title()),
        "description": data.get("description", ""),
        "base_price_per_night": float(data.get("base_price_per_night", 0)),
        "currency": data.get("currency", "TRY"),
        "weekend_multiplier": float(data.get("weekend_multiplier", 1.0)),
        "season_rules": data.get("season_rules", []),
        "min_stay_nights": int(data.get("min_stay_nights", 1)),
        "max_guests": int(data.get("max_guests", 2)),
        "refundable": data.get("refundable", True),
        "breakfast_included": data.get("breakfast_included", False),
        "is_active": True,
        "last_updated_by": user.get("name", ""),
    })
    await log_audit(tid, "ROOM_RATE_CREATED", "room_rate", rate["id"], user.get("id", ""))
    return rate


@router.patch("/tenants/{tenant_slug}/properties/{property_id}/room-rates/{rate_id}")
async def update_room_rate(tenant_slug: str, property_id: str, rate_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    if user.get("role") not in ["owner", "admin", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    allowed = ["room_type_name", "description", "base_price_per_night", "currency",
               "weekend_multiplier", "season_rules", "min_stay_nights", "max_guests",
               "refundable", "breakfast_included", "is_active"]
    update = {k: v for k, v in data.items() if k in allowed}
    update["last_updated_by"] = user.get("name", "")

    updated = await update_scoped("room_rates", tid, rate_id, update)
    if not updated:
        raise HTTPException(status_code=404, detail="Rate not found")
    await log_audit(tid, "ROOM_RATE_UPDATED", "room_rate", rate_id, user.get("id", ""))
    return updated


@router.delete("/tenants/{tenant_slug}/properties/{property_id}/room-rates/{rate_id}")
async def delete_room_rate(tenant_slug: str, property_id: str, rate_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    if user.get("role") not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Only Admin can delete rates")
    result = await db.room_rates.delete_one({"id": rate_id, "tenant_id": tid})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Rate not found")
    await log_audit(tid, "ROOM_RATE_DELETED", "room_rate", rate_id, user.get("id", ""))
    return {"deleted": True}


# ============ ADMIN: Discount Rules ============

@router.get("/tenants/{tenant_slug}/properties/{property_id}/discount-rules")
async def get_discount_rules(tenant_slug: str, property_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    rules = await db.discount_rules.find_one(
        {"tenant_id": tenant["id"], "property_id": property_id}, {"_id": 0}
    )
    if not rules:
        rules = {"tenant_id": tenant["id"], "property_id": property_id,
                "enabled": False, "max_discount_percent": 10,
                "min_nights_for_discount": 3, "blackouts": []}
    return serialize_doc(rules)


@router.put("/tenants/{tenant_slug}/properties/{property_id}/discount-rules")
async def update_discount_rules(tenant_slug: str, property_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    if user.get("role") not in ["owner", "admin", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    allowed = ["enabled", "max_discount_percent", "min_nights_for_discount",
               "blackouts", "allowed_channels"]
    update = {k: v for k, v in data.items() if k in allowed}
    update["tenant_id"] = tid
    update["property_id"] = property_id
    update["updated_at"] = now_utc().isoformat()
    update["last_updated_by"] = user.get("name", "")

    await db.discount_rules.update_one(
        {"tenant_id": tid, "property_id": property_id},
        {"$set": update},
        upsert=True
    )
    await log_audit(tid, "DISCOUNT_RULES_UPDATED", "discount_rules", property_id, user.get("id", ""))
    return {"ok": True}


# ============ ADMIN: Business Policies ============

@router.get("/tenants/{tenant_slug}/properties/{property_id}/policies")
async def get_policies(tenant_slug: str, property_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    policies = await db.business_policies.find_one(
        {"tenant_id": tenant["id"], "property_id": property_id}, {"_id": 0}
    )
    if not policies:
        policies = {"tenant_id": tenant["id"], "property_id": property_id,
                   "check_in_time": "14:00", "check_out_time": "12:00",
                   "cancellation_policy_text": "Free cancellation up to 48 hours before check-in.",
                   "pets_allowed": False, "smoking_policy": "Non-smoking",
                   "parking_info": "Free parking available",
                   "location_info": "", "contact_phone": ""}
    return serialize_doc(policies)


@router.put("/tenants/{tenant_slug}/properties/{property_id}/policies")
async def update_policies(tenant_slug: str, property_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    if user.get("role") not in ["owner", "admin", "manager"]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    allowed = ["check_in_time", "check_out_time", "cancellation_policy_text",
               "pets_allowed", "smoking_policy", "parking_info",
               "location_info", "contact_phone"]
    update = {k: v for k, v in data.items() if k in allowed}
    update["tenant_id"] = tid
    update["property_id"] = property_id
    update["updated_at"] = now_utc().isoformat()
    update["last_updated_by"] = user.get("name", "")

    await db.business_policies.update_one(
        {"tenant_id": tid, "property_id": property_id},
        {"$set": update},
        upsert=True
    )
    await log_audit(tid, "POLICIES_UPDATED", "business_policies", property_id, user.get("id", ""))
    return {"ok": True}


# ============ AI Chat Endpoint (used by webchat auto-reply) ============

@router.post("/tenants/{tenant_slug}/conversations/{conv_id}/ai-respond")
async def ai_respond(tenant_slug: str, conv_id: str, user=Depends(get_current_user)):
    """Manually trigger AI response for a conversation (admin action)."""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    conv = await db.conversations.find_one({"id": conv_id, "tenant_id": tid}, {"_id": 0})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Resolve property
    property_id = conv.get("property_id", "")
    if not property_id:
        # Use first active property as default
        default_prop = await db.properties.find_one({"tenant_id": tid, "is_active": True}, {"_id": 0})
        property_id = default_prop["id"] if default_prop else ""

    if not property_id:
        raise HTTPException(status_code=400, detail="No active property found")

    result = await _run_ai_response(tid, property_id, conv_id, conv.get("contact_id", ""))
    if result.get("error"):
        raise HTTPException(status_code=500, detail=result["error"])
    return result


# ============ AI Sales Session Info ============

@router.get("/tenants/{tenant_slug}/conversations/{conv_id}/session")
async def get_session_info(tenant_slug: str, conv_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    session = await db.ai_sales_sessions.find_one(
        {"tenant_id": tenant["id"], "conversation_id": conv_id}, {"_id": 0}
    )
    return serialize_doc(session) if session else {"state": "NO_SESSION"}


# ============ AI Sales Stats ============

@router.get("/tenants/{tenant_slug}/stats")
async def get_ai_stats(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    # AI usage this month
    month_key = now_utc().strftime("%Y-%m")
    counter = await db.usage_counters.find_one(
        {"tenant_id": tid, "month_key": month_key}, {"_id": 0}
    )
    used = counter.get("ai_replies_used", 0) if counter else 0
    limit_val = tenant.get("plan_limits", {}).get("monthly_ai_replies", 50)

    # AI offers created
    ai_offers = await db.offers.count_documents({"tenant_id": tid, "source": "AI_WEBCHAT"})
    ai_paid = await db.offers.count_documents({"tenant_id": tid, "source": "AI_WEBCHAT", "status": "PAID"})

    # Active AI sessions
    active_sessions = await db.ai_sales_sessions.count_documents(
        {"tenant_id": tid, "state": {"$nin": ["CONFIRMED", "ESCALATED"]}}
    )

    return {
        "ai_replies_used": used,
        "ai_replies_limit": limit_val,
        "ai_offers_created": ai_offers,
        "ai_offers_paid": ai_paid,
        "active_sessions": active_sessions,
        "month": month_key,
    }


# ============ Core AI Response Logic ============

async def _run_ai_response(
    tenant_id: str, property_id: str, conversation_id: str, contact_id: str = ""
) -> Dict:
    """Run AI response for a conversation. Called from webchat handler or admin trigger."""

    # Load/create session
    session = await get_or_create_session(tenant_id, property_id, conversation_id)

    # Build system prompt with hotel context
    system_prompt = await build_system_prompt(tenant_id, property_id, session)

    # Build conversation messages
    conv_messages = await build_conversation_messages(tenant_id, conversation_id, session)

    # Combine: system prompt + conversation
    messages = [{"role": "system", "content": system_prompt}] + conv_messages

    # Create tool executor bound to this tenant/property
    async def tool_exec(func_name, func_args):
        return await execute_tool(tenant_id, property_id, contact_id, session.get("data", {}), func_name, func_args)

    # Call AI
    result = await call_chat_with_tools(
        messages=messages,
        tools=TOOLS_SCHEMA,
        tool_executor=tool_exec,
        model="gpt-4o-mini",
        temperature=0.4,
        max_tokens=260,
    )

    if result.get("error") and result["error"] == "NO_API_KEY":
        return {"error": "NO_API_KEY", "message": "AI key not configured"}

    if result.get("error") and not result.get("content"):
        # AI failed - escalate
        await update_session(tenant_id, conversation_id, {"state": "ESCALATED"})
        await log_audit(tenant_id, "AI_ESCALATED", "conversation", conversation_id, "ai_agent",
                       {"error": result["error"]})
        return {"error": result["error"], "escalated": True}

    ai_text = result.get("content", "")
    if not ai_text:
        ai_text = "Let me connect you with our team for further assistance."

    # Store AI response as outbound message
    from core.tenant_guard import insert_scoped
    msg = await insert_scoped("messages", tenant_id, {
        "conversation_id": conversation_id,
        "direction": "OUT",
        "body": ai_text,
        "meta": {
            "sender_type": "ai",
            "ai": True,
            "model": result.get("model", "gpt-4o-mini"),
            "tokens": result.get("total_tokens", 0),
            "tool_calls": [tc["name"] for tc in result.get("tool_calls_made", [])],
        },
    })

    # Update conversation timestamp
    await db.conversations.update_one(
        {"id": conversation_id},
        {"$set": {"last_message_at": now_utc().isoformat()}}
    )

    # Increment AI usage
    await increment_ai_usage(tenant_id)

    # Update session
    msg_count = session.get("message_count", 0) + 1
    session_updates = {"message_count": msg_count}

    # Track state based on tool calls
    for tc in result.get("tool_calls_made", []):
        if tc["name"] == "check_availability_and_price":
            session_updates["state"] = "PRICE_QUOTED"
            if tc.get("result", {}).get("quotes"):
                session_updates["data.last_quotes"] = tc["result"]["quotes"]
        elif tc["name"] == "validate_discount":
            session_updates["state"] = "DISCOUNT_NEGOTIATION"
        elif tc["name"] == "create_offer":
            offer_id = tc.get("result", {}).get("offer_id", "")
            if offer_id:
                session_updates["data.offer_id"] = offer_id
        elif tc["name"] == "generate_payment_link":
            session_updates["state"] = "PAYMENT_SENT"
            pl_id = tc.get("result", {}).get("payment_link_id", "")
            if pl_id:
                session_updates["data.payment_link_id"] = pl_id

    await update_session(tenant_id, conversation_id, session_updates)

    # Log audit
    await log_audit(tenant_id, "AI_AUTO_REPLY_SENT", "message", msg["id"], "ai_agent",
                   {"tokens": result.get("total_tokens", 0),
                    "tool_calls": [tc["name"] for tc in result.get("tool_calls_made", [])]})

    # Broadcast via WebSocket
    try:
        from server import ws_manager
        await ws_manager.broadcast_tenant(tenant_id, "message", "message", "created", msg)
    except Exception as e:
        logger.warning(f"WebSocket broadcast failed: {e}")

    return {
        "message": serialize_doc(msg),
        "ai_text": ai_text,
        "tool_calls": [tc["name"] for tc in result.get("tool_calls_made", [])],
        "tokens_used": result.get("total_tokens", 0),
        "session_state": session_updates.get("state", session.get("state", "INFO")),
    }


# Make _run_ai_response accessible to inbox router
run_ai_response = _run_ai_response
