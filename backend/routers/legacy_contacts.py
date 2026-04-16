"""Legacy contact / CRM routes."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from core.config import db
from core.legacy_helpers import (
    get_tenant_by_slug, serialize_doc, now_utc,
)

logger = logging.getLogger("omnihub.legacy.contacts")
router = APIRouter()


@router.get("/tenants/{tenant_slug}/contacts")
async def list_contacts(
    tenant_slug: str, page: int = 1, limit: int = 20, search: Optional[str] = None
):
    tenant = await get_tenant_by_slug(tenant_slug)
    query = {"tenant_id": tenant["id"]}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
        ]
    skip = (page - 1) * limit
    contacts = (
        await db.contacts.find(query, {"_id": 0})
        .sort("updated_at", -1)
        .skip(skip)
        .limit(limit)
        .to_list(limit)
    )
    total = await db.contacts.count_documents(query)
    return {
        "data": [serialize_doc(c) for c in contacts],
        "total": total,
        "page": page,
        "limit": limit,
    }


@router.get("/tenants/{tenant_slug}/contacts/{contact_id}")
async def get_contact(tenant_slug: str, contact_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    contact = await db.contacts.find_one(
        {"id": contact_id, "tenant_id": tenant["id"]}, {"_id": 0}
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return serialize_doc(contact)


@router.patch("/tenants/{tenant_slug}/contacts/{contact_id}")
async def update_contact(tenant_slug: str, contact_id: str, data: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    allowed = ["name", "tags", "notes", "consent_marketing", "consent_data"]
    update_data = {k: v for k, v in data.items() if k in allowed}
    update_data["updated_at"] = now_utc().isoformat()
    await db.contacts.update_one(
        {"id": contact_id, "tenant_id": tenant["id"]}, {"$set": update_data}
    )
    updated = await db.contacts.find_one({"id": contact_id}, {"_id": 0})
    return serialize_doc(updated)


@router.get("/tenants/{tenant_slug}/contacts/{contact_id}/timeline")
async def get_contact_timeline(tenant_slug: str, contact_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    contact = await db.contacts.find_one(
        {"id": contact_id, "tenant_id": tenant["id"]}, {"_id": 0}
    )
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    timeline = []
    phone = contact.get("phone", "")
    email = contact.get("email", "")

    if phone:
        reqs = await db.guest_requests.find(
            {"tenant_id": tenant["id"], "guest_phone": phone}, {"_id": 0}
        ).to_list(100)
        for r in reqs:
            timeline.append({"type": "request", "data": serialize_doc(r), "timestamp": r.get("created_at", "")})

        ords = await db.orders.find(
            {"tenant_id": tenant["id"], "guest_phone": phone}, {"_id": 0}
        ).to_list(100)
        for o in ords:
            timeline.append({"type": "order", "data": serialize_doc(o), "timestamp": o.get("created_at", "")})

    if email:
        reqs = await db.guest_requests.find(
            {"tenant_id": tenant["id"], "guest_email": email}, {"_id": 0}
        ).to_list(100)
        for r in reqs:
            if not any(t["data"].get("id") == r.get("id") for t in timeline):
                timeline.append({"type": "request", "data": serialize_doc(r), "timestamp": r.get("created_at", "")})

    if contact.get("loyalty_account_id"):
        ledger = await db.loyalty_ledger.find(
            {"account_id": contact["loyalty_account_id"]}, {"_id": 0}
        ).to_list(100)
        for entry in ledger:
            timeline.append({"type": "loyalty", "data": serialize_doc(entry), "timestamp": entry.get("created_at", "")})

    timeline.sort(key=lambda x: x["timestamp"], reverse=True)
    return timeline
