"""Analytics routes: basic analytics, guest intelligence v2, revenue & staff KPIs.
Extracted from server.py for maintainability.
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime
import logging

from core.config import db
from core.tenant_guard import now_utc
from core.legacy_helpers import get_tenant_by_slug
from rbac import LOYALTY_TIERS, compute_tier, next_tier_info, analyze_sentiment
from analytics_engine import compute_analytics, compute_revenue_analytics, compute_staff_performance

logger = logging.getLogger("omnihub.analytics")
router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/tenants/{tenant_slug}/analytics")
async def get_analytics(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    return await compute_analytics(db, tenant["id"])


@router.get("/tenants/{tenant_slug}/contacts/{contact_id}/intelligence-v2")
async def get_intelligence_v2(tenant_slug: str, contact_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    contact = await db.contacts.find_one({"id": contact_id, "tenant_id": tenant["id"]}, {"_id": 0})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    phone = contact.get("phone", "")

    reqs = await db.guest_requests.find({"tenant_id": tenant["id"], "guest_phone": phone}, {"_id": 0}).to_list(500) if phone else []
    orders = await db.orders.find({"tenant_id": tenant["id"], "guest_phone": phone}, {"_id": 0}).to_list(500) if phone else []

    order_total = sum(o.get("total", 0) for o in orders)
    res_list = await db.reservations.find({"tenant_id": tenant["id"], "guest_phone": phone}, {"_id": 0}).to_list(100) if phone else []
    res_total = sum(r.get("price", 0) for r in res_list)
    lifetime_value = order_total + res_total

    response_times = []
    for r in reqs:
        if r.get("first_response_at") and r.get("created_at"):
            try:
                created = datetime.fromisoformat(r["created_at"].replace('Z', '+00:00'))
                responded = datetime.fromisoformat(r["first_response_at"].replace('Z', '+00:00'))
                response_times.append((responded - created).total_seconds() / 60)
            except Exception:
                pass
    avg_response_time = round(sum(response_times) / len(response_times), 1) if response_times else 0

    ratings = [r["rating"] for r in reqs if r.get("rating")]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0

    recent_ratings = ratings[-5:] if ratings else []
    older_ratings = ratings[:-5] if len(ratings) > 5 else []
    if recent_ratings and older_ratings:
        trend = "improving" if sum(recent_ratings) / len(recent_ratings) > sum(older_ratings) / len(older_ratings) else "declining"
    elif recent_ratings:
        trend = "stable"
    else:
        trend = "unknown"

    days_since_last = 999
    all_dates = [r.get("created_at", "") for r in reqs + orders]
    if all_dates:
        try:
            latest = max(all_dates)
            last_dt = datetime.fromisoformat(latest.replace('Z', '+00:00'))
            days_since_last = (now_utc() - last_dt).days
        except Exception:
            pass

    if days_since_last > 90:
        churn_risk = "high"
    elif days_since_last > 30:
        churn_risk = "medium"
    else:
        churn_risk = "low"

    complaints = [r for r in reqs if r.get("priority") in ["high", "urgent"] or analyze_sentiment(r.get("description", "")) == "negative"]
    complaint_ratio = round(len(complaints) / max(len(reqs), 1), 2)

    categories = {}
    for r in reqs:
        cat = r.get("category", "other")
        categories[cat] = categories.get(cat, 0) + 1

    item_counts = {}
    for o in orders:
        for item in o.get("items", []):
            name = item.get("menu_item_name", "")
            item_counts[name] = item_counts.get(name, 0) + item.get("quantity", 1)

    loyalty_info = None
    if contact.get("loyalty_account_id"):
        account = await db.loyalty_accounts.find_one({"id": contact["loyalty_account_id"]}, {"_id": 0})
        if account:
            tier = compute_tier(account.get("points", 0))
            loyalty_info = {
                "points": account.get("points", 0),
                "tier": tier,
                "tier_info": LOYALTY_TIERS.get(tier, {}),
                "next_tier": next_tier_info(tier, account.get("points", 0)),
            }

    alerts = []
    if churn_risk == "high":
        alerts.append({"type": "danger", "message": "High churn risk - no activity in 90+ days"})
    if complaint_ratio > 0.3:
        alerts.append({"type": "warning", "message": f"High complaint ratio ({int(complaint_ratio*100)}%)"})
    if avg_rating > 0 and avg_rating < 3:
        alerts.append({"type": "warning", "message": f"Low satisfaction: {avg_rating}/5"})
    if lifetime_value > 5000:
        alerts.append({"type": "success", "message": f"High-value guest: {lifetime_value} TRY"})
    for r in complaints[-2:]:
        alerts.append({"type": "danger", "message": f"Complaint: {r.get('description', '')[:60]}"})

    return {
        "lifetime_value": lifetime_value,
        "avg_response_time_min": avg_response_time,
        "avg_rating": avg_rating,
        "satisfaction_trend": trend,
        "predicted_churn_risk": churn_risk,
        "complaint_ratio": complaint_ratio,
        "total_requests": len(reqs),
        "total_orders": len(orders),
        "total_reservations": len(res_list),
        "service_preferences": categories,
        "favorite_items": sorted(item_counts.items(), key=lambda x: -x[1])[:5],
        "loyalty": loyalty_info,
        "alerts": alerts,
        "days_since_last_activity": days_since_last,
    }


@router.get("/tenants/{tenant_slug}/analytics/revenue")
async def revenue_analytics(tenant_slug: str, period: int = 30):
    """Revenue analytics v2 - gelir, upsell donusum, tekrar misafir, AI verimlilik KPI"""
    tenant = await get_tenant_by_slug(tenant_slug)
    return await compute_revenue_analytics(db, tenant["id"], period)


@router.get("/tenants/{tenant_slug}/analytics/staff-performance")
async def staff_performance(tenant_slug: str, period: int = 30):
    """Staff performance dashboard - personel bazli verimlilik metrikleri"""
    tenant = await get_tenant_by_slug(tenant_slug)
    return await compute_staff_performance(db, tenant["id"], period)
