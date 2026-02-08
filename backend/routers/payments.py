"""Payments V2 Router: Mock payment provider with idempotent webhook simulation.
No real payment gateway. Provides provider interface + StripeStub.
Public endpoints for guest checkout.
"""
from fastapi import APIRouter, HTTPException, Request
import secrets

from core.config import db
from core.tenant_guard import (
    serialize_doc, new_id, now_utc,
    find_one_scoped, insert_scoped, update_scoped, log_audit
)

router = APIRouter(prefix="/api/v2/payments", tags=["payments"])


def _generate_confirmation_code() -> str:
    """Generate a human-readable confirmation code like RES-XXXXXX"""
    return f"RES-{secrets.token_hex(3).upper()}"


@router.get("/pay/{payment_link_id}")
async def get_payment_page_data(payment_link_id: str):
    """Public endpoint - returns offer summary for payment page"""
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

    offer = await db.offers.find_one({"id": pl.get("offer_id")}, {"_id": 0})
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    offer = serialize_doc(offer)

    # Get tenant name
    tenant = await db.tenants.find_one({"id": pl["tenant_id"]}, {"_id": 0})
    tenant_name = tenant.get("name", "") if tenant else ""

    # Get property name if available
    property_name = ""
    if offer.get("property_id"):
        prop = await db.properties.find_one({"id": offer["property_id"]}, {"_id": 0})
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
async def checkout(payment_link_id: str):
    """Simulate starting a payment - creates payments record as INITIATED"""
    pl = await db.payment_links.find_one({"id": payment_link_id}, {"_id": 0})
    if not pl:
        raise HTTPException(status_code=404, detail="Payment link not found")
    pl = serialize_doc(pl)

    if pl.get("status") == "SUCCEEDED":
        return {"status": "ALREADY_PAID", "message": "This payment has already been completed."}

    if pl.get("status") == "CANCELLED":
        raise HTTPException(status_code=400, detail="Payment link has been cancelled")

    offer = await db.offers.find_one({"id": pl.get("offer_id")}, {"_id": 0})
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
async def webhook_mock_succeed(data: dict):
    """Idempotent mock payment success webhook.
    If already succeeded, returns 200 without duplicating.
    """
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

    # Update payment link to SUCCEEDED
    await db.payment_links.update_one({"id": payment_link_id},
        {"$set": {"status": "SUCCEEDED", "updated_at": now_utc().isoformat()}})

    # Update payment record if exists
    await db.payments.update_one(
        {"payment_link_id": payment_link_id, "tenant_id": tid},
        {"$set": {"status": "SUCCEEDED", "provider_payment_id": provider_payment_id,
                  "updated_at": now_utc().isoformat()}},
        upsert=False
    )

    # Find the offer
    offer = await db.offers.find_one({"id": pl.get("offer_id")}, {"_id": 0})
    if not offer:
        return {"status": "SUCCEEDED", "reservation": None, "message": "Payment succeeded but offer not found"}
    offer = serialize_doc(offer)

    # Update offer to PAID
    await db.offers.update_one({"id": offer["id"]},
        {"$set": {"status": "PAID", "updated_at": now_utc().isoformat()}})

    # Create reservation (CONFIRMED)
    confirmation_code = _generate_confirmation_code()
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

    return {
        "status": "SUCCEEDED",
        "idempotent": False,
        "reservation": serialize_doc(reservation),
        "confirmation_code": confirmation_code,
        "message": "Payment successful. Reservation confirmed."
    }


@router.post("/webhook/mock/fail")
async def webhook_mock_fail(data: dict):
    """Mock payment failure webhook"""
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
