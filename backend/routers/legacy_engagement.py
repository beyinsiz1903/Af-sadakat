"""Legacy engagement routes — extracted from server.py (T007 Faz 2).
Endpoints under /api: reviews, connectors, offers, payments/mock/succeed.
"""
import random
from fastapi import APIRouter, HTTPException
from datetime import timedelta

from core.config import db
from core.legacy_helpers import (
    now_utc, new_id, serialize_doc, get_tenant_by_slug, ws_manager,
)
from rbac import FAKE_REVIEWS, CONNECTOR_TYPES, analyze_sentiment
from connectors_legacy import StripeStubProvider

router = APIRouter(prefix="/api", tags=["legacy-engagement"])


@router.get("/tenants/{tenant_slug}/reviews")
async def list_reviews(tenant_slug: str, source: Optional[str] = None, page: int = 1, limit: int = 20):
    tenant = await get_tenant_by_slug(tenant_slug)
    query = {"tenant_id": tenant["id"]}
    if source:
        query["source"] = source.upper()
    skip = (page - 1) * limit
    reviews = await db.reviews.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.reviews.count_documents(query)
    return {"data": [serialize_doc(r) for r in reviews], "total": total, "page": page}

@router.post("/tenants/{tenant_slug}/reviews/{review_id}/reply")
async def reply_to_review(tenant_slug: str, review_id: str, data: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    review = await db.reviews.find_one({"id": review_id, "tenant_id": tenant["id"]})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    reply = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "review_id": review_id,
        "content": data.get("content", ""),
        "author": data.get("author", "Management"),
        "status": "draft",  # draft, published (stub)
        "created_at": now_utc().isoformat()
    }
    await db.review_replies.insert_one(reply)
    await db.reviews.update_one({"id": review_id}, {"$set": {"replied": True, "reply_id": reply["id"], "updated_at": now_utc().isoformat()}})
    return serialize_doc(reply)

@router.post("/tenants/{tenant_slug}/reviews/seed-stubs")
async def seed_stub_reviews(tenant_slug: str):
    """Seed fake reviews from connector stubs"""
    tenant = await get_tenant_by_slug(tenant_slug)
    existing = await db.reviews.count_documents({"tenant_id": tenant["id"]})
    if existing > 0:
        return {"message": "Reviews already exist", "count": existing}
    
    reviews = []
    for i, fr in enumerate(FAKE_REVIEWS):
        reviews.append({
            "id": new_id(),
            "tenant_id": tenant["id"],
            "source": fr["source"],
            "author": fr["author"],
            "rating": fr["rating"],
            "text": fr["text"],
            "language": fr["language"],
            "sentiment": analyze_sentiment(fr["text"]),
            "replied": False,
            "reply_id": None,
            "created_at": (now_utc() - timedelta(days=random.randint(1, 30))).isoformat(),
            "updated_at": now_utc().isoformat()
        })
    await db.reviews.insert_many(reviews)
    return {"message": f"Seeded {len(reviews)} reviews", "count": len(reviews)}

@router.get("/tenants/{tenant_slug}/connectors")
async def list_connectors(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    # Get configured connectors
    credentials = await db.connector_credentials.find({"tenant_id": tenant["id"]}, {"_id": 0}).to_list(20)
    cred_map = {c["connector_type"]: c for c in credentials}
    
    result = []
    for ct in CONNECTOR_TYPES:
        cred = cred_map.get(ct["type"])
        result.append({
            **ct,
            "configured": cred is not None,
            "enabled": cred.get("enabled", False) if cred else False,
            "credential_id": cred.get("id") if cred else None,
        })
    return result

@router.post("/tenants/{tenant_slug}/connectors")
async def configure_connector(tenant_slug: str, data: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    connector_type = data.get("connector_type", "").upper()
    
    existing = await db.connector_credentials.find_one({
        "tenant_id": tenant["id"], "connector_type": connector_type
    })
    
    if existing:
        await db.connector_credentials.update_one(
            {"id": existing["id"]},
            {"$set": {"credentials_json": data.get("credentials", {}), "enabled": data.get("enabled", True), "updated_at": now_utc().isoformat()}}
        )
        updated = await db.connector_credentials.find_one({"id": existing["id"]}, {"_id": 0})
        return serialize_doc(updated)
    
    cred = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "connector_type": connector_type,
        "credentials_json": data.get("credentials", {}),
        "enabled": data.get("enabled", True),
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat()
    }
    await db.connector_credentials.insert_one(cred)
    return serialize_doc(cred)

@router.post("/tenants/{tenant_slug}/offers")
async def create_offer(tenant_slug: str, data: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    
    offer = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "guest_name": data.get("guest_name", ""),
        "guest_email": data.get("guest_email", ""),
        "guest_phone": data.get("guest_phone", ""),
        "room_type": data.get("room_type", "standard"),
        "check_in": data.get("check_in", ""),
        "check_out": data.get("check_out", ""),
        "price": data.get("price", 0),
        "currency": data.get("currency", "TRY"),
        "inclusions": data.get("inclusions", []),
        "notes": data.get("notes", ""),
        "status": "draft",  # draft, sent, accepted, expired
        "payment_link_id": None,
        "reservation_id": None,
        "created_by": data.get("created_by", ""),
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat()
    }
    await db.offers.insert_one(offer)
    
    # Log audit
    await _log_audit(tenant["id"], "offer_created", "offer", offer["id"], data.get("created_by", ""))
    
    return serialize_doc(offer)

@router.get("/tenants/{tenant_slug}/offers")
async def list_offers(tenant_slug: str, status: Optional[str] = None):
    tenant = await get_tenant_by_slug(tenant_slug)
    query = {"tenant_id": tenant["id"]}
    if status:
        query["status"] = status
    offers = await db.offers.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [serialize_doc(o) for o in offers]

@router.post("/tenants/{tenant_slug}/offers/{offer_id}/generate-payment-link")
async def generate_payment_link(tenant_slug: str, offer_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    offer = await db.offers.find_one({"id": offer_id, "tenant_id": tenant["id"]})
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    payment_data = StripeStubProvider.create_payment_link(
        amount=offer["price"],
        currency=offer.get("currency", "TRY"),
        description=f"Reservation: {offer['room_type']} {offer.get('check_in','')} - {offer.get('check_out','')}"
    )
    
    payment_link = {
        **payment_data,
        "tenant_id": tenant["id"],
        "offer_id": offer_id,
    }
    await db.payment_links.insert_one(payment_link)
    await db.offers.update_one({"id": offer_id}, {"$set": {"payment_link_id": payment_data["id"], "status": "sent", "updated_at": now_utc().isoformat()}})
    
    return serialize_doc(payment_link)

@router.post("/payments/mock/succeed/{link_id}")
async def mock_payment_success(link_id: str):
    """Simulate payment success"""
    link = await db.payment_links.find_one({"id": link_id})
    if not link:
        raise HTTPException(status_code=404, detail="Payment link not found")
    
    # Update payment link
    await db.payment_links.update_one({"id": link_id}, {"$set": {"status": "succeeded", "paid_at": now_utc().isoformat()}})
    
    # Find offer
    offer = await db.offers.find_one({"id": link.get("offer_id")})
    if offer:
        # Create reservation
        reservation = {
            "id": new_id(),
            "tenant_id": link["tenant_id"],
            "offer_id": offer["id"],
            "payment_link_id": link_id,
            "guest_name": offer.get("guest_name", ""),
            "guest_email": offer.get("guest_email", ""),
            "guest_phone": offer.get("guest_phone", ""),
            "room_type": offer.get("room_type", ""),
            "check_in": offer.get("check_in", ""),
            "check_out": offer.get("check_out", ""),
            "price": offer.get("price", 0),
            "currency": offer.get("currency", "TRY"),
            "status": "confirmed",
            "created_at": now_utc().isoformat()
        }
        await db.reservations.insert_one(reservation)
        await db.offers.update_one({"id": offer["id"]}, {"$set": {"status": "accepted", "reservation_id": reservation["id"], "updated_at": now_utc().isoformat()}})
        
        # Broadcast
        await ws_manager.broadcast_tenant(link["tenant_id"], "reservation", "reservation", "created", serialize_doc(reservation))
        
        return {"payment": "succeeded", "reservation": serialize_doc(reservation)}
    
    return {"payment": "succeeded", "reservation": None}

