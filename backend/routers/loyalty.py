"""Loyalty V2 Router: Rules, Members, Ledger, Adjust, Redeem, Enroll, Auto-award
Full tenant_guard isolation. Audit logged.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from core.config import db
from core.tenant_guard import (
    resolve_tenant, get_current_user, serialize_doc,
    new_id, now_utc, find_one_scoped, find_many_scoped, count_scoped,
    insert_scoped, update_scoped, log_audit
)

router = APIRouter(prefix="/api/v2/loyalty", tags=["loyalty"])

DEFAULT_TIERS = [
    {"name": "Silver", "min_points": 0, "perks": ["5% off room service"]},
    {"name": "Gold", "min_points": 500, "perks": ["10% off all services", "Late checkout"]},
    {"name": "Platinum", "min_points": 1500, "perks": ["20% off all services", "Late checkout", "Room upgrade", "Welcome amenity"]},
]


def _calc_tier(points: int, tiers: list) -> str:
    sorted_tiers = sorted(tiers, key=lambda t: t.get("min_points", 0), reverse=True)
    for t in sorted_tiers:
        if points >= t.get("min_points", 0):
            return t["name"]
    return tiers[0]["name"] if tiers else "Silver"


def _next_tier_info(points: int, current_tier: str, tiers: list) -> dict:
    sorted_tiers = sorted(tiers, key=lambda t: t.get("min_points", 0))
    for i, t in enumerate(sorted_tiers):
        if t["name"] == current_tier and i < len(sorted_tiers) - 1:
            nxt = sorted_tiers[i + 1]
            return {"next_tier": nxt["name"], "points_needed": max(0, nxt["min_points"] - points),
                    "progress": min(100, int(points / max(nxt["min_points"], 1) * 100))}
    return {"next_tier": None, "points_needed": 0, "progress": 100}


async def _get_rules(tenant_id: str):
    rules = await db.loyalty_rules.find_one({"tenant_id": tenant_id}, {"_id": 0})
    if not rules:
        rules = {
            "id": new_id(), "tenant_id": tenant_id, "enabled": False,
            "earn": {"per_request_closed_points": 10, "per_order_completed_points": 5,
                     "per_reservation_confirmed_points": 20},
            "tiers": DEFAULT_TIERS,
            "updated_at": now_utc().isoformat()
        }
        await db.loyalty_rules.insert_one(rules)
    return serialize_doc(rules)


async def _recalc_tier(tenant_id: str, contact_id: str):
    acct = await db.loyalty_accounts.find_one({"tenant_id": tenant_id, "contact_id": contact_id})
    if not acct:
        return
    rules = await _get_rules(tenant_id)
    tiers = rules.get("tiers", DEFAULT_TIERS)
    new_tier = _calc_tier(acct.get("points_balance", 0), tiers)
    if new_tier != acct.get("tier_name"):
        await db.loyalty_accounts.update_one({"tenant_id": tenant_id, "contact_id": contact_id},
            {"$set": {"tier_name": new_tier, "updated_at": now_utc().isoformat()}})


# ============ RULES ============
@router.get("/tenants/{tenant_slug}/rules")
async def get_rules(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    return await _get_rules(tenant["id"])


@router.put("/tenants/{tenant_slug}/rules")
async def update_rules(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    tiers = data.get("tiers", DEFAULT_TIERS)
    # Validate tiers
    names = [t.get("name") for t in tiers]
    if len(names) != len(set(names)):
        raise HTTPException(status_code=400, detail="Tier names must be unique")
    pts = [t.get("min_points", 0) for t in tiers]
    if pts != sorted(pts):
        raise HTTPException(status_code=400, detail="Tiers must have ascending min_points")
    update = {
        "enabled": data.get("enabled", False),
        "earn": data.get("earn", {}),
        "tiers": tiers,
        "last_updated_by": user.get("name", ""),
        "updated_at": now_utc().isoformat(),
    }
    existing = await db.loyalty_rules.find_one({"tenant_id": tid})
    if existing:
        await db.loyalty_rules.update_one({"tenant_id": tid}, {"$set": update})
    else:
        update["id"] = new_id()
        update["tenant_id"] = tid
        await db.loyalty_rules.insert_one(update)
    await log_audit(tid, "LOYALTY_RULES_UPDATED", "loyalty_rules", "", user.get("id", ""))
    return await _get_rules(tid)


# ============ MEMBERS ============
@router.get("/tenants/{tenant_slug}/members")
async def list_members(tenant_slug: str, q: Optional[str] = None, page: int = 1, limit: int = 30,
                        user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    accounts = await find_many_scoped("loyalty_accounts", tid, {},
                                       sort=[("points_balance", -1)], skip=(page-1)*limit, limit=limit)
    total = await count_scoped("loyalty_accounts", tid)
    # Enrich with contact info
    for acct in accounts:
        contact = await find_one_scoped("contacts", tid, {"id": acct.get("contact_id", "")})
        acct["contact"] = contact
        rules = await _get_rules(tid)
        acct["next_tier"] = _next_tier_info(acct.get("points_balance", 0), acct.get("tier_name", "Silver"),
                                              rules.get("tiers", DEFAULT_TIERS))
    return {"data": accounts, "total": total, "page": page}


@router.get("/tenants/{tenant_slug}/members/{contact_id}/ledger")
async def get_member_ledger(tenant_slug: str, contact_id: str, page: int = 1, limit: int = 50,
                             user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    entries = await find_many_scoped("loyalty_ledger", tenant["id"],
                                      {"contact_id": contact_id},
                                      sort=[("created_at", -1)], skip=(page-1)*limit, limit=limit)
    total = await count_scoped("loyalty_ledger", tenant["id"], {"contact_id": contact_id})
    return {"data": entries, "total": total, "page": page}


@router.post("/tenants/{tenant_slug}/members/{contact_id}/adjust")
async def adjust_points(tenant_slug: str, contact_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    points = data.get("points", 0)
    reason = data.get("reason", "Manual adjustment")
    if not points:
        raise HTTPException(status_code=400, detail="Points amount required")
    acct = await db.loyalty_accounts.find_one({"tenant_id": tid, "contact_id": contact_id})
    if not acct:
        raise HTTPException(status_code=404, detail="Loyalty account not found")
    new_balance = acct.get("points_balance", 0) + points
    if new_balance < 0:
        raise HTTPException(status_code=400, detail="Insufficient points")
    await db.loyalty_accounts.update_one({"tenant_id": tid, "contact_id": contact_id},
        {"$set": {"points_balance": new_balance, "updated_at": now_utc().isoformat()}})
    await insert_scoped("loyalty_ledger", tid, {
        "contact_id": contact_id, "direction": "ADJUST",
        "points": points, "reason": reason,
        "created_by_user_id": user.get("id", ""),
    })
    await _recalc_tier(tid, contact_id)
    from routers.crm import emit_contact_event
    await emit_contact_event(tid, contact_id, "LOYALTY_ADJUSTED",
                              f"{'+'if points>0 else ''}{points} pts: {reason}")
    await log_audit(tid, "LOYALTY_ADJUSTED", "loyalty", contact_id, user.get("id", ""),
                    {"points": points, "reason": reason})
    return {"new_balance": new_balance}


@router.post("/tenants/{tenant_slug}/members/{contact_id}/redeem")
async def redeem_points(tenant_slug: str, contact_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    points = abs(data.get("points", 0))
    reason = data.get("reason", "Redemption")
    if not points:
        raise HTTPException(status_code=400, detail="Points required")
    acct = await db.loyalty_accounts.find_one({"tenant_id": tid, "contact_id": contact_id})
    if not acct:
        raise HTTPException(status_code=404, detail="Account not found")
    if acct.get("points_balance", 0) < points:
        raise HTTPException(status_code=400, detail="Insufficient points")
    new_balance = acct["points_balance"] - points
    await db.loyalty_accounts.update_one({"tenant_id": tid, "contact_id": contact_id},
        {"$set": {"points_balance": new_balance, "updated_at": now_utc().isoformat()}})
    await insert_scoped("loyalty_ledger", tid, {
        "contact_id": contact_id, "direction": "SPEND",
        "points": -points, "reason": reason,
    })
    await _recalc_tier(tid, contact_id)
    from routers.crm import emit_contact_event
    await emit_contact_event(tid, contact_id, "LOYALTY_REDEEMED", f"-{points} pts: {reason}")
    await log_audit(tid, "LOYALTY_REDEEMED", "loyalty", contact_id, user.get("id", ""),
                    {"points": points, "reason": reason})
    return {"new_balance": new_balance}


@router.post("/tenants/{tenant_slug}/enroll")
async def enroll_loyalty(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    contact_id = data.get("contact_id", "")
    if not contact_id:
        raise HTTPException(status_code=400, detail="contact_id required")
    existing = await db.loyalty_accounts.find_one({"tenant_id": tid, "contact_id": contact_id})
    if existing:
        return serialize_doc(existing)
    rules = await _get_rules(tid)
    tiers = rules.get("tiers", DEFAULT_TIERS)
    tier_name = tiers[0]["name"] if tiers else "Silver"
    acct = await insert_scoped("loyalty_accounts", tid, {
        "contact_id": contact_id, "points_balance": 0,
        "tier_name": tier_name, "enrolled_at": now_utc().isoformat(),
    })
    from routers.crm import emit_contact_event
    await emit_contact_event(tid, contact_id, "LOYALTY_ENROLLED", "Enrolled in loyalty program")
    await log_audit(tid, "LOYALTY_ENROLLED", "loyalty", contact_id, user.get("id", ""))
    return acct


# ============ AUTO-AWARD (called by other routers) ============
async def auto_award_points(tenant_id: str, contact_id: str, event_type: str, ref_id: str = ""):
    """Called by hotel/restaurant routers on status transitions.
    event_type: request_closed | order_completed | reservation_confirmed
    """
    if not contact_id:
        return
    rules = await _get_rules(tenant_id)
    if not rules.get("enabled"):
        return
    earn = rules.get("earn", {})
    points = 0
    reason = ""
    if event_type == "request_closed":
        points = earn.get("per_request_closed_points", 0)
        reason = "Request completed"
    elif event_type == "order_completed":
        points = earn.get("per_order_completed_points", 0)
        reason = "Order completed"
    elif event_type == "reservation_confirmed":
        points = earn.get("per_reservation_confirmed_points", 0)
        reason = "Reservation confirmed"
    if points <= 0:
        return
    # Ensure loyalty account exists
    acct = await db.loyalty_accounts.find_one({"tenant_id": tenant_id, "contact_id": contact_id})
    if not acct:
        return  # Not enrolled
    new_balance = acct.get("points_balance", 0) + points
    await db.loyalty_accounts.update_one({"tenant_id": tenant_id, "contact_id": contact_id},
        {"$set": {"points_balance": new_balance, "updated_at": now_utc().isoformat()}})
    await insert_scoped("loyalty_ledger", tenant_id, {
        "contact_id": contact_id, "direction": "EARN",
        "points": points, "reason": reason,
        "ref_type": event_type, "ref_id": ref_id,
    })
    await _recalc_tier(tenant_id, contact_id)
    from routers.crm import emit_contact_event
    await emit_contact_event(tenant_id, contact_id, "LOYALTY_EARNED", f"+{points} pts: {reason}",
                              ref_type=event_type, ref_id=ref_id)
