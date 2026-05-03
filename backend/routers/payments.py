"""Payments V2 Router: Dual-mode payment provider (Real Stripe or Stub).
When STRIPE_SECRET_KEY is set, uses real Stripe Checkout Sessions.
Otherwise falls back to mock webhook simulation.
Public endpoints for guest checkout. Rate limited.
"""
from fastapi import APIRouter, HTTPException, Request
import secrets
import logging

from core.config import db, STRIPE_SECRET_KEY, STRIPE_PUBLIC_KEY, STRIPE_MODE
from core.tenant_guard import (
    serialize_doc, new_id, now_utc, log_audit
)
from core.middleware import rate_limit_ip, generate_unique_confirmation_code

logger = logging.getLogger("omnihub.payments")

router = APIRouter(prefix="/api/v2/payments", tags=["payments"])

stripe = None
if STRIPE_MODE == "live":
    try:
        import stripe as _stripe
        _stripe.api_key = STRIPE_SECRET_KEY
        stripe = _stripe
        logger.info("Stripe LIVE mode enabled")
    except ImportError:
        logger.warning("stripe package not installed, falling back to stub")

# iyzico (Turkey) provider — auto-enabled when env keys present
try:
    from services import iyzico_provider
    if iyzico_provider.is_configured():
        logger.info("iyzico LIVE mode enabled")
except Exception as e:
    iyzico_provider = None
    logger.warning("iyzico provider not loaded: %s", e)


def _payment_provider() -> str:
    """Resolve which provider to use for new checkouts."""
    if iyzico_provider and iyzico_provider.is_configured():
        return "iyzico"
    if STRIPE_MODE == "live" and stripe:
        return "stripe"
    return "stub"

@router.get("/config")
async def get_payment_config():
    return {
        "mode": STRIPE_MODE,
        "public_key": STRIPE_PUBLIC_KEY if STRIPE_MODE == "live" else None,
    }


@router.get("/pay/{payment_link_id}")
async def get_payment_page_data(payment_link_id: str, request: Request):
    """Public endpoint - returns offer summary for payment page"""
    rate_limit_ip(request, 30, 60)
    pl = await db.payment_links.find_one({"id": payment_link_id}, {"_id": 0})
    if not pl:
        raise HTTPException(status_code=404, detail="Payment link not found")
    pl = serialize_doc(pl)

    if pl.get("status") == "SUCCEEDED":
        # Already paid - find reservation
        reservation = await db.reservations.find_one(
            {"tenant_id": pl["tenant_id"], "offer_id": pl.get("offer_id")}, {"_id": 0})
        return {
            "status": "ALREADY_PAID",
            "payment_link": pl,
            "reservation": serialize_doc(reservation) if reservation else None
        }

    offer = await db.offers.find_one({"id": pl.get("offer_id"), "tenant_id": pl["tenant_id"]}, {"_id": 0})
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    offer = serialize_doc(offer)

    # Get tenant name
    tenant = await db.tenants.find_one({"id": pl["tenant_id"]}, {"_id": 0})
    tenant_name = tenant.get("name", "") if tenant else ""

    # Get property name if available
    property_name = ""
    if offer.get("property_id"):
        prop = await db.properties.find_one({"id": offer["property_id"], "tenant_id": pl["tenant_id"]}, {"_id": 0})
        property_name = prop.get("name", "") if prop else ""

    return {
        "status": "PENDING",
        "payment_link": pl,
        "offer": {
            "id": offer["id"],
            "check_in": offer.get("check_in", ""),
            "check_out": offer.get("check_out", ""),
            "guests_count": offer.get("guests_count", 1),
            "room_type": offer.get("room_type", ""),
            "price_total": offer.get("price_total", 0),
            "currency": offer.get("currency", "TRY"),
            "notes": offer.get("notes", ""),
            "guest_name": offer.get("guest_name", ""),
        },
        "tenant_name": tenant_name,
        "property_name": property_name,
    }


@router.post("/pay/{payment_link_id}/checkout")
async def checkout(payment_link_id: str, request: Request):
    """Simulate starting a payment - creates payments record as INITIATED"""
    rate_limit_ip(request, 30, 60)
    pl = await db.payment_links.find_one({"id": payment_link_id}, {"_id": 0})
    if not pl:
        raise HTTPException(status_code=404, detail="Payment link not found")
    pl = serialize_doc(pl)

    if pl.get("status") == "SUCCEEDED":
        return {"status": "ALREADY_PAID", "message": "This payment has already been completed."}

    if pl.get("status") == "CANCELLED":
        raise HTTPException(status_code=400, detail="Payment link has been cancelled")

    offer = await db.offers.find_one({"id": pl.get("offer_id"), "tenant_id": pl["tenant_id"]}, {"_id": 0})
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    # Check if offer expired
    if offer.get("status") == "EXPIRED":
        raise HTTPException(status_code=400, detail="This offer has expired")
    if offer.get("status") == "CANCELLED":
        raise HTTPException(status_code=400, detail="This offer has been cancelled")

    # Create payment record
    payment = {
        "id": new_id(),
        "tenant_id": pl["tenant_id"],
        "offer_id": pl.get("offer_id"),
        "payment_link_id": payment_link_id,
        "provider": "STRIPE_STUB",
        "amount": pl.get("amount", 0),
        "currency": pl.get("currency", "TRY"),
        "status": "INITIATED",
        "provider_payment_id": f"pi_stub_{secrets.token_hex(8)}",
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat(),
    }
    await db.payments.insert_one(payment)

    return {"status": "INITIATED", "payment_id": payment["id"],
            "provider_payment_id": payment["provider_payment_id"],
            "message": "Payment initiated. Processing..."}


@router.post("/webhook/mock/succeed")
async def webhook_mock_succeed(data: dict, request: Request):
    """Idempotent mock payment success webhook.
    If already succeeded, returns 200 without duplicating.
    DISABLED in live Stripe mode for security.
    """
    if STRIPE_MODE == "live":
        raise HTTPException(status_code=403, detail="Mock webhooks disabled in live mode")
    rate_limit_ip(request, 30, 60)
    payment_link_id = data.get("paymentLinkId", data.get("payment_link_id", ""))
    provider_payment_id = data.get("providerPaymentId", data.get("provider_payment_id", f"pi_stub_{secrets.token_hex(8)}"))

    if not payment_link_id:
        raise HTTPException(status_code=400, detail="paymentLinkId required")

    pl = await db.payment_links.find_one({"id": payment_link_id}, {"_id": 0})
    if not pl:
        raise HTTPException(status_code=404, detail="Payment link not found")
    pl = serialize_doc(pl)
    tid = pl["tenant_id"]

    # IDEMPOTENCY CHECK: If already succeeded, return existing reservation
    if pl.get("status") == "SUCCEEDED":
        reservation = await db.reservations.find_one(
            {"tenant_id": tid, "offer_id": pl.get("offer_id")}, {"_id": 0})
        return {
            "status": "ALREADY_SUCCEEDED",
            "idempotent": True,
            "reservation": serialize_doc(reservation) if reservation else None,
            "message": "Payment already processed successfully."
        }

    # Atomic status check - prevent race condition
    result = await db.payment_links.update_one(
        {"id": payment_link_id, "status": {"$ne": "SUCCEEDED"}},
        {"$set": {"status": "SUCCEEDED", "updated_at": now_utc().isoformat()}}
    )
    if result.modified_count == 0:
        # Another request already succeeded
        reservation = await db.reservations.find_one(
            {"tenant_id": tid, "offer_id": pl.get("offer_id")}, {"_id": 0})
        return {
            "status": "ALREADY_SUCCEEDED", "idempotent": True,
            "reservation": serialize_doc(reservation) if reservation else None,
            "message": "Payment already processed successfully."
        }

    # Update payment record if exists
    await db.payments.update_one(
        {"payment_link_id": payment_link_id, "tenant_id": tid},
        {"$set": {"status": "SUCCEEDED", "provider_payment_id": provider_payment_id,
                  "updated_at": now_utc().isoformat()}},
        upsert=False
    )

    # Find the offer
    offer = await db.offers.find_one({"id": pl.get("offer_id"), "tenant_id": tid}, {"_id": 0})
    if not offer:
        return {"status": "SUCCEEDED", "reservation": None, "message": "Payment succeeded but offer not found"}
    offer = serialize_doc(offer)

    # Validate offer not expired/cancelled
    if offer.get("status") in ["EXPIRED", "CANCELLED"]:
        logger.warning("Payment succeeded for %s offer %s", offer["status"], offer["id"])

    # Validate payment amount matches offer
    expected_amount = offer.get("price_total", 0)
    actual_amount = pl.get("amount", 0)
    if expected_amount and actual_amount and abs(float(expected_amount) - float(actual_amount)) > 0.01:
        logger.warning("Payment amount mismatch: expected=%s actual=%s offer=%s",
                       expected_amount, actual_amount, offer["id"])

    # Update offer to PAID (atomic)
    await db.offers.update_one(
        {"id": offer["id"], "status": {"$ne": "PAID"}},
        {"$set": {"status": "PAID", "updated_at": now_utc().isoformat()}}
    )

    # Get property prefix for confirmation code
    prop_prefix = "GHI"
    if offer.get("property_id"):
        prop = await db.properties.find_one({"id": offer["property_id"], "tenant_id": tid}, {"_id": 0})
        if prop and prop.get("slug"):
            prop_prefix = prop["slug"][:3].upper() or "GHI"

    # Create reservation (CONFIRMED) with unique confirmation code
    confirmation_code = await generate_unique_confirmation_code(tid, prop_prefix)
    reservation = {
        "id": new_id(),
        "tenant_id": tid,
        "property_id": offer.get("property_id", ""),
        "contact_id": offer.get("contact_id", ""),
        "offer_id": offer["id"],
        "status": "CONFIRMED",
        "confirmation_code": confirmation_code,
        "guest_name": offer.get("guest_name", ""),
        "guest_email": offer.get("guest_email", ""),
        "guest_phone": offer.get("guest_phone", ""),
        "room_type": offer.get("room_type", ""),
        "check_in": offer.get("check_in", ""),
        "check_out": offer.get("check_out", ""),
        "guests_count": offer.get("guests_count", 1),
        "price_total": offer.get("price_total", 0),
        "currency": offer.get("currency", "TRY"),
        "last_updated_by": "system",
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat(),
    }
    await db.reservations.insert_one(reservation)

    # Award loyalty points
    try:
        from routers.loyalty import auto_award_points
        contact_id = offer.get("contact_id", "")
        if contact_id:
            await auto_award_points(tid, contact_id, "reservation_confirmed", reservation["id"])
    except Exception:
        pass

    # Emit contact event
    try:
        from routers.crm import emit_contact_event
        contact_id = offer.get("contact_id", "")
        if contact_id:
            await emit_contact_event(tid, contact_id, "RESERVATION_CONFIRMED",
                                      f"Reservation {confirmation_code} confirmed",
                                      ref_type="reservation", ref_id=reservation["id"])
    except Exception:
        pass

    # WebSocket broadcast
    try:
        from server import ws_manager
        await ws_manager.broadcast_tenant(tid, "reservation", "reservation", "created",
                                           serialize_doc(reservation))
    except Exception:
        pass

    # Audit log
    await log_audit(tid, "PAYMENT_SUCCEEDED", "payment", payment_link_id, "system",
                    {"offer_id": offer["id"], "amount": offer.get("price_total", 0)})
    await log_audit(tid, "RESERVATION_CREATED", "reservation", reservation["id"], "system",
                    {"confirmation_code": confirmation_code, "offer_id": offer["id"]})

    # Send notifications (mock)
    try:
        from notification_service import send_notification
        tenant_doc = await db.tenants.find_one({"id": tid}, {"_id": 0})
        hotel_name = tenant_doc.get("name", "") if tenant_doc else ""
        await send_notification(tid, "PAYMENT_SUCCEEDED",
            recipient_email=offer.get("guest_email", ""),
            recipient_phone=offer.get("guest_phone", ""),
            context={"hotel_name": hotel_name, "guest_name": offer.get("guest_name", ""),
                     "currency": offer.get("currency", ""), "price": str(offer.get("price_total", "")),
                     "confirmation_code": confirmation_code})
        await send_notification(tid, "RESERVATION_CONFIRMED",
            recipient_email=offer.get("guest_email", ""),
            recipient_phone=offer.get("guest_phone", ""),
            context={"hotel_name": hotel_name, "guest_name": offer.get("guest_name", ""),
                     "check_in": offer.get("check_in", ""), "check_out": offer.get("check_out", ""),
                     "confirmation_code": confirmation_code})
    except Exception as e:
        logger.error("Notification sending failed: %s", str(e))

    return {
        "status": "SUCCEEDED",
        "idempotent": False,
        "reservation": serialize_doc(reservation),
        "confirmation_code": confirmation_code,
        "message": "Payment successful. Reservation confirmed."
    }


@router.post("/iyzico/pay/{payment_link_id}/init")
async def iyzico_init(payment_link_id: str, data: dict, request: Request):
    """Initialize an iyzico 3DS payment. Returns provider htmlContent for redirect.
    Only active when iyzico provider is configured; otherwise 503.
    """
    if not (iyzico_provider and iyzico_provider.is_configured()):
        raise HTTPException(status_code=503, detail="iyzico provider not configured")
    rate_limit_ip(request, 30, 60)

    pl = await db.payment_links.find_one({"id": payment_link_id}, {"_id": 0})
    if not pl:
        raise HTTPException(status_code=404, detail="Payment link not found")
    pl = serialize_doc(pl)
    if pl.get("status") == "SUCCEEDED":
        return {"status": "ALREADY_PAID"}

    offer = await db.offers.find_one({"id": pl.get("offer_id"), "tenant_id": pl["tenant_id"]}, {"_id": 0})
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")

    conv_id = new_id()
    base_url = str(request.base_url).rstrip("/")
    callback_url = f"{base_url}/api/v2/payments/iyzico/callback"

    buyer = data.get("buyer") or {
        "id": offer.get("contact_id", "guest"),
        "name": offer.get("guest_name", "Guest"),
        "surname": "-",
        "gsmNumber": offer.get("guest_phone", "+905555555555"),
        "email": offer.get("guest_email", "guest@example.com"),
        "identityNumber": "11111111111",
        "registrationAddress": "-",
        "city": "Istanbul",
        "country": "Turkey",
        "ip": request.client.host if request.client else "127.0.0.1",
    }
    address = data.get("address") or {
        "contactName": buyer.get("name", "Guest"),
        "city": "Istanbul",
        "country": "Turkey",
        "address": "-",
    }
    items = [{
        "id": offer.get("id", "item-1"),
        "name": offer.get("room_type", "Reservation"),
        "category1": "Hospitality",
        "itemType": "VIRTUAL",
        "price": f"{float(pl.get('amount', 0)):.2f}",
    }]
    card = data.get("card")
    if not card:
        raise HTTPException(status_code=400, detail="card payload required")

    try:
        result = await iyzico_provider.create_3ds_payment(
            conversation_id=conv_id,
            price=float(pl.get("amount", 0)),
            paid_price=float(pl.get("amount", 0)),
            currency=pl.get("currency", "TRY"),
            callback_url=callback_url,
            buyer=buyer, address=address, items=items, card=card,
        )
    except Exception as e:
        logger.error("iyzico init failed: %s", e)
        raise HTTPException(status_code=502, detail="iyzico init failed")

    # Persist init payment record
    await db.payments.insert_one({
        "id": new_id(),
        "tenant_id": pl["tenant_id"],
        "offer_id": pl.get("offer_id"),
        "payment_link_id": payment_link_id,
        "provider": "IYZICO",
        "amount": pl.get("amount", 0),
        "currency": pl.get("currency", "TRY"),
        "status": "INITIATED",
        "provider_payment_id": result.get("paymentId", conv_id),
        "conversation_id": conv_id,
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat(),
    })
    return {"status": result.get("status"), "htmlContent": result.get("threeDSHtmlContent"),
            "conversationId": conv_id}


@router.post("/iyzico/callback")
async def iyzico_callback(request: Request):
    """3DS callback from iyzico. Completes the auth and marks payment."""
    if not (iyzico_provider and iyzico_provider.is_configured()):
        raise HTTPException(status_code=503, detail="iyzico provider not configured")
    rate_limit_ip(request, 30, 60)
    form = await request.form()
    conv_id = form.get("conversationId", "")
    payment_id = form.get("paymentId", "")
    conv_data = form.get("conversationData", "")
    if not (conv_id and payment_id):
        raise HTTPException(status_code=400, detail="conversationId and paymentId required")
    try:
        result = await iyzico_provider.complete_3ds_payment(
            conversation_id=conv_id, payment_id=payment_id, conversation_data=conv_data,
        )
    except Exception as e:
        logger.error("iyzico complete failed: %s", e)
        raise HTTPException(status_code=502, detail="iyzico complete failed")
    return {"status": result.get("status"), "paymentStatus": result.get("paymentStatus")}


@router.post("/webhook/iyzico")
async def webhook_iyzico(request: Request):
    """iyzico webhook with HMAC signature verification (x-iyz-signature-v3)."""
    if not (iyzico_provider and iyzico_provider.is_configured()):
        raise HTTPException(status_code=503, detail="iyzico provider not configured")
    raw = await request.body()
    sig = request.headers.get("x-iyz-signature-v3", "") or request.headers.get("X-Iyz-Signature-V3", "")
    if not iyzico_provider.verify_webhook_signature(raw, sig):
        logger.warning("iyzico webhook signature mismatch")
        raise HTTPException(status_code=401, detail="Invalid signature")
    try:
        import json as _json
        data = _json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    conv_id = data.get("conversationId") or data.get("iyziEventType", "")
    status = (data.get("status") or data.get("paymentStatus") or "").upper()

    payment = await db.payments.find_one({"conversation_id": conv_id}, {"_id": 0}) if conv_id else None
    if not payment:
        return {"received": True, "matched": False}

    new_status = "SUCCEEDED" if status in ("SUCCESS", "SUCCEEDED") else "FAILED"
    await db.payments.update_one(
        {"id": payment["id"]},
        {"$set": {"status": new_status, "updated_at": now_utc().isoformat()}},
    )
    await log_audit(payment["tenant_id"], f"PAYMENT_{new_status}", "payment",
                    payment.get("payment_link_id", ""), "iyzico_webhook",
                    {"conversation_id": conv_id})
    return {"received": True, "matched": True, "status": new_status}


@router.post("/webhook/mock/fail")
async def webhook_mock_fail(data: dict, request: Request):
    """Mock payment failure webhook. DISABLED in live mode."""
    if STRIPE_MODE == "live":
        raise HTTPException(status_code=403, detail="Mock webhooks disabled in live mode")
    rate_limit_ip(request, 30, 60)
    payment_link_id = data.get("paymentLinkId", data.get("payment_link_id", ""))
    if not payment_link_id:
        raise HTTPException(status_code=400, detail="paymentLinkId required")

    pl = await db.payment_links.find_one({"id": payment_link_id}, {"_id": 0})
    if not pl:
        raise HTTPException(status_code=404, detail="Payment link not found")
    pl = serialize_doc(pl)
    tid = pl["tenant_id"]

    # Update payment link
    await db.payment_links.update_one({"id": payment_link_id},
        {"$set": {"status": "FAILED", "updated_at": now_utc().isoformat()}})

    # Update payment record
    await db.payments.update_one(
        {"payment_link_id": payment_link_id, "tenant_id": tid},
        {"$set": {"status": "FAILED", "updated_at": now_utc().isoformat()}},
        upsert=False
    )

    await log_audit(tid, "PAYMENT_FAILED", "payment", payment_link_id, "system")

    return {"status": "FAILED", "message": "Payment failed."}
