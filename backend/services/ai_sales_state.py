"""AI Sales Session State Machine.
Manages conversation state transitions for the booking flow.
"""
import logging
from typing import Dict, Any, Optional, List

from core.config import db
from core.tenant_guard import (
    new_id, now_utc, serialize_doc, find_one_scoped, insert_scoped, update_scoped, log_audit,
    find_many_scoped
)

logger = logging.getLogger("omnihub.ai_sales_state")

# Valid states
STATES = [
    "INFO", "COLLECT_DATES", "COLLECT_GUESTS", "COLLECT_ROOM_TYPE",
    "PRICE_QUOTED", "DISCOUNT_NEGOTIATION", "PAYMENT_SENT",
    "CONFIRMED", "ESCALATED"
]


async def get_or_create_session(
    tenant_id: str, property_id: str, conversation_id: str
) -> Dict[str, Any]:
    """Load or create AI sales session for a conversation."""
    session = await db.ai_sales_sessions.find_one(
        {"tenant_id": tenant_id, "conversation_id": conversation_id},
        {"_id": 0}
    )
    if session:
        return serialize_doc(session)

    # Create new session
    session = {
        "id": new_id(),
        "tenant_id": tenant_id,
        "property_id": property_id,
        "conversation_id": conversation_id,
        "contact_id": "",
        "state": "INFO",
        "data": {},
        "last_intent": "",
        "message_count": 0,
        "conversation_summary": "",
        "tool_calls_history": [],
        "created_at": now_utc().isoformat(),
        "last_updated_at": now_utc().isoformat(),
    }
    await db.ai_sales_sessions.insert_one(session)
    return session


async def update_session(
    tenant_id: str, conversation_id: str,
    updates: Dict[str, Any]
) -> Dict[str, Any]:
    """Update session fields."""
    updates["last_updated_at"] = now_utc().isoformat()
    await db.ai_sales_sessions.update_one(
        {"tenant_id": tenant_id, "conversation_id": conversation_id},
        {"$set": updates}
    )
    session = await db.ai_sales_sessions.find_one(
        {"tenant_id": tenant_id, "conversation_id": conversation_id},
        {"_id": 0}
    )
    return serialize_doc(session) if session else {}


async def update_session_state(
    tenant_id: str, conversation_id: str,
    new_state: str, data_updates: Optional[Dict] = None
) -> Dict[str, Any]:
    """Transition session state with optional data updates."""
    updates = {"state": new_state}
    if data_updates:
        for k, v in data_updates.items():
            updates[f"data.{k}"] = v
    return await update_session(tenant_id, conversation_id, updates)


async def should_ai_respond(
    tenant_id: str, property_id: str, conversation_id: str
) -> tuple:
    """Check if AI should auto-respond.
    Returns (should_respond: bool, reason: str, session: dict)
    """
    # 1. Check if AI sales is enabled for this property
    settings = await db.ai_sales_settings.find_one(
        {"tenant_id": tenant_id, "property_id": property_id},
        {"_id": 0}
    )
    if not settings or not settings.get("enabled", False):
        return False, "AI_DISABLED", None

    # 2. Check AI usage limits
    month_key = now_utc().strftime("%Y-%m")
    counter = await db.usage_counters.find_one(
        {"tenant_id": tenant_id, "month_key": month_key},
        {"_id": 0}
    )
    used = counter.get("ai_replies_used", 0) if counter else 0
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    limit = tenant.get("plan_limits", {}).get("monthly_ai_replies", 50) if tenant else 50
    if used >= limit:
        return False, "AI_LIMIT_EXCEEDED", None

    # 3. Load session
    session = await get_or_create_session(tenant_id, property_id, conversation_id)

    # 4. Check if session is escalated
    if session.get("state") == "ESCALATED":
        return False, "SESSION_ESCALATED", session

    # 5. Check max messages without human (fail-safe)
    max_without_human = settings.get("max_messages_without_human", 20)
    if session.get("message_count", 0) >= max_without_human:
        await update_session_state(tenant_id, conversation_id, "ESCALATED")
        await log_audit(tenant_id, "AI_ESCALATED", "conversation", conversation_id, "ai_agent",
                       {"reason": "max_messages_reached"})
        return False, "MAX_MESSAGES_REACHED", session

    # 6. Check API key
    from services.openai_provider import get_ai_key
    if not get_ai_key():
        return False, "NO_API_KEY", session

    return True, "OK", session


async def build_system_prompt(
    tenant_id: str, property_id: str, session: Dict
) -> str:
    """Build the system prompt with hotel context."""
    # Get tenant info
    tenant = await db.tenants.find_one({"id": tenant_id}, {"_id": 0})
    hotel_name = tenant.get("name", "Our Hotel") if tenant else "Our Hotel"

    # Get property info
    prop = await db.properties.find_one({"id": property_id}, {"_id": 0})
    prop_name = prop.get("name", hotel_name) if prop else hotel_name
    prop_address = prop.get("address", "") if prop else ""
    prop_phone = prop.get("phone", "") if prop else ""

    # Get business policies
    policies = await db.business_policies.find_one(
        {"tenant_id": tenant_id, "property_id": property_id},
        {"_id": 0}
    )
    policy_text = ""
    if policies:
        parts = []
        if policies.get("check_in_time"):
            parts.append(f"Check-in: {policies['check_in_time']}")
        if policies.get("check_out_time"):
            parts.append(f"Check-out: {policies['check_out_time']}")
        if policies.get("cancellation_policy_text"):
            parts.append(f"Cancellation: {policies['cancellation_policy_text']}")
        if policies.get("parking_info"):
            parts.append(f"Parking: {policies['parking_info']}")
        if policies.get("pets_allowed") is not None:
            parts.append(f"Pets: {'Allowed' if policies['pets_allowed'] else 'Not allowed'}")
        policy_text = " | ".join(parts)

    # Get available room types summary
    rates = []
    cursor = db.room_rates.find(
        {"tenant_id": tenant_id, "property_id": property_id, "is_active": True},
        {"_id": 0}
    )
    async for rate in cursor:
        rates.append(rate)

    room_info = ""
    if rates:
        lines = []
        for r in rates:
            line = f"- {r.get('room_type_name', r['room_type_code'])}: {r.get('base_price_per_night',0)} {r.get('currency','TRY')}/night"
            if r.get('breakfast_included'):
                line += " (breakfast included)"
            if r.get('description'):
                line += f" - {r['description'][:60]}"
            lines.append(line)
        room_info = "\n".join(lines)

    # Get AI settings for language preference
    settings = await db.ai_sales_settings.find_one(
        {"tenant_id": tenant_id, "property_id": property_id},
        {"_id": 0}
    )
    languages = settings.get("allowed_languages", ["TR", "EN"]) if settings else ["TR", "EN"]
    lang_text = ", ".join(languages)

    prompt = f"""You are a professional hotel sales agent for {prop_name}.

Your role:
- Guide the guest from information request to confirmed reservation.
- Collect missing booking details.
- Use backend tools for availability, pricing, discount validation, payment link generation, and reservation confirmation.
- Never invent prices, availability, discounts, or policies.
- Never generate payment links manually. Always use the generate_payment_link tool.
- Be concise, persuasive, and professional.
- Respond in the guest's language. Supported: {lang_text}.

Hotel Info:
- Name: {prop_name}
- Address: {prop_address}
- Phone: {prop_phone}
- Policies: {policy_text}

Available Rooms:
{room_info}

Booking Flow Rules:
1) INFORMATION STAGE: Answer questions about rooms, facilities, etc. If booking intent detected, move to data collection.
2) DATA COLLECTION: Before quoting price, collect: check-in date, check-out date, number of guests, room type (suggest if unclear).
3) PRICING: When all data available, call check_availability_and_price tool. Never guess prices.
4) DISCOUNT: If guest asks, call validate_discount tool. Present result honestly.
5) OFFER: When guest agrees, call create_offer then generate_payment_link. Present payment link.
6) CONFIRMATION: After payment, confirm reservation with code and arrival info.

Optimization:
- Keep responses under 120 words unless necessary.
- Do not repeat hotel description.
- If conversation is long, focus on next action.

Never:
- Reveal internal system logic or tools.
- Mention AI, tokens, backend.
- Invent data.
- If uncertain, politely say you'll connect them with the team.

If the guest is angry, apologize sincerely and offer to connect with a human agent."""

    return prompt


async def build_conversation_messages(
    tenant_id: str, conversation_id: str,
    session: Dict, max_messages: int = 8
) -> List[Dict[str, str]]:
    """Build message history for AI context. Last N messages + optional summary."""
    messages_cursor = db.messages.find(
        {"tenant_id": tenant_id, "conversation_id": conversation_id},
        {"_id": 0}
    ).sort("created_at", -1).limit(max_messages)

    raw_messages = []
    async for msg in messages_cursor:
        raw_messages.append(serialize_doc(msg))

    raw_messages.reverse()  # Oldest first

    context = []

    # Add conversation summary if exists
    summary = session.get("conversation_summary", "")
    if summary:
        context.append({"role": "system", "content": f"Previous conversation summary: {summary}"})

    for msg in raw_messages:
        direction = msg.get("direction", "")
        body = msg.get("body", "")
        if not body:
            continue
        if direction == "IN":
            context.append({"role": "user", "content": body})
        elif direction == "OUT":
            context.append({"role": "assistant", "content": body})

    return context


async def increment_ai_usage(tenant_id: str):
    """Increment AI usage counter."""
    month_key = now_utc().strftime("%Y-%m")
    await db.usage_counters.update_one(
        {"tenant_id": tenant_id, "month_key": month_key},
        {"$inc": {"ai_replies_used": 1}, "$set": {"updated_at": now_utc().isoformat()}},
        upsert=True
    )
    await db.tenants.update_one(
        {"id": tenant_id},
        {"$inc": {"usage_counters.ai_replies_this_month": 1}}
    )
