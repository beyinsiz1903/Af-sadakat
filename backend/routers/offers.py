"""Offers V2 Router: Sales flow - create, send, payment link, cancel.
Full tenant_guard isolation. Audit logged.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from datetime import timedelta
import secrets

from core.config import db, PUBLIC_BASE_URL
from core.tenant_guard import (
    resolve_tenant, get_current_user, get_optional_user, serialize_doc,
    new_id, now_utc, find_one_scoped, find_many_scoped, count_scoped,
    insert_scoped, update_scoped, log_audit
)

router = APIRouter(prefix="/api/v2/offers", tags=["offers"])

OFFER_STATUSES = ["DRAFT", "SENT", "EXPIRED", "PAID", "CANCELLED"]


def _validate_dates(check_in: str, check_out: str):
    from datetime import date as dt_date
    try:
        ci = dt_date.fromisoformat(check_in)
        co = dt_date.fromisoformat(check_out)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    if co <= ci:
        raise HTTPException(status_code=400, detail="check_out must be after check_in")
    return ci, co


@router.get("/tenants/{tenant_slug}/offers")
async def list_offers(tenant_slug: str, propertyId: Optional[str] = None,
                      status: Optional[str] = None, q: Optional[str] = None,
                      page: int = 1, limit: int = 30, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if propertyId:
        query["property_id"] = propertyId
    if status:
        query["status"] = status.upper()
    if q:
        query["$or"] = [
            {"notes": {"$regex": q, "$options": "i"}},
        ]
    skip = (page - 1) * limit
    data = await find_many_scoped("offers", tenant["id"], query,
                                   sort=[("created_at", -1)], skip=skip, limit=limit)
    total = await count_scoped("offers", tenant["id"], query)

    # Enrich with contact info
    for offer in data:
        if offer.get("contact_id"):
            contact = await find_one_scoped("contacts", tenant["id"], {"id": offer["contact_id"]})
            offer["contact"] = contact
        # Attach payment link info
        if offer.get("payment_link_id"):
            pl = await find_one_scoped("payment_links", tenant["id"], {"id": offer["payment_link_id"]})
            offer["payment_link"] = pl

    return {"data": data, "total": total, "page": page}


@router.post("/tenants/{tenant_slug}/offers")
async def create_offer(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    # Permission check
    if user.get("role") not in ["owner", "admin", "manager", "agent"]:
        raise HTTPException(status_code=403, detail="Only Agent/Manager/Admin can create offers")

    property_id = data.get("propertyId", data.get("property_id", ""))
    contact_id = data.get("contactId", data.get("contact_id", ""))
    check_in = data.get("checkIn", data.get("check_in", ""))
    check_out = data.get("checkOut", data.get("check_out", ""))
    price_total = float(data.get("priceTotal", data.get("price_total", data.get("price", 0))))
    currency = data.get("currency", "TRY")
    guests_count = int(data.get("guestsCount", data.get("guests_count", 1)))
    room_type = data.get("roomType", data.get("room_type", "standard"))
    source = data.get("source", "MANUAL")
    notes = data.get("notes", "")
    guest_name = data.get("guest_name", "")
    guest_email = data.get("guest_email", "")
    guest_phone = data.get("guest_phone", "")

    if price_total <= 0:
        raise HTTPException(status_code=400, detail="Price must be positive")

    if check_in and check_out:
        _validate_dates(check_in, check_out)

    offer = await insert_scoped("offers", tid, {
        "property_id": property_id,
        "contact_id": contact_id,
        "source": source,
        "check_in": check_in,
        "check_out": check_out,
        "guests_count": guests_count,
        "room_type": room_type,
        "price_total": price_total,
        "currency": currency,
        "status": "DRAFT",
        "expires_at": None,
        "notes": notes,
        "guest_name": guest_name,
        "guest_email": guest_email,
        "guest_phone": guest_phone,
        "payment_link_id": None,
        "last_updated_by": user.get("name", ""),
        "meta": {},
    })

    await log_audit(tid, "OFFER_CREATED", "offer", offer["id"], user.get("id", ""),
                    {"price": price_total, "source": source})

    if contact_id:
        try:
            from routers.crm import emit_contact_event
            await emit_contact_event(tid, contact_id, "OFFER_CREATED",
                                      f"Offer created: {room_type} {check_in}-{check_out} {currency} {price_total}",
                                      ref_type="offer", ref_id=offer["id"])
        except:
            pass

    return offer


@router.get("/tenants/{tenant_slug}/offers/{offer_id}")
async def get_offer(tenant_slug: str, offer_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    offer = await find_one_scoped("offers", tenant["id"], {"id": offer_id})
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if offer.get("contact_id"):
        offer["contact"] = await find_one_scoped("contacts", tenant["id"], {"id": offer["contact_id"]})
    if offer.get("payment_link_id"):
        offer["payment_link"] = await find_one_scoped("payment_links", tenant["id"], {"id": offer["payment_link_id"]})
    return offer


@router.patch("/tenants/{tenant_slug}/offers/{offer_id}")
async def update_offer(tenant_slug: str, offer_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    offer = await find_one_scoped("offers", tenant["id"], {"id": offer_id})
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if offer["status"] != "DRAFT":
        raise HTTPException(status_code=400, detail="Can only update DRAFT offers")

    allowed = ["check_in", "check_out", "guests_count", "room_type", "price_total",
               "currency", "notes", "guest_name", "guest_email", "guest_phone",
               "checkIn", "checkOut", "guestsCount", "roomType", "priceTotal", "contactId", "propertyId"]
    update = {}
    for k, v in data.items():
        if k in allowed and v is not None:
            # Normalize camelCase to snake_case
            key_map = {"checkIn": "check_in", "checkOut": "check_out", "guestsCount": "guests_count",
                       "roomType": "room_type", "priceTotal": "price_total", "contactId": "contact_id",
                       "propertyId": "property_id"}
            mapped_key = key_map.get(k, k)
            update[mapped_key] = v

    if "price_total" in update and float(update["price_total"]) <= 0:
        raise HTTPException(status_code=400, detail="Price must be positive")
    if "check_in" in update and "check_out" in update:
        _validate_dates(update["check_in"], update["check_out"])

    update["last_updated_by"] = user.get("name", "")
    updated = await update_scoped("offers", tenant["id"], offer_id, update)
    await log_audit(tenant["id"], "OFFER_UPDATED", "offer", offer_id, user.get("id", ""))
    return updated


@router.post("/tenants/{tenant_slug}/offers/{offer_id}/send")
async def send_offer(tenant_slug: str, offer_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    offer = await find_one_scoped("offers", tid, {"id": offer_id})
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if offer["status"] not in ["DRAFT"]:
        raise HTTPException(status_code=400, detail="Can only send DRAFT offers")

    expires_at = (now_utc() + timedelta(hours=48)).isoformat()
    updated = await update_scoped("offers", tid, offer_id, {
        "status": "SENT",
        "expires_at": expires_at,
        "last_updated_by": user.get("name", ""),
    })

    await log_audit(tid, "OFFER_SENT", "offer", offer_id, user.get("id", ""))

    if offer.get("contact_id"):
        try:
            from routers.crm import emit_contact_event
            await emit_contact_event(tid, offer["contact_id"], "OFFER_SENT",
                                      f"Offer sent (expires {expires_at[:10]})",
                                      ref_type="offer", ref_id=offer_id)
        except:
            pass

    return updated


@router.post("/tenants/{tenant_slug}/offers/{offer_id}/cancel")
async def cancel_offer(tenant_slug: str, offer_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    offer = await find_one_scoped("offers", tenant["id"], {"id": offer_id})
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if offer["status"] in ["PAID", "CANCELLED"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel offer with status {offer['status']}")

    updated = await update_scoped("offers", tenant["id"], offer_id, {
        "status": "CANCELLED",
        "last_updated_by": user.get("name", ""),
    })
    await log_audit(tenant["id"], "OFFER_CANCELLED", "offer", offer_id, user.get("id", ""))
    return updated


@router.post("/tenants/{tenant_slug}/offers/{offer_id}/create-payment-link")
async def create_payment_link(tenant_slug: str, offer_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    offer = await find_one_scoped("offers", tid, {"id": offer_id})
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if offer["status"] not in ["DRAFT", "SENT"]:
        raise HTTPException(status_code=400, detail="Offer must be DRAFT or SENT to create payment link")

    # Check if payment link already exists
    if offer.get("payment_link_id"):
        existing_pl = await find_one_scoped("payment_links", tid, {"id": offer["payment_link_id"]})
        if existing_pl and existing_pl.get("status") == "PENDING":
            return existing_pl

    idempotency_key = f"offer_{offer_id}_{secrets.token_hex(8)}"
    payment_link_id = new_id()
    payment_url = f"{PUBLIC_BASE_URL}/pay/{payment_link_id}"

    pl = await insert_scoped("payment_links", tid, {
        "id": payment_link_id,
        "offer_id": offer_id,
        "provider": "STRIPE_STUB",
        "url": payment_url,
        "status": "PENDING",
        "idempotency_key": idempotency_key,
        "amount": offer.get("price_total", 0),
        "currency": offer.get("currency", "TRY"),
    })

    # Update offer with payment link and set to SENT if DRAFT
    offer_update = {"payment_link_id": payment_link_id, "last_updated_by": user.get("name", "")}
    if offer["status"] == "DRAFT":
        offer_update["status"] = "SENT"
        offer_update["expires_at"] = (now_utc() + timedelta(hours=48)).isoformat()

    await update_scoped("offers", tid, offer_id, offer_update)
    await log_audit(tid, "PAYMENT_LINK_CREATED", "payment_link", payment_link_id, user.get("id", ""),
                    {"offer_id": offer_id, "url": payment_url})

    return pl
