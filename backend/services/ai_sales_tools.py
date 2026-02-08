"""AI Sales Agent Tool Functions.
These are called by the AI model via function/tool calling.
All are tenant + property scoped. Never invent data.
"""
import json
import logging
from datetime import date as dt_date, timedelta
from typing import Dict, Any, Optional, List

from core.config import db, PUBLIC_BASE_URL
from core.tenant_guard import (
    new_id, now_utc, find_one_scoped, find_many_scoped,
    insert_scoped, update_scoped, log_audit, serialize_doc
)

logger = logging.getLogger("omnihub.ai_sales_tools")

# ========== TOOL DEFINITIONS (for OpenAI function calling) ==========

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "check_availability_and_price",
            "description": "Check room availability and calculate total price for given dates and guest count. Call this when you have check-in, check-out dates and guest count.",
            "parameters": {
                "type": "object",
                "properties": {
                    "check_in": {"type": "string", "description": "Check-in date in YYYY-MM-DD format"},
                    "check_out": {"type": "string", "description": "Check-out date in YYYY-MM-DD format"},
                    "guests": {"type": "integer", "description": "Number of guests"},
                    "room_type_code": {"type": "string", "description": "Room type code (e.g. standard, deluxe, suite). Optional - if not specified, show all available options."}
                },
                "required": ["check_in", "check_out", "guests"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "validate_discount",
            "description": "Validate if a discount is allowed and calculate the final price. Call when guest asks for discount.",
            "parameters": {
                "type": "object",
                "properties": {
                    "original_price": {"type": "number", "description": "Original total price before discount"},
                    "requested_discount_percent": {"type": "number", "description": "Requested discount percentage (e.g. 10 for 10%)"},
                    "nights": {"type": "integer", "description": "Number of nights"}
                },
                "required": ["original_price", "requested_discount_percent"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_offer",
            "description": "Create a booking offer record in the system. Call when guest agrees to the price.",
            "parameters": {
                "type": "object",
                "properties": {
                    "check_in": {"type": "string", "description": "Check-in date YYYY-MM-DD"},
                    "check_out": {"type": "string", "description": "Check-out date YYYY-MM-DD"},
                    "guests": {"type": "integer", "description": "Number of guests"},
                    "room_type_code": {"type": "string", "description": "Room type code"},
                    "price_total": {"type": "number", "description": "Total price"},
                    "currency": {"type": "string", "description": "Currency code (default TRY)"},
                    "guest_name": {"type": "string", "description": "Guest name if known"}
                },
                "required": ["check_in", "check_out", "guests", "room_type_code", "price_total"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_payment_link",
            "description": "Generate a payment link for an offer. Call after creating an offer and guest is ready to pay.",
            "parameters": {
                "type": "object",
                "properties": {
                    "offer_id": {"type": "string", "description": "The offer ID returned from create_offer"}
                },
                "required": ["offer_id"]
            }
        }
    }
]


# ========== TOOL IMPLEMENTATIONS ==========

async def check_availability_and_price(
    tenant_id: str, property_id: str,
    check_in: str, check_out: str, guests: int,
    room_type_code: Optional[str] = None
) -> Dict[str, Any]:
    """Check availability and calculate price from room_rates collection."""
    try:
        ci = dt_date.fromisoformat(check_in)
        co = dt_date.fromisoformat(check_out)
    except (ValueError, TypeError):
        return {"error": "Invalid date format. Use YYYY-MM-DD."}

    if co <= ci:
        return {"error": "Check-out must be after check-in."}

    nights = (co - ci).days
    if nights < 1:
        return {"error": "Minimum 1 night stay required."}

    # Query room rates for this property
    rate_query = {"tenant_id": tenant_id, "property_id": property_id, "is_active": True}
    if room_type_code:
        rate_query["room_type_code"] = room_type_code

    rates = []
    cursor = db.room_rates.find(rate_query, {"_id": 0})
    async for rate in cursor:
        rates.append(serialize_doc(rate))

    if not rates:
        # Check if ANY rates exist for this tenant (maybe wrong property)
        any_rates = await db.room_rates.count_documents({"tenant_id": tenant_id})
        if any_rates == 0:
            return {"error": "No room rates configured. Please contact hotel reception."}
        return {"error": f"No rooms available for the specified criteria."}

    # Calculate price for each available room type
    quotes = []
    for rate in rates:
        # Check capacity
        capacity = rate.get("max_guests", 4)
        if guests > capacity:
            continue

        # Check min stay
        min_stay = rate.get("min_stay_nights", 1)
        if nights < min_stay:
            continue

        # Calculate price
        base_price = rate.get("base_price_per_night", 0)
        total = 0.0
        current_date = ci
        for _ in range(nights):
            day_price = base_price
            # Weekend multiplier (Friday=4, Saturday=5)
            if current_date.weekday() in (4, 5):
                day_price *= rate.get("weekend_multiplier", 1.0)
            # Season rules
            for season in rate.get("season_rules", []):
                try:
                    s_start = dt_date.fromisoformat(season["start"])
                    s_end = dt_date.fromisoformat(season["end"])
                    if s_start <= current_date <= s_end:
                        day_price *= season.get("multiplier", 1.0)
                        break
                except:
                    pass
            total += day_price
            current_date += timedelta(days=1)

        currency = rate.get("currency", "TRY")
        quotes.append({
            "room_type_code": rate["room_type_code"],
            "room_type_name": rate.get("room_type_name", rate["room_type_code"]),
            "nights": nights,
            "price_per_night_base": base_price,
            "price_total": round(total, 2),
            "currency": currency,
            "breakfast_included": rate.get("breakfast_included", False),
            "refundable": rate.get("refundable", True),
            "max_guests": capacity,
            "description": rate.get("description", ""),
        })

    if not quotes:
        return {
            "available": False,
            "message": f"No rooms available for {guests} guests and {nights} nights.",
            "alternatives": []
        }

    return {
        "available": True,
        "check_in": check_in,
        "check_out": check_out,
        "nights": nights,
        "guests": guests,
        "quotes": quotes
    }


async def validate_discount(
    tenant_id: str, property_id: str,
    original_price: float, requested_discount_percent: float,
    nights: int = 1
) -> Dict[str, Any]:
    """Validate discount against rules. Never exceed max."""
    # Get discount rules
    rules = await db.discount_rules.find_one(
        {"tenant_id": tenant_id, "property_id": property_id},
        {"_id": 0}
    )
    if not rules or not rules.get("enabled", False):
        return {
            "allowed": False,
            "approved_discount_percent": 0,
            "final_price_total": original_price,
            "reason": "Discounts are not available at this time."
        }

    max_discount = rules.get("max_discount_percent", 0)
    min_nights = rules.get("min_nights_for_discount", 1)

    # Check min nights
    if nights < min_nights:
        return {
            "allowed": False,
            "approved_discount_percent": 0,
            "final_price_total": original_price,
            "reason": f"Discount requires minimum {min_nights} nights stay."
        }

    # Check blackout dates (skip for now in MVP - could be expanded)
    # Cap discount
    approved = min(requested_discount_percent, max_discount)
    if approved <= 0:
        return {
            "allowed": False,
            "approved_discount_percent": 0,
            "final_price_total": original_price,
            "reason": "No discount available for this reservation."
        }

    final_price = round(original_price * (1 - approved / 100), 2)
    return {
        "allowed": True,
        "requested_discount_percent": requested_discount_percent,
        "approved_discount_percent": approved,
        "original_price": original_price,
        "final_price_total": final_price,
        "currency": "TRY",
        "reason": f"{approved}% discount applied." if approved == requested_discount_percent else f"Maximum discount is {max_discount}%. Applied {approved}%."
    }


async def create_offer_tool(
    tenant_id: str, property_id: str,
    check_in: str, check_out: str, guests: int,
    room_type_code: str, price_total: float,
    currency: str = "TRY", guest_name: str = "",
    contact_id: str = ""
) -> Dict[str, Any]:
    """Create an offer in the system."""
    try:
        ci = dt_date.fromisoformat(check_in)
        co = dt_date.fromisoformat(check_out)
        if co <= ci:
            return {"error": "Invalid dates"}
    except:
        return {"error": "Invalid date format"}

    if price_total <= 0:
        return {"error": "Price must be positive"}

    offer = await insert_scoped("offers", tenant_id, {
        "property_id": property_id,
        "contact_id": contact_id,
        "source": "AI_WEBCHAT",
        "check_in": check_in,
        "check_out": check_out,
        "guests_count": guests,
        "room_type": room_type_code,
        "price_total": price_total,
        "currency": currency,
        "status": "DRAFT",
        "expires_at": None,
        "notes": f"AI Sales Agent - {guest_name}",
        "guest_name": guest_name,
        "guest_email": "",
        "guest_phone": "",
        "payment_link_id": None,
        "last_updated_by": "AI Sales Agent",
        "meta": {"created_by_ai": True},
    })

    await log_audit(tenant_id, "AI_OFFER_CREATED", "offer", offer["id"], "ai_agent",
                    {"price": price_total, "room_type": room_type_code, "source": "AI_WEBCHAT"})

    return {"offer_id": offer["id"], "status": "DRAFT", "price_total": price_total, "currency": currency}


async def generate_payment_link_tool(
    tenant_id: str, property_id: str,
    offer_id: str
) -> Dict[str, Any]:
    """Generate payment link for an offer."""
    import secrets as _secrets

    offer = await find_one_scoped("offers", tenant_id, {"id": offer_id})
    if not offer:
        return {"error": "Offer not found"}

    if offer.get("status") not in ["DRAFT", "SENT"]:
        return {"error": f"Cannot create payment link for {offer.get('status')} offer"}

    # Check existing payment link
    if offer.get("payment_link_id"):
        existing = await find_one_scoped("payment_links", tenant_id, {"id": offer["payment_link_id"]})
        if existing and existing.get("status") == "PENDING":
            return {
                "payment_link_id": existing["id"],
                "payment_url": existing.get("url", ""),
                "already_exists": True
            }

    payment_link_id = new_id()
    payment_url = f"{PUBLIC_BASE_URL}/pay/{payment_link_id}"

    pl = await insert_scoped("payment_links", tenant_id, {
        "id": payment_link_id,
        "offer_id": offer_id,
        "provider": "STRIPE_STUB",
        "url": payment_url,
        "status": "PENDING",
        "idempotency_key": f"ai_offer_{offer_id}_{_secrets.token_hex(8)}",
        "amount": offer.get("price_total", 0),
        "currency": offer.get("currency", "TRY"),
        "metadata": {"offer_id": offer_id, "source": "AI_WEBCHAT"},
    })

    # Update offer with payment link and mark as SENT
    await update_scoped("offers", tenant_id, offer_id, {
        "payment_link_id": payment_link_id,
        "status": "SENT",
        "expires_at": (now_utc() + timedelta(hours=48)).isoformat(),
        "last_updated_by": "AI Sales Agent",
    })

    await log_audit(tenant_id, "AI_PAYMENT_LINK_CREATED", "payment_link", payment_link_id, "ai_agent",
                    {"offer_id": offer_id, "amount": offer.get("price_total", 0)})

    return {
        "payment_link_id": payment_link_id,
        "payment_url": payment_url,
        "already_exists": False
    }


# ========== TOOL EXECUTOR (dispatches tool calls) ==========

async def execute_tool(tenant_id: str, property_id: str,
                       contact_id: str, session_data: dict,
                       func_name: str, func_args: dict) -> Dict[str, Any]:
    """Execute a tool call from the AI model."""
    if func_name == "check_availability_and_price":
        return await check_availability_and_price(
            tenant_id, property_id,
            func_args.get("check_in", ""),
            func_args.get("check_out", ""),
            func_args.get("guests", 1),
            func_args.get("room_type_code")
        )

    elif func_name == "validate_discount":
        return await validate_discount(
            tenant_id, property_id,
            func_args.get("original_price", 0),
            func_args.get("requested_discount_percent", 0),
            func_args.get("nights", 1)
        )

    elif func_name == "create_offer":
        return await create_offer_tool(
            tenant_id, property_id,
            func_args.get("check_in", ""),
            func_args.get("check_out", ""),
            func_args.get("guests", 1),
            func_args.get("room_type_code", "standard"),
            func_args.get("price_total", 0),
            func_args.get("currency", "TRY"),
            func_args.get("guest_name", ""),
            contact_id
        )

    elif func_name == "generate_payment_link":
        return await generate_payment_link_tool(
            tenant_id, property_id,
            func_args.get("offer_id", "")
        )

    else:
        return {"error": f"Unknown tool: {func_name}"}
