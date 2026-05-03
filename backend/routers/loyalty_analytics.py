"""Loyalty Analytics V3: RFM, CLV, Churn, Cohort, Segmentation, ROI
AI-powered member segmentation and loyalty program analytics.
"""
import asyncio
from fastapi import APIRouter, Depends
from typing import Optional
from datetime import datetime, timedelta
import math

from core.config import db
from core.tenant_guard import (
    resolve_tenant, get_current_user, serialize_doc,
    new_id, now_utc, find_one_scoped, find_many_scoped, count_scoped,
    insert_scoped, update_scoped
)

import logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/loyalty-analytics", tags=["loyalty-analytics"])


def _rfm_score(value, thresholds):
    """Score 1-5 based on thresholds"""
    for i, t in enumerate(thresholds):
        if value <= t:
            return i + 1
    return 5


def _clv_simple(avg_spend, frequency, lifespan_months):
    """Simple CLV = avg_spend * frequency * lifespan"""
    return round(avg_spend * frequency * (lifespan_months / 12), 2)


# ============ RFM ANALYSIS ============
@router.get("/tenants/{tenant_slug}/rfm")
async def rfm_analysis(tenant_slug: str, user=Depends(get_current_user)):
    """RFM (Recency, Frequency, Monetary) segmentation analysis"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    now = now_utc()

    # Single aggregation: per-contact recency + frequency + monetary in one pass.
    ledger_pipeline = [
        {"$match": {"tenant_id": tid}},
        {"$group": {
            "_id": "$contact_id",
            "last_at": {"$max": "$created_at"},
            "frequency": {"$sum": 1},
            "monetary": {"$sum": {"$cond": [{"$eq": ["$direction", "EARN"]}, "$points", 0]}},
        }},
    ]

    members, ledger_docs, contacts = await asyncio.gather(
        db.loyalty_accounts.find({"tenant_id": tid}).to_list(5000),
        db.loyalty_ledger.aggregate(ledger_pipeline).to_list(None),
        db.contacts.find({"tenant_id": tid}, {"id": 1, "name": 1}).to_list(None),
    )
    ledger_by_contact = {d["_id"]: d for d in ledger_docs}
    contact_by_id = {c["id"]: c for c in contacts}

    rfm_data = []
    for member in members:
        contact_id = member.get("contact_id", "")
        contact = contact_by_id.get(contact_id)
        led = ledger_by_contact.get(contact_id, {})

        last_at = led.get("last_at")
        if last_at:
            try:
                last_date = datetime.fromisoformat(last_at.replace("Z", "+00:00"))
                recency_days = (now - last_date).days
            except Exception:
                recency_days = 365
        else:
            recency_days = 365

        frequency = led.get("frequency", 0)
        monetary = led.get("monetary", 0)

        # Score R, F, M (1-5 each)
        r_score = 5 - min(4, recency_days // 30)  # 5=recent, 1=old
        f_score = min(5, max(1, frequency))
        m_score = min(5, max(1, monetary // 100))

        # Segment classification
        total_score = r_score + f_score + m_score
        if total_score >= 13:
            segment = "Sampiyon"
            segment_en = "Champion"
        elif r_score >= 4 and f_score >= 3:
            segment = "Sadik Musteri"
            segment_en = "Loyal"
        elif r_score >= 3 and m_score >= 4:
            segment = "Yuksek Harcama"
            segment_en = "Big Spender"
        elif r_score >= 4 and f_score <= 2:
            segment = "Yeni Musteri"
            segment_en = "New Customer"
        elif r_score <= 2 and f_score >= 3:
            segment = "Risk Altinda"
            segment_en = "At Risk"
        elif r_score <= 2 and f_score <= 2:
            segment = "Kayip"
            segment_en = "Lost"
        elif f_score >= 3:
            segment = "Potansiyel Sadik"
            segment_en = "Potential Loyalist"
        else:
            segment = "Diger"
            segment_en = "Other"

        rfm_data.append({
            "contact_id": contact_id,
            "name": contact.get("name", "Unknown") if contact else "Unknown",
            "tier": member.get("tier_name", member.get("tier_slug", "Silver")),
            "points": member.get("points_balance", 0),
            "recency_days": recency_days,
            "frequency": frequency,
            "monetary": monetary,
            "r_score": r_score,
            "f_score": f_score,
            "m_score": m_score,
            "total_score": total_score,
            "segment": segment,
            "segment_en": segment_en,
        })

    # Segment distribution
    segment_dist = {}
    for item in rfm_data:
        seg = item["segment"]
        segment_dist[seg] = segment_dist.get(seg, 0) + 1

    return {
        "data": rfm_data,
        "total": len(rfm_data),
        "segment_distribution": segment_dist,
        "avg_rfm": {
            "avg_recency": round(sum(d["recency_days"] for d in rfm_data) / max(len(rfm_data), 1), 1),
            "avg_frequency": round(sum(d["frequency"] for d in rfm_data) / max(len(rfm_data), 1), 1),
            "avg_monetary": round(sum(d["monetary"] for d in rfm_data) / max(len(rfm_data), 1), 1),
        }
    }


# ============ CLV (Customer Lifetime Value) ============
@router.get("/tenants/{tenant_slug}/clv")
async def clv_analysis(tenant_slug: str, user=Depends(get_current_user)):
    """Calculate Customer Lifetime Value for each member"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    members = await db.loyalty_accounts.find({"tenant_id": tid}).to_list(5000)
    now = now_utc()
    clv_data = []

    for member in members:
        contact_id = member.get("contact_id", "")
        contact = await find_one_scoped("contacts", tid, {"id": contact_id})

        # Total earned
        total_earned = 0
        tx_count = 0
        async for doc in db.loyalty_ledger.aggregate([
            {"$match": {"tenant_id": tid, "contact_id": contact_id, "direction": "EARN"}},
            {"$group": {"_id": None, "total": {"$sum": "$points"}, "count": {"$sum": 1}}}
        ]):
            total_earned = doc.get("total", 0)
            tx_count = doc.get("count", 0)

        # Lifespan in months
        enrolled_at = member.get("enrolled_at", "")
        try:
            enrolled_date = datetime.fromisoformat(enrolled_at.replace("Z", "+00:00"))
            lifespan_months = max(1, (now - enrolled_date).days / 30)
        except Exception:
            lifespan_months = 1

        avg_spend_per_tx = total_earned / max(tx_count, 1)
        frequency_per_month = tx_count / lifespan_months
        predicted_lifespan = min(60, lifespan_months * 2)  # Simple prediction

        clv = _clv_simple(avg_spend_per_tx, frequency_per_month, predicted_lifespan)

        # Risk level
        if clv > 5000:
            risk = "dusuk"
            risk_label = "Dusuk Risk"
        elif clv > 1000:
            risk = "orta"
            risk_label = "Orta Risk"
        else:
            risk = "yuksek"
            risk_label = "Yuksek Risk"

        clv_data.append({
            "contact_id": contact_id,
            "name": contact.get("name", "Unknown") if contact else "Unknown",
            "tier": member.get("tier_name", member.get("tier_slug", "Silver")),
            "points": member.get("points_balance", 0),
            "total_earned": total_earned,
            "transaction_count": tx_count,
            "lifespan_months": round(lifespan_months, 1),
            "avg_spend_per_tx": round(avg_spend_per_tx, 1),
            "frequency_per_month": round(frequency_per_month, 2),
            "clv": clv,
            "predicted_lifespan_months": round(predicted_lifespan, 1),
            "risk": risk,
            "risk_label": risk_label,
        })

    # Sort by CLV descending
    clv_data.sort(key=lambda x: x["clv"], reverse=True)

    avg_clv = round(sum(d["clv"] for d in clv_data) / max(len(clv_data), 1), 2)
    total_clv = round(sum(d["clv"] for d in clv_data), 2)

    return {
        "data": clv_data,
        "total": len(clv_data),
        "avg_clv": avg_clv,
        "total_clv": total_clv,
    }


# ============ CHURN PREDICTION ============
@router.get("/tenants/{tenant_slug}/churn")
async def churn_analysis(tenant_slug: str, user=Depends(get_current_user)):
    """Churn risk scoring for loyalty members"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    members = await db.loyalty_accounts.find({"tenant_id": tid}).to_list(5000)
    now = now_utc()
    churn_data = []

    for member in members:
        contact_id = member.get("contact_id", "")
        contact = await find_one_scoped("contacts", tid, {"id": contact_id})

        # Days since last activity
        last_entry = await db.loyalty_ledger.find_one(
            {"tenant_id": tid, "contact_id": contact_id},
            sort=[("created_at", -1)]
        )
        if last_entry and last_entry.get("created_at"):
            try:
                last_date = datetime.fromisoformat(last_entry["created_at"].replace("Z", "+00:00"))
                days_inactive = (now - last_date).days
            except Exception:
                days_inactive = 365
        else:
            days_inactive = 365

        # Frequency in last 90 days
        ninety_days_ago = (now - timedelta(days=90)).isoformat()
        recent_activity = await db.loyalty_ledger.count_documents({
            "tenant_id": tid, "contact_id": contact_id,
            "created_at": {"$gte": ninety_days_ago}
        })

        # Points trend (earning vs spending)
        total_earned = 0
        total_spent = 0
        async for doc in db.loyalty_ledger.aggregate([
            {"$match": {"tenant_id": tid, "contact_id": contact_id}},
            {"$group": {"_id": "$direction", "total": {"$sum": {"$abs": "$points"}}}}
        ]):
            if doc["_id"] == "EARN":
                total_earned = doc.get("total", 0)
            elif doc["_id"] in ["SPEND", "ADJUST"]:
                total_spent = doc.get("total", 0)

        # Churn score (0-100, higher = more likely to churn)
        inactivity_score = min(50, days_inactive * 0.15)
        recency_score = min(25, max(0, 25 - recent_activity * 5))
        engagement_score = min(25, max(0, 25 - (total_earned / max(total_spent + 1, 1)) * 5))
        churn_score = round(min(100, inactivity_score + recency_score + engagement_score))

        if churn_score >= 70:
            risk_level = "kritik"
            risk_label = "Kritik"
            risk_color = "#EF4444"
        elif churn_score >= 50:
            risk_level = "yuksek"
            risk_label = "Yuksek"
            risk_color = "#F59E0B"
        elif churn_score >= 30:
            risk_level = "orta"
            risk_label = "Orta"
            risk_color = "#3B82F6"
        else:
            risk_level = "dusuk"
            risk_label = "Dusuk"
            risk_color = "#10B981"

        # Recommended action
        if churn_score >= 70:
            action = "Acil kisisel teklif gonderin"
        elif churn_score >= 50:
            action = "Ozel kampanya ile yeniden aktive edin"
        elif churn_score >= 30:
            action = "Hatirlatma mesaji gonderin"
        else:
            action = "Mevcut etklesimi devam ettirin"

        churn_data.append({
            "contact_id": contact_id,
            "name": contact.get("name", "Unknown") if contact else "Unknown",
            "tier": member.get("tier_name", member.get("tier_slug", "Silver")),
            "points": member.get("points_balance", 0),
            "days_inactive": days_inactive,
            "recent_activity_90d": recent_activity,
            "total_earned": total_earned,
            "total_spent": total_spent,
            "churn_score": churn_score,
            "risk_level": risk_level,
            "risk_label": risk_label,
            "risk_color": risk_color,
            "recommended_action": action,
        })

    churn_data.sort(key=lambda x: x["churn_score"], reverse=True)

    # Risk distribution
    risk_dist = {"kritik": 0, "yuksek": 0, "orta": 0, "dusuk": 0}
    for item in churn_data:
        risk_dist[item["risk_level"]] = risk_dist.get(item["risk_level"], 0) + 1

    return {
        "data": churn_data,
        "total": len(churn_data),
        "risk_distribution": risk_dist,
        "avg_churn_score": round(sum(d["churn_score"] for d in churn_data) / max(len(churn_data), 1), 1),
    }


# ============ COHORT ANALYSIS ============
@router.get("/tenants/{tenant_slug}/cohort")
async def cohort_analysis(tenant_slug: str, months: int = 6, user=Depends(get_current_user)):
    """Cohort analysis: new vs returning members by enrollment month"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    now = now_utc()

    if months <= 0:
        return {"data": [], "months": months}

    # Build month boundaries once
    boundaries = []
    for i in range(months):
        month_start = (now - timedelta(days=30 * (months - i - 1))).replace(day=1, hour=0, minute=0, second=0)
        if i < months - 1:
            month_end = (now - timedelta(days=30 * (months - i - 2))).replace(day=1, hour=0, minute=0, second=0)
        else:
            month_end = now
        boundaries.append((month_start, month_end, month_start.strftime("%Y-%m")))

    earliest = boundaries[0][0].isoformat()
    latest = boundaries[-1][1].isoformat()

    # Run both aggregations in parallel — replaces N*3 sequential queries.
    enrolled_pipeline = [
        {"$match": {"tenant_id": tid, "enrolled_at": {"$gte": earliest, "$lt": latest}}},
        {"$project": {"contact_id": 1, "month": {"$substr": ["$enrolled_at", 0, 7]}}},
        {"$group": {"_id": "$month", "count": {"$sum": 1}, "contact_ids": {"$addToSet": "$contact_id"}}},
    ]
    active_pipeline = [
        {"$match": {"tenant_id": tid, "created_at": {"$gte": earliest, "$lt": latest}}},
        {"$project": {"contact_id": 1, "month": {"$substr": ["$created_at", 0, 7]}}},
        {"$group": {"_id": {"month": "$month", "contact_id": "$contact_id"}}},
        {"$group": {"_id": "$_id.month", "contact_ids": {"$addToSet": "$_id.contact_id"}}},
    ]

    enrolled_docs, active_docs = await asyncio.gather(
        db.loyalty_accounts.aggregate(enrolled_pipeline).to_list(None),
        db.loyalty_ledger.aggregate(active_pipeline).to_list(None),
    )
    enrolled_by_month = {d["_id"]: d for d in enrolled_docs}
    active_by_month = {d["_id"]: set(d.get("contact_ids", [])) for d in active_docs}

    cohorts = []
    for _, _, label in boundaries:
        e = enrolled_by_month.get(label, {})
        new_set = set(e.get("contact_ids", []))
        active_set = active_by_month.get(label, set())
        returning = len(active_set - new_set)
        total_active = len(active_set)
        cohorts.append({
            "month": label,
            "new_members": e.get("count", 0),
            "active_members": total_active,
            "returning_members": returning,
            "retention_rate": round(returning / max(total_active, 1) * 100, 1)
        })

    return {"data": cohorts, "months": months}


# ============ ROI MEASUREMENT ============
@router.get("/tenants/{tenant_slug}/roi")
async def roi_measurement(tenant_slug: str, user=Depends(get_current_user)):
    """ROI measurement for loyalty program"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    total_members = await count_scoped("loyalty_accounts", tid)

    # Total points distributed
    total_points_earned = 0
    async for doc in db.loyalty_ledger.aggregate([
        {"$match": {"tenant_id": tid, "direction": "EARN"}},
        {"$group": {"_id": None, "total": {"$sum": "$points"}}}
    ]):
        total_points_earned = doc.get("total", 0)

    # Total redeemed
    total_redeemed = 0
    async for doc in db.loyalty_ledger.aggregate([
        {"$match": {"tenant_id": tid, "direction": "SPEND"}},
        {"$group": {"_id": None, "total": {"$sum": {"$abs": "$points"}}}}
    ]):
        total_redeemed = doc.get("total", 0)

    # Reward redemptions
    total_reward_redemptions = await count_scoped("reward_redemptions", tid)
    fulfilled_redemptions = await count_scoped("reward_redemptions", tid, {"status": "fulfilled"})

    # Estimated point value (1 point = ~0.1 TRY)
    point_value_try = 0.1
    program_cost = round(total_points_earned * point_value_try, 2)
    redemption_cost = round(total_redeemed * point_value_try, 2)

    # Revenue estimate from loyal members (rough proxy)
    reservations_from_members = await db.reservations.count_documents({"tenant_id": tid})
    avg_reservation_value = 2500  # TRY estimate
    estimated_revenue = reservations_from_members * avg_reservation_value

    roi = round((estimated_revenue - program_cost) / max(program_cost, 1) * 100, 1)

    # Referral contribution
    referral_conversions = await count_scoped("member_referrals", tid, {"status": "completed"})

    return {
        "total_members": total_members,
        "total_points_earned": total_points_earned,
        "total_points_redeemed": total_redeemed,
        "total_reward_redemptions": total_reward_redemptions,
        "fulfilled_redemptions": fulfilled_redemptions,
        "program_cost_try": program_cost,
        "redemption_cost_try": redemption_cost,
        "estimated_revenue_try": estimated_revenue,
        "roi_percentage": roi,
        "referral_conversions": referral_conversions,
        "point_value_try": point_value_try,
        "avg_points_per_member": round(total_points_earned / max(total_members, 1), 1),
        "redemption_rate": round(total_redeemed / max(total_points_earned, 1) * 100, 1),
    }


# ============ AI SEGMENTATION SUMMARY ============
@router.get("/tenants/{tenant_slug}/segments")
async def ai_segmentation_summary(tenant_slug: str, user=Depends(get_current_user)):
    """AI-powered segmentation summary combining RFM + CLV + Churn"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    members = await db.loyalty_accounts.find({"tenant_id": tid}).to_list(5000)
    now = now_utc()

    segments = {
        "Sampiyon": {"count": 0, "total_points": 0, "color": "#10B981", "description": "Yuksek harcama, sik ziyaret, dusuk churn"},
        "Sadik": {"count": 0, "total_points": 0, "color": "#3B82F6", "description": "Duzenli aktivite, orta harcama"},
        "Yukselen": {"count": 0, "total_points": 0, "color": "#8B5CF6", "description": "Artan aktivite, gelecek vadeden"},
        "Risk Altinda": {"count": 0, "total_points": 0, "color": "#F59E0B", "description": "Azalan aktivite, churn riski"},
        "Kayip": {"count": 0, "total_points": 0, "color": "#EF4444", "description": "Uzun suredir inaktif"},
    }

    member_segments = []
    for member in members:
        contact_id = member.get("contact_id", "")
        contact = await find_one_scoped("contacts", tid, {"id": contact_id})
        points = member.get("points_balance", 0)

        # Simple segmentation logic
        last_entry = await db.loyalty_ledger.find_one(
            {"tenant_id": tid, "contact_id": contact_id},
            sort=[("created_at", -1)]
        )
        days_inactive = 365
        if last_entry and last_entry.get("created_at"):
            try:
                last_date = datetime.fromisoformat(last_entry["created_at"].replace("Z", "+00:00"))
                days_inactive = (now - last_date).days
            except Exception:
                pass

        frequency = await db.loyalty_ledger.count_documents(
            {"tenant_id": tid, "contact_id": contact_id}
        )

        if days_inactive < 30 and frequency > 3 and points > 300:
            seg = "Sampiyon"
        elif days_inactive < 60 and frequency > 2:
            seg = "Sadik"
        elif days_inactive < 90 and frequency >= 1:
            seg = "Yukselen"
        elif days_inactive < 180:
            seg = "Risk Altinda"
        else:
            seg = "Kayip"

        segments[seg]["count"] += 1
        segments[seg]["total_points"] += points

        member_segments.append({
            "contact_id": contact_id,
            "name": contact.get("name", "Unknown") if contact else "Unknown",
            "segment": seg,
            "points": points,
            "days_inactive": days_inactive,
            "frequency": frequency,
        })

    # Personalized offers per segment
    offers = {
        "Sampiyon": "Exclusive VIP deneyimi ve erken erisim firsat",
        "Sadik": "Puan carpani artisi ve ozel odul firsatlari",
        "Yukselen": "Hosgeldin bonusu ve ilk odul indirimi",
        "Risk Altinda": "Geri donus kampanyasi ve bonus puan teklifi",
        "Kayip": "Ozluyoruz kampanyasi ve buyuk puan bonusu",
    }

    return {
        "segments": segments,
        "member_segments": member_segments,
        "personalized_offers": offers,
        "total_members": len(members),
    }


# ============ LOYALTY DASHBOARD ANALYTICS ============
@router.get("/tenants/{tenant_slug}/dashboard")
async def loyalty_dashboard(tenant_slug: str, period: str = "30d", user=Depends(get_current_user)):
    """Comprehensive loyalty analytics dashboard"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    now = now_utc()

    days = int(period.replace("d", "")) if "d" in period else 30
    period_start = (now - timedelta(days=days)).isoformat()

    # KPIs
    total_members = await count_scoped("loyalty_accounts", tid)
    active_members = len(await db.loyalty_ledger.distinct("contact_id", {
        "tenant_id": tid, "created_at": {"$gte": period_start}
    }))

    points_earned_period = 0
    async for doc in db.loyalty_ledger.aggregate([
        {"$match": {"tenant_id": tid, "direction": "EARN", "created_at": {"$gte": period_start}}},
        {"$group": {"_id": None, "total": {"$sum": "$points"}}}
    ]):
        points_earned_period = doc.get("total", 0)

    points_spent_period = 0
    async for doc in db.loyalty_ledger.aggregate([
        {"$match": {"tenant_id": tid, "direction": "SPEND", "created_at": {"$gte": period_start}}},
        {"$group": {"_id": None, "total": {"$sum": {"$abs": "$points"}}}}
    ]):
        points_spent_period = doc.get("total", 0)

    new_enrollments = await db.loyalty_accounts.count_documents({
        "tenant_id": tid, "enrolled_at": {"$gte": period_start}
    })

    redemptions_period = await db.reward_redemptions.count_documents({
        "tenant_id": tid, "redeemed_at": {"$gte": period_start}
    })

    # Activity by day (last N days)
    daily_activity = []
    for i in range(min(days, 30)):
        day = (now - timedelta(days=i))
        day_str = day.strftime("%Y-%m-%d")
        day_start = day.replace(hour=0, minute=0, second=0).isoformat()
        day_end = day.replace(hour=23, minute=59, second=59).isoformat()
        earned = 0
        async for doc in db.loyalty_ledger.aggregate([
            {"$match": {"tenant_id": tid, "direction": "EARN",
                         "created_at": {"$gte": day_start, "$lte": day_end}}},
            {"$group": {"_id": None, "total": {"$sum": "$points"}}}
        ]):
            earned = doc.get("total", 0)
        daily_activity.append({"date": day_str, "points_earned": earned})

    daily_activity.reverse()

    return {
        "period": period,
        "kpis": {
            "total_members": total_members,
            "active_members": active_members,
            "activity_rate": round(active_members / max(total_members, 1) * 100, 1),
            "points_earned": points_earned_period,
            "points_spent": points_spent_period,
            "new_enrollments": new_enrollments,
            "redemptions": redemptions_period,
        },
        "daily_activity": daily_activity,
    }
