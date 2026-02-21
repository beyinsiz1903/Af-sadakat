"""Loyalty Engine V3: Advanced Points Engine, Tier Management, Digital Card, Self-Service, Referral
Complete loyalty program management with dynamic rules, configurable tiers, QR-based digital cards,
member referral system, and guest self-service portal.
"""
from fastapi import APIRouter, HTTPException, Depends, Response
from typing import Optional
from datetime import datetime, timedelta
import hashlib
import json
import io
import base64

from core.config import db
from core.tenant_guard import (
    resolve_tenant, get_current_user, serialize_doc,
    new_id, now_utc, find_one_scoped, find_many_scoped, count_scoped,
    insert_scoped, update_scoped, delete_scoped, log_audit
)

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/loyalty-engine", tags=["loyalty-engine"])

# ============ TIER DEFAULTS ============
DEFAULT_TIERS_V3 = [
    {
        "name": "Bronz", "slug": "bronze", "min_points": 0, "color": "#CD7F32", "icon": "shield",
        "benefits": ["Hosgeldin puani", "Dogum gunu surprizi"],
        "multiplier": 1.0, "sort_order": 1
    },
    {
        "name": "Gumus", "slug": "silver", "min_points": 500, "color": "#C0C0C0", "icon": "award",
        "benefits": ["Oda servisi %5 indirim", "Ucretsiz WiFi yukseltme", "Oncelikli rezervasyon"],
        "multiplier": 1.25, "sort_order": 2
    },
    {
        "name": "Altin", "slug": "gold", "min_points": 1500, "color": "#FFD700", "icon": "star",
        "benefits": ["Tum hizmetlerde %10 indirim", "Gec check-out (14:00)", "Ucretsiz oda yukseltme", "Lounge erisimi"],
        "multiplier": 1.5, "sort_order": 3
    },
    {
        "name": "Platin", "slug": "platinum", "min_points": 5000, "color": "#E5E4E2", "icon": "crown",
        "benefits": ["Tum hizmetlerde %20 indirim", "Gec check-out (16:00)", "Garantili oda yukseltme",
                      "VIP lounge erisimi", "Hosgeldin amenity", "Ucretsiz havalimanı transferi", "Ozel concierge"],
        "multiplier": 2.0, "sort_order": 4
    },
]


def _calc_tier_v3(points: int, tiers: list) -> dict:
    """Calculate current tier based on points"""
    sorted_tiers = sorted(tiers, key=lambda t: t.get("min_points", 0), reverse=True)
    for t in sorted_tiers:
        if points >= t.get("min_points", 0):
            return t
    return tiers[0] if tiers else DEFAULT_TIERS_V3[0]


def _next_tier_info_v3(points: int, current_tier_slug: str, tiers: list) -> dict:
    sorted_tiers = sorted(tiers, key=lambda t: t.get("min_points", 0))
    for i, t in enumerate(sorted_tiers):
        if t.get("slug") == current_tier_slug and i < len(sorted_tiers) - 1:
            nxt = sorted_tiers[i + 1]
            needed = max(0, nxt["min_points"] - points)
            progress = min(100, int(points / max(nxt["min_points"], 1) * 100))
            return {"next_tier": nxt["name"], "next_tier_slug": nxt["slug"],
                    "points_needed": needed, "progress": progress}
    return {"next_tier": None, "next_tier_slug": None, "points_needed": 0, "progress": 100}


# ============ POINT RULES ENGINE ============
@router.get("/tenants/{tenant_slug}/point-rules")
async def list_point_rules(tenant_slug: str, user=Depends(get_current_user)):
    """List all dynamic point rules"""
    tenant = await resolve_tenant(tenant_slug)
    rules = await find_many_scoped("point_rules", tenant["id"], {}, sort=[("sort_order", 1)])
    return {"data": rules, "total": len(rules)}


@router.post("/tenants/{tenant_slug}/point-rules")
async def create_point_rule(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    """Create a dynamic point rule.
    rule_type: accommodation | spend | activity | custom
    Examples:
      - {rule_type: 'accommodation', name: 'Deluxe 3 gece', condition: {hotel:'*', room_type:'deluxe', min_nights:3}, points: 500}
      - {rule_type: 'spend', name: 'Her 100 TRY', condition: {per_amount:100, currency:'TRY'}, points: 10}
      - {rule_type: 'activity', name: 'Spa rezervasyonu', condition: {event_type:'spa_booking'}, points: 50}
      - {rule_type: 'custom', name: 'VIP davet', condition: {trigger:'manual'}, points: 1000}
    """
    tenant = await resolve_tenant(tenant_slug)
    rule = await insert_scoped("point_rules", tenant["id"], {
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "rule_type": data.get("rule_type", "activity"),
        "condition": data.get("condition", {}),
        "points": data.get("points", 0),
        "multiplier_enabled": data.get("multiplier_enabled", True),
        "active": data.get("active", True),
        "valid_from": data.get("valid_from", ""),
        "valid_until": data.get("valid_until", ""),
        "sort_order": data.get("sort_order", 0),
        "applies_to_tiers": data.get("applies_to_tiers", []),
        "property_ids": data.get("property_ids", []),
    })
    await log_audit(tenant["id"], "POINT_RULE_CREATED", "point_rules", rule["id"], user.get("id", ""))
    return rule


@router.put("/tenants/{tenant_slug}/point-rules/{rule_id}")
async def update_point_rule(tenant_slug: str, rule_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    allowed = ["name", "description", "rule_type", "condition", "points", "multiplier_enabled",
               "active", "valid_from", "valid_until", "sort_order", "applies_to_tiers", "property_ids"]
    update_data = {k: v for k, v in data.items() if k in allowed}
    result = await update_scoped("point_rules", tenant["id"], rule_id, update_data)
    return result


@router.delete("/tenants/{tenant_slug}/point-rules/{rule_id}")
async def delete_point_rule(tenant_slug: str, rule_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    await delete_scoped("point_rules", tenant["id"], rule_id)
    return {"ok": True}


# ============ TIER MANAGEMENT ============
@router.get("/tenants/{tenant_slug}/tiers")
async def list_tiers(tenant_slug: str, user=Depends(get_current_user)):
    """Get configurable tier definitions"""
    tenant = await resolve_tenant(tenant_slug)
    config = await db.tier_config.find_one({"tenant_id": tenant["id"]}, {"_id": 0})
    if not config:
        config = {
            "id": new_id(), "tenant_id": tenant["id"],
            "tiers": DEFAULT_TIERS_V3,
            "auto_upgrade": True, "auto_downgrade": True,
            "downgrade_period_days": 365,
            "evaluation_period": "yearly",
            "updated_at": now_utc().isoformat()
        }
        await db.tier_config.insert_one(config)
    return serialize_doc(config)


@router.put("/tenants/{tenant_slug}/tiers")
async def update_tiers(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    """Update tier configuration"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    tiers = data.get("tiers", DEFAULT_TIERS_V3)
    # Validate
    slugs = [t.get("slug") for t in tiers]
    if len(slugs) != len(set(slugs)):
        raise HTTPException(status_code=400, detail="Tier slugs must be unique")
    pts = [t.get("min_points", 0) for t in tiers]
    if pts != sorted(pts):
        raise HTTPException(status_code=400, detail="Tiers must have ascending min_points")

    update = {
        "tiers": tiers,
        "auto_upgrade": data.get("auto_upgrade", True),
        "auto_downgrade": data.get("auto_downgrade", True),
        "downgrade_period_days": data.get("downgrade_period_days", 365),
        "evaluation_period": data.get("evaluation_period", "yearly"),
        "updated_at": now_utc().isoformat(),
    }
    existing = await db.tier_config.find_one({"tenant_id": tid})
    if existing:
        await db.tier_config.update_one({"tenant_id": tid}, {"$set": update})
    else:
        update["id"] = new_id()
        update["tenant_id"] = tid
        await db.tier_config.insert_one(update)
    await log_audit(tid, "TIER_CONFIG_UPDATED", "tier_config", "", user.get("id", ""))
    return await list_tiers(tenant_slug, user)


@router.post("/tenants/{tenant_slug}/tiers/evaluate")
async def evaluate_all_tiers(tenant_slug: str, user=Depends(get_current_user)):
    """Re-evaluate all members' tiers based on current config"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    config = await db.tier_config.find_one({"tenant_id": tid}, {"_id": 0})
    tiers = config.get("tiers", DEFAULT_TIERS_V3) if config else DEFAULT_TIERS_V3
    auto_downgrade = config.get("auto_downgrade", True) if config else True

    members = await db.loyalty_accounts.find({"tenant_id": tid}).to_list(5000)
    upgraded = 0
    downgraded = 0
    for member in members:
        points = member.get("points_balance", 0)
        current_slug = member.get("tier_slug", "bronze")
        new_tier = _calc_tier_v3(points, tiers)
        new_slug = new_tier.get("slug", "bronze")

        if new_slug != current_slug:
            current_order = next((t.get("sort_order", 0) for t in tiers if t.get("slug") == current_slug), 0)
            new_order = new_tier.get("sort_order", 0)

            if new_order > current_order:
                # Upgrade
                await db.loyalty_accounts.update_one(
                    {"tenant_id": tid, "id": member["id"]},
                    {"$set": {"tier_name": new_tier["name"], "tier_slug": new_slug,
                              "tier_color": new_tier.get("color", "#CD7F32"),
                              "last_tier_change": now_utc().isoformat(),
                              "updated_at": now_utc().isoformat()}}
                )
                upgraded += 1
                # Log tier change
                await insert_scoped("tier_history", tid, {
                    "contact_id": member.get("contact_id", ""),
                    "from_tier": current_slug, "to_tier": new_slug,
                    "direction": "upgrade", "points_at_change": points,
                })
            elif new_order < current_order and auto_downgrade:
                # Downgrade
                await db.loyalty_accounts.update_one(
                    {"tenant_id": tid, "id": member["id"]},
                    {"$set": {"tier_name": new_tier["name"], "tier_slug": new_slug,
                              "tier_color": new_tier.get("color", "#CD7F32"),
                              "last_tier_change": now_utc().isoformat(),
                              "updated_at": now_utc().isoformat()}}
                )
                downgraded += 1
                await insert_scoped("tier_history", tid, {
                    "contact_id": member.get("contact_id", ""),
                    "from_tier": current_slug, "to_tier": new_slug,
                    "direction": "downgrade", "points_at_change": points,
                })

    return {"evaluated": len(members), "upgraded": upgraded, "downgraded": downgraded}


@router.get("/tenants/{tenant_slug}/tier-history")
async def get_tier_history(tenant_slug: str, page: int = 1, limit: int = 50, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    entries = await find_many_scoped("tier_history", tenant["id"], {},
                                      sort=[("created_at", -1)], skip=(page-1)*limit, limit=limit)
    total = await count_scoped("tier_history", tenant["id"])
    return {"data": entries, "total": total, "page": page}


# ============ DIGITAL CARD & QR ============
@router.get("/tenants/{tenant_slug}/members/{contact_id}/digital-card")
async def get_digital_card(tenant_slug: str, contact_id: str, user=Depends(get_current_user)):
    """Generate digital loyalty card data with QR code"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    acct = await db.loyalty_accounts.find_one({"tenant_id": tid, "contact_id": contact_id})
    if not acct:
        raise HTTPException(status_code=404, detail="Loyalty account not found")
    contact = await find_one_scoped("contacts", tid, {"id": contact_id})
    config = await db.tier_config.find_one({"tenant_id": tid}, {"_id": 0})
    tiers = config.get("tiers", DEFAULT_TIERS_V3) if config else DEFAULT_TIERS_V3

    tier = _calc_tier_v3(acct.get("points_balance", 0), tiers)
    next_info = _next_tier_info_v3(acct.get("points_balance", 0), tier.get("slug", "bronze"), tiers)

    card_data = {
        "member_id": acct.get("id", ""),
        "contact_id": contact_id,
        "member_name": contact.get("name", "Unknown") if contact else "Unknown",
        "member_email": contact.get("email", "") if contact else "",
        "member_phone": contact.get("phone", "") if contact else "",
        "tenant_name": tenant.get("name", ""),
        "points_balance": acct.get("points_balance", 0),
        "tier_name": tier.get("name", "Bronz"),
        "tier_slug": tier.get("slug", "bronze"),
        "tier_color": tier.get("color", "#CD7F32"),
        "tier_benefits": tier.get("benefits", []),
        "tier_multiplier": tier.get("multiplier", 1.0),
        "next_tier": next_info,
        "enrolled_at": acct.get("enrolled_at", ""),
        "referral_code": acct.get("referral_code", ""),
    }

    # Generate QR code as base64
    try:
        import qrcode
        qr_payload = json.dumps({"type": "loyalty", "member_id": acct["id"], "tenant": tenant_slug})
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_payload)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        card_data["qr_code_base64"] = base64.b64encode(buf.getvalue()).decode()
    except Exception as e:
        logger.error(f"QR generation error: {e}")
        card_data["qr_code_base64"] = ""

    return card_data


@router.get("/tenants/{tenant_slug}/members/{contact_id}/wallet-pass")
async def get_wallet_pass(tenant_slug: str, contact_id: str, wallet_type: str = "apple",
                          user=Depends(get_current_user)):
    """Get wallet pass data for Apple Wallet / Google Pay"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    acct = await db.loyalty_accounts.find_one({"tenant_id": tid, "contact_id": contact_id})
    if not acct:
        raise HTTPException(status_code=404, detail="Loyalty account not found")
    contact = await find_one_scoped("contacts", tid, {"id": contact_id})
    config = await db.tier_config.find_one({"tenant_id": tid}, {"_id": 0})
    tiers = config.get("tiers", DEFAULT_TIERS_V3) if config else DEFAULT_TIERS_V3
    tier = _calc_tier_v3(acct.get("points_balance", 0), tiers)

    pass_data = {
        "wallet_type": wallet_type,
        "pass_type": "loyalty",
        "organization_name": tenant.get("name", "Hotel"),
        "description": f"{tenant.get('name', 'Hotel')} Sadakat Karti",
        "serial_number": acct.get("id", ""),
        "member_name": contact.get("name", "") if contact else "",
        "points": acct.get("points_balance", 0),
        "tier": tier.get("name", "Bronz"),
        "tier_color": tier.get("color", "#CD7F32"),
        "barcode": {
            "format": "PKBarcodeFormatQR" if wallet_type == "apple" else "QR_CODE",
            "message": json.dumps({"member_id": acct["id"], "tenant": tenant_slug}),
            "altText": f"Uye: {acct['id'][:8]}"
        },
        "status": "ready",
        "download_url": f"/api/v2/loyalty-engine/tenants/{tenant_slug}/members/{contact_id}/wallet-pass/download?type={wallet_type}"
    }
    return pass_data


# ============ REFERRAL SYSTEM ============
@router.get("/tenants/{tenant_slug}/referral/stats")
async def get_referral_stats(tenant_slug: str, user=Depends(get_current_user)):
    """Get overall referral program stats"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    total_referrals = await count_scoped("member_referrals", tid)
    successful = await count_scoped("member_referrals", tid, {"status": "completed"})
    pending = await count_scoped("member_referrals", tid, {"status": "pending"})
    total_points_given = 0
    async for doc in db.member_referrals.aggregate([
        {"$match": {"tenant_id": tid, "status": "completed"}},
        {"$group": {"_id": None, "total": {"$sum": "$referrer_points_earned"}}}
    ]):
        total_points_given = doc.get("total", 0)

    # Top referrers
    top_referrers = []
    async for doc in db.member_referrals.aggregate([
        {"$match": {"tenant_id": tid, "status": "completed"}},
        {"$group": {"_id": "$referrer_contact_id", "count": {"$sum": 1}, "points": {"$sum": "$referrer_points_earned"}}},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]):
        contact = await find_one_scoped("contacts", tid, {"id": doc["_id"]})
        top_referrers.append({
            "contact_id": doc["_id"],
            "name": contact.get("name", "Unknown") if contact else "Unknown",
            "referral_count": doc["count"],
            "points_earned": doc["points"]
        })

    # Referral config
    config = await db.referral_config.find_one({"tenant_id": tid}, {"_id": 0})
    if not config:
        config = {
            "id": new_id(), "tenant_id": tid,
            "enabled": True,
            "referrer_points": 200,
            "referee_points": 100,
            "max_referrals_per_member": 20,
            "require_first_stay": True,
            "updated_at": now_utc().isoformat()
        }
        await db.referral_config.insert_one(config)

    return {
        "total_referrals": total_referrals,
        "successful": successful,
        "pending": pending,
        "total_points_given": total_points_given,
        "top_referrers": top_referrers,
        "config": serialize_doc(config),
    }


@router.put("/tenants/{tenant_slug}/referral/config")
async def update_referral_config(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    update = {
        "enabled": data.get("enabled", True),
        "referrer_points": data.get("referrer_points", 200),
        "referee_points": data.get("referee_points", 100),
        "max_referrals_per_member": data.get("max_referrals_per_member", 20),
        "require_first_stay": data.get("require_first_stay", True),
        "updated_at": now_utc().isoformat(),
    }
    existing = await db.referral_config.find_one({"tenant_id": tid})
    if existing:
        await db.referral_config.update_one({"tenant_id": tid}, {"$set": update})
    else:
        update["id"] = new_id()
        update["tenant_id"] = tid
        await db.referral_config.insert_one(update)
    return serialize_doc(await db.referral_config.find_one({"tenant_id": tid}, {"_id": 0}))


@router.get("/tenants/{tenant_slug}/referral/list")
async def list_referrals(tenant_slug: str, status: Optional[str] = None,
                         page: int = 1, limit: int = 30, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if status:
        query["status"] = status
    refs = await find_many_scoped("member_referrals", tenant["id"], query,
                                   sort=[("created_at", -1)], skip=(page-1)*limit, limit=limit)
    total = await count_scoped("member_referrals", tenant["id"], query)
    # Enrich
    for r in refs:
        referrer = await find_one_scoped("contacts", tenant["id"], {"id": r.get("referrer_contact_id", "")})
        referee = await find_one_scoped("contacts", tenant["id"], {"id": r.get("referee_contact_id", "")})
        r["referrer_name"] = referrer.get("name", "Unknown") if referrer else "Unknown"
        r["referee_name"] = referee.get("name", "Unknown") if referee else "Unknown"
    return {"data": refs, "total": total, "page": page}


@router.post("/tenants/{tenant_slug}/members/{contact_id}/referral-code")
async def generate_referral_code(tenant_slug: str, contact_id: str, user=Depends(get_current_user)):
    """Generate unique referral code for a member"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    acct = await db.loyalty_accounts.find_one({"tenant_id": tid, "contact_id": contact_id})
    if not acct:
        raise HTTPException(status_code=404, detail="Loyalty account not found")
    if acct.get("referral_code"):
        return {"referral_code": acct["referral_code"]}

    code = f"REF-{hashlib.md5(f'{tid}{contact_id}'.encode()).hexdigest()[:6].upper()}"
    await db.loyalty_accounts.update_one(
        {"tenant_id": tid, "contact_id": contact_id},
        {"$set": {"referral_code": code, "updated_at": now_utc().isoformat()}}
    )
    return {"referral_code": code}


@router.post("/tenants/{tenant_slug}/referral/track")
async def track_referral(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    """Track a referral: referrer_code + referee_contact_id"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    code = data.get("referral_code", "")
    referee_contact_id = data.get("referee_contact_id", "")
    if not code or not referee_contact_id:
        raise HTTPException(status_code=400, detail="referral_code and referee_contact_id required")

    referrer_acct = await db.loyalty_accounts.find_one({"tenant_id": tid, "referral_code": code})
    if not referrer_acct:
        raise HTTPException(status_code=404, detail="Invalid referral code")

    config = await db.referral_config.find_one({"tenant_id": tid}, {"_id": 0})
    referrer_points = config.get("referrer_points", 200) if config else 200
    referee_points = config.get("referee_points", 100) if config else 100

    ref = await insert_scoped("member_referrals", tid, {
        "referrer_contact_id": referrer_acct.get("contact_id", ""),
        "referee_contact_id": referee_contact_id,
        "referral_code": code,
        "status": "completed",
        "referrer_points_earned": referrer_points,
        "referee_points_earned": referee_points,
    })

    # Award points
    await db.loyalty_accounts.update_one(
        {"tenant_id": tid, "contact_id": referrer_acct["contact_id"]},
        {"$inc": {"points_balance": referrer_points}}
    )
    referee_acct = await db.loyalty_accounts.find_one({"tenant_id": tid, "contact_id": referee_contact_id})
    if referee_acct:
        await db.loyalty_accounts.update_one(
            {"tenant_id": tid, "contact_id": referee_contact_id},
            {"$inc": {"points_balance": referee_points}}
        )

    return ref


# ============ REWARD CATALOG ENHANCED ============
@router.get("/tenants/{tenant_slug}/rewards-enhanced")
async def list_rewards_enhanced(tenant_slug: str, tier: Optional[str] = None,
                                category: Optional[str] = None, user=Depends(get_current_user)):
    """Enhanced reward catalog with tier-based and seasonal filtering"""
    tenant = await resolve_tenant(tenant_slug)
    query = {"active": True}
    if category:
        query["category"] = category
    rewards = await find_many_scoped("rewards_catalog_v3", tenant["id"], query,
                                      sort=[("sort_order", 1)])
    # Filter by tier access
    if tier:
        tier_order = {"bronze": 1, "silver": 2, "gold": 3, "platinum": 4}
        member_level = tier_order.get(tier, 1)
        rewards = [r for r in rewards if tier_order.get(r.get("min_tier", "bronze"), 1) <= member_level]

    return {"data": rewards, "total": len(rewards)}


@router.post("/tenants/{tenant_slug}/rewards-enhanced")
async def create_reward_enhanced(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    reward = await insert_scoped("rewards_catalog_v3", tenant["id"], {
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "points_cost": data.get("points_cost", 100),
        "category": data.get("category", "genel"),
        "subcategory": data.get("subcategory", ""),
        "icon": data.get("icon", "gift"),
        "image_url": data.get("image_url", ""),
        "min_tier": data.get("min_tier", "bronze"),
        "is_partner": data.get("is_partner", False),
        "partner_name": data.get("partner_name", ""),
        "partner_type": data.get("partner_type", ""),
        "is_seasonal": data.get("is_seasonal", False),
        "season": data.get("season", ""),
        "valid_from": data.get("valid_from", ""),
        "valid_until": data.get("valid_until", ""),
        "stock": data.get("stock", -1),
        "redeemed_count": 0,
        "sort_order": data.get("sort_order", 0),
        "active": True,
    })
    await log_audit(tenant["id"], "REWARD_V3_CREATED", "rewards_catalog_v3", reward["id"], user.get("id", ""))
    return reward


@router.put("/tenants/{tenant_slug}/rewards-enhanced/{reward_id}")
async def update_reward_enhanced(tenant_slug: str, reward_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    allowed = ["name", "description", "points_cost", "category", "subcategory", "icon", "image_url",
               "min_tier", "is_partner", "partner_name", "partner_type", "is_seasonal", "season",
               "valid_from", "valid_until", "stock", "sort_order", "active"]
    update_data = {k: v for k, v in data.items() if k in allowed}
    return await update_scoped("rewards_catalog_v3", tenant["id"], reward_id, update_data)


@router.delete("/tenants/{tenant_slug}/rewards-enhanced/{reward_id}")
async def delete_reward_enhanced(tenant_slug: str, reward_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    await delete_scoped("rewards_catalog_v3", tenant["id"], reward_id)
    return {"ok": True}


# ============ CAMPAIGNS ============
@router.get("/tenants/{tenant_slug}/campaigns")
async def list_campaigns(tenant_slug: str, status: Optional[str] = None, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if status:
        query["status"] = status
    campaigns = await find_many_scoped("loyalty_campaigns", tenant["id"], query,
                                        sort=[("created_at", -1)])
    return {"data": campaigns, "total": len(campaigns)}


@router.post("/tenants/{tenant_slug}/campaigns")
async def create_campaign(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    campaign = await insert_scoped("loyalty_campaigns", tenant["id"], {
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "campaign_type": data.get("campaign_type", "seasonal"),
        "target_segment": data.get("target_segment", "all"),
        "target_tiers": data.get("target_tiers", []),
        "channel": data.get("channel", "all"),
        "bonus_points": data.get("bonus_points", 0),
        "bonus_multiplier": data.get("bonus_multiplier", 1.0),
        "reward_id": data.get("reward_id", ""),
        "message_template": data.get("message_template", ""),
        "start_date": data.get("start_date", ""),
        "end_date": data.get("end_date", ""),
        "status": data.get("status", "draft"),
        "sent_count": 0,
        "opened_count": 0,
        "converted_count": 0,
    })
    await log_audit(tenant["id"], "CAMPAIGN_CREATED", "loyalty_campaigns", campaign["id"], user.get("id", ""))
    return campaign


@router.put("/tenants/{tenant_slug}/campaigns/{campaign_id}")
async def update_campaign(tenant_slug: str, campaign_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    allowed = ["name", "description", "campaign_type", "target_segment", "target_tiers", "channel",
               "bonus_points", "bonus_multiplier", "reward_id", "message_template",
               "start_date", "end_date", "status", "sent_count", "opened_count", "converted_count"]
    update_data = {k: v for k, v in data.items() if k in allowed}
    return await update_scoped("loyalty_campaigns", tenant["id"], campaign_id, update_data)


@router.delete("/tenants/{tenant_slug}/campaigns/{campaign_id}")
async def delete_campaign(tenant_slug: str, campaign_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    await delete_scoped("loyalty_campaigns", tenant["id"], campaign_id)
    return {"ok": True}


# ============ COMMUNICATION PREFERENCES ============
@router.get("/tenants/{tenant_slug}/communication-prefs")
async def get_comm_prefs(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    prefs = await db.comm_prefs.find_one({"tenant_id": tenant["id"]}, {"_id": 0})
    if not prefs:
        prefs = {
            "id": new_id(), "tenant_id": tenant["id"],
            "email_enabled": True,
            "sms_enabled": False,
            "whatsapp_enabled": False,
            "push_enabled": True,
            "inapp_enabled": True,
            "birthday_campaign": True,
            "anniversary_campaign": True,
            "tier_change_notification": True,
            "points_reminder_days": 30,
            "inactive_reminder_days": 60,
            "updated_at": now_utc().isoformat()
        }
        await db.comm_prefs.insert_one(prefs)
    return serialize_doc(prefs)


@router.put("/tenants/{tenant_slug}/communication-prefs")
async def update_comm_prefs(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    allowed = ["email_enabled", "sms_enabled", "whatsapp_enabled", "push_enabled", "inapp_enabled",
               "birthday_campaign", "anniversary_campaign", "tier_change_notification",
               "points_reminder_days", "inactive_reminder_days"]
    update = {k: v for k, v in data.items() if k in allowed}
    update["updated_at"] = now_utc().isoformat()
    existing = await db.comm_prefs.find_one({"tenant_id": tid})
    if existing:
        await db.comm_prefs.update_one({"tenant_id": tid}, {"$set": update})
    else:
        update["id"] = new_id()
        update["tenant_id"] = tid
        await db.comm_prefs.insert_one(update)
    return serialize_doc(await db.comm_prefs.find_one({"tenant_id": tid}, {"_id": 0}))


# ============ SELF-SERVICE PORTAL (Guest-Facing) ============
@router.get("/g/{tenant_slug}/loyalty/profile/{contact_id}")
async def guest_loyalty_profile(tenant_slug: str, contact_id: str):
    """Guest-facing: Get loyalty profile with points, tier, history"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    acct = await db.loyalty_accounts.find_one({"tenant_id": tid, "contact_id": contact_id})
    if not acct:
        raise HTTPException(status_code=404, detail="Sadakat hesabi bulunamadi")

    contact = await find_one_scoped("contacts", tid, {"id": contact_id})
    config = await db.tier_config.find_one({"tenant_id": tid}, {"_id": 0})
    tiers = config.get("tiers", DEFAULT_TIERS_V3) if config else DEFAULT_TIERS_V3
    tier = _calc_tier_v3(acct.get("points_balance", 0), tiers)
    next_info = _next_tier_info_v3(acct.get("points_balance", 0), tier.get("slug", "bronze"), tiers)

    # Recent ledger
    ledger = await find_many_scoped("loyalty_ledger", tid, {"contact_id": contact_id},
                                     sort=[("created_at", -1)], limit=20)
    # Earned badges
    badges = await find_many_scoped("earned_badges", tid, {"contact_id": contact_id},
                                     sort=[("earned_at", -1)])
    # Active challenges progress
    challenge_progress = await find_many_scoped("challenge_progress", tid,
                                                  {"contact_id": contact_id, "completed": False})

    return {
        "member_name": contact.get("name", "") if contact else "",
        "member_email": contact.get("email", "") if contact else "",
        "points_balance": acct.get("points_balance", 0),
        "tier": {
            "name": tier.get("name", "Bronz"),
            "slug": tier.get("slug", "bronze"),
            "color": tier.get("color", "#CD7F32"),
            "benefits": tier.get("benefits", []),
            "multiplier": tier.get("multiplier", 1.0),
        },
        "next_tier": next_info,
        "enrolled_at": acct.get("enrolled_at", ""),
        "referral_code": acct.get("referral_code", ""),
        "recent_activity": ledger[:10],
        "badges": badges,
        "active_challenges": challenge_progress,
        "all_tiers": [{"name": t["name"], "slug": t["slug"], "min_points": t["min_points"],
                        "color": t.get("color", "#CD7F32")} for t in tiers],
    }


@router.get("/g/{tenant_slug}/loyalty/rewards")
async def guest_available_rewards(tenant_slug: str, contact_id: Optional[str] = None):
    """Guest-facing: Browse available rewards"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    member_tier = "bronze"
    member_points = 0
    if contact_id:
        acct = await db.loyalty_accounts.find_one({"tenant_id": tid, "contact_id": contact_id})
        if acct:
            member_tier = acct.get("tier_slug", "bronze")
            member_points = acct.get("points_balance", 0)

    rewards = await find_many_scoped("rewards_catalog_v3", tid, {"active": True},
                                      sort=[("points_cost", 1)])
    tier_order = {"bronze": 1, "silver": 2, "gold": 3, "platinum": 4}
    member_level = tier_order.get(member_tier, 1)
    available = []
    for r in rewards:
        r_level = tier_order.get(r.get("min_tier", "bronze"), 1)
        if r_level <= member_level:
            r["can_redeem"] = member_points >= r.get("points_cost", 0)
            available.append(r)

    return {"data": available, "total": len(available), "member_points": member_points, "member_tier": member_tier}


@router.post("/g/{tenant_slug}/loyalty/redeem")
async def guest_redeem_reward(tenant_slug: str, data: dict):
    """Guest-facing: Redeem a reward"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    contact_id = data.get("contact_id", "")
    reward_id = data.get("reward_id", "")
    if not contact_id or not reward_id:
        raise HTTPException(status_code=400, detail="contact_id and reward_id required")

    acct = await db.loyalty_accounts.find_one({"tenant_id": tid, "contact_id": contact_id})
    if not acct:
        raise HTTPException(status_code=404, detail="Sadakat hesabi bulunamadi")

    reward = await find_one_scoped("rewards_catalog_v3", tid, {"id": reward_id})
    if not reward:
        # Fallback to legacy catalog
        reward = await find_one_scoped("rewards_catalog", tid, {"id": reward_id})
    if not reward:
        raise HTTPException(status_code=404, detail="Odul bulunamadi")

    cost = reward.get("points_cost", 0)
    if acct.get("points_balance", 0) < cost:
        raise HTTPException(status_code=400, detail="Yetersiz puan")

    new_balance = acct["points_balance"] - cost
    await db.loyalty_accounts.update_one(
        {"tenant_id": tid, "contact_id": contact_id},
        {"$set": {"points_balance": new_balance, "updated_at": now_utc().isoformat()}}
    )

    redemption = await insert_scoped("reward_redemptions", tid, {
        "contact_id": contact_id,
        "reward_id": reward_id,
        "reward_name": reward.get("name", ""),
        "points_spent": cost,
        "status": "pending",
        "source": "self_service",
        "redeemed_at": now_utc().isoformat(),
    })

    return {"redemption": redemption, "new_balance": new_balance}


# ============ OVERVIEW / DASHBOARD ============
@router.get("/tenants/{tenant_slug}/overview")
async def loyalty_overview(tenant_slug: str, user=Depends(get_current_user)):
    """Comprehensive loyalty program overview dashboard"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    total_members = await count_scoped("loyalty_accounts", tid)
    total_points_in_circulation = 0
    async for doc in db.loyalty_accounts.aggregate([
        {"$match": {"tenant_id": tid}},
        {"$group": {"_id": None, "total": {"$sum": "$points_balance"}}}
    ]):
        total_points_in_circulation = doc.get("total", 0)

    total_earned = 0
    async for doc in db.loyalty_ledger.aggregate([
        {"$match": {"tenant_id": tid, "direction": "EARN"}},
        {"$group": {"_id": None, "total": {"$sum": "$points"}}}
    ]):
        total_earned = doc.get("total", 0)

    total_spent = 0
    async for doc in db.loyalty_ledger.aggregate([
        {"$match": {"tenant_id": tid, "direction": {"$in": ["SPEND", "ADJUST"]}, "points": {"$lt": 0}}},
        {"$group": {"_id": None, "total": {"$sum": {"$abs": "$points"}}}}
    ]):
        total_spent = doc.get("total", 0)

    total_redemptions = await count_scoped("reward_redemptions", tid)
    redemption_rate = round(total_redemptions / max(total_members, 1) * 100, 1)

    # Tier distribution
    tier_dist = []
    async for doc in db.loyalty_accounts.aggregate([
        {"$match": {"tenant_id": tid}},
        {"$group": {"_id": {"$ifNull": ["$tier_slug", "$tier_name"]}, "count": {"$sum": 1}}}
    ]):
        tier_dist.append({"tier": doc["_id"], "count": doc["count"]})

    # Recent enrollments (last 30 days)
    thirty_days_ago = (now_utc() - timedelta(days=30)).isoformat()
    new_members_30d = await db.loyalty_accounts.count_documents({
        "tenant_id": tid, "enrolled_at": {"$gte": thirty_days_ago}
    })

    total_referrals = await count_scoped("member_referrals", tid, {"status": "completed"})
    total_campaigns = await count_scoped("loyalty_campaigns", tid)
    active_campaigns = await count_scoped("loyalty_campaigns", tid, {"status": "active"})

    point_rules_count = await count_scoped("point_rules", tid, {"active": True})
    rewards_count = await count_scoped("rewards_catalog_v3", tid, {"active": True})
    # Fallback to legacy
    if rewards_count == 0:
        rewards_count = await count_scoped("rewards_catalog", tid, {"active": True})

    return {
        "total_members": total_members,
        "new_members_30d": new_members_30d,
        "points_in_circulation": total_points_in_circulation,
        "total_points_earned": total_earned,
        "total_points_spent": total_spent,
        "total_redemptions": total_redemptions,
        "redemption_rate": redemption_rate,
        "tier_distribution": tier_dist,
        "total_referrals": total_referrals,
        "total_campaigns": total_campaigns,
        "active_campaigns": active_campaigns,
        "point_rules_count": point_rules_count,
        "rewards_count": rewards_count,
    }
