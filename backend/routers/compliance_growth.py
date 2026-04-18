"""Compliance (GDPR/KVKK) + Growth/Referral routes.
Extracted from server.py for maintainability.
"""
from fastapi import APIRouter, HTTPException
import logging

from core.config import db
from core.tenant_guard import serialize_doc, new_id, now_utc
from core.legacy_helpers import get_tenant_by_slug
from compliance import export_guest_data, forget_guest
from referral import get_or_create_referral, get_referral_landing_data

logger = logging.getLogger("omnihub.compliance_growth")
router = APIRouter(prefix="/api", tags=["compliance-growth"])


async def _log_audit(tenant_id: str, action: str, entity_type: str, entity_id: str, user_id: str = "", details: dict = None):
    """Fail-fast audit logger preserving original semantics (GDPR endpoints
    must surface audit-log failures rather than silently succeed)."""
    await db.audit_logs.insert_one({
        "id": new_id(),
        "tenant_id": tenant_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "user_id": user_id,
        "details": details or {},
        "created_at": now_utc().isoformat(),
    })


@router.post("/tenants/{tenant_slug}/compliance/export/{contact_id}")
async def export_contact_data(tenant_slug: str, contact_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    bundle = await export_guest_data(db, tenant["id"], contact_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Contact not found")
    await _log_audit(tenant["id"], "data_export", "contact", contact_id)
    return bundle


@router.post("/tenants/{tenant_slug}/compliance/forget/{contact_id}")
async def forget_contact(tenant_slug: str, contact_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    result = await forget_guest(db, tenant["id"], contact_id)
    if not result:
        raise HTTPException(status_code=404, detail="Contact not found")
    await _log_audit(tenant["id"], "data_forget", "contact", contact_id)
    return result


@router.get("/tenants/{tenant_slug}/compliance/consent-logs")
async def list_consent_logs(tenant_slug: str, page: int = 1, limit: int = 50):
    tenant = await get_tenant_by_slug(tenant_slug)
    skip = (page - 1) * limit
    logs = await db.consent_logs.find({"tenant_id": tenant["id"]}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.consent_logs.count_documents({"tenant_id": tenant["id"]})
    return {"data": [serialize_doc(l) for l in logs], "total": total}


@router.get("/tenants/{tenant_slug}/compliance/retention")
async def get_retention_policy(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    policy = await db.retention_policies.find_one({"tenant_id": tenant["id"]}, {"_id": 0})
    if not policy:
        policy = {
            "id": new_id(),
            "tenant_id": tenant["id"],
            "retention_months": 24,
            "auto_purge": False,
            "created_at": now_utc().isoformat(),
        }
        await db.retention_policies.insert_one(policy)
    return serialize_doc(policy)


@router.patch("/tenants/{tenant_slug}/compliance/retention")
async def update_retention_policy(tenant_slug: str, data: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    update = {}
    if "retention_months" in data:
        update["retention_months"] = data["retention_months"]
    if "auto_purge" in data:
        update["auto_purge"] = data["auto_purge"]
    update["updated_at"] = now_utc().isoformat()
    await db.retention_policies.update_one({"tenant_id": tenant["id"]}, {"$set": update}, upsert=True)
    return await get_retention_policy(tenant_slug)


@router.get("/tenants/{tenant_slug}/growth/referral")
async def get_referral(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    referral = await get_or_create_referral(db, tenant["id"], tenant_slug)
    return serialize_doc(referral)


@router.get("/r/{referral_code}")
async def referral_landing(referral_code: str):
    """Public referral landing page data"""
    data = await get_referral_landing_data(db, referral_code)
    if not data:
        raise HTTPException(status_code=404, detail="Referral not found")
    return data


@router.get("/tenants/{tenant_slug}/growth/stats")
async def get_growth_stats(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    referral = await get_or_create_referral(db, tenant["id"], tenant_slug)
    events = await db.referral_events.find({"referrer_tenant_id": tenant["id"]}, {"_id": 0}).to_list(100)
    return {
        "referral": serialize_doc(referral),
        "events": [serialize_doc(e) for e in events],
        "total_clicks": referral.get("clicks", 0),
        "total_signups": referral.get("signups", 0),
        "total_rewards": referral.get("rewards_earned", 0),
    }
