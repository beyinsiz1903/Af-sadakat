"""Reports Router - Advanced reporting and analytics
Department performance, guest satisfaction, staff productivity, etc.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime, timezone, timedelta

from core.config import db
from core.tenant_guard import (
    resolve_tenant, get_current_user, serialize_doc, new_id, now_utc,
    find_one_scoped, find_many_scoped, count_scoped
)

router = APIRouter(prefix="/api/v2/reports", tags=["reports"])

@router.get("/tenants/{tenant_slug}/department-performance")
async def department_performance(tenant_slug: str, days: int = 30,
                                  user=Depends(get_current_user)):
    """Department performance report"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    since = (now_utc() - timedelta(days=days)).isoformat()
    
    departments = await find_many_scoped("departments", tid)
    dept_stats = []
    
    for dept in departments:
        code = dept.get("code", "")
        total = await count_scoped("guest_requests", tid, {"department_code": code, "created_at": {"$gte": since}})
        resolved = await count_scoped("guest_requests", tid, {
            "department_code": code, "created_at": {"$gte": since},
            "status": {"$in": ["DONE", "CLOSED"]}
        })
        open_count = await count_scoped("guest_requests", tid, {
            "department_code": code, "created_at": {"$gte": since},
            "status": "OPEN"
        })
        
        # Average resolution time
        resolved_reqs = await find_many_scoped("guest_requests", tid, {
            "department_code": code, "resolved_at": {"$ne": None}
        }, limit=200)
        
        resolution_times = []
        ratings = []
        for r in resolved_reqs:
            if r.get("resolved_at") and r.get("created_at"):
                try:
                    created = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
                    resolved_dt = datetime.fromisoformat(r["resolved_at"].replace("Z", "+00:00"))
                    diff_min = (resolved_dt - created).total_seconds() / 60
                    resolution_times.append(diff_min)
                except:
                    pass
            if r.get("rating"):
                ratings.append(r["rating"])
        
        avg_resolution = round(sum(resolution_times) / len(resolution_times), 1) if resolution_times else 0
        avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0
        resolution_rate = round(resolved / max(total, 1) * 100, 1)
        
        dept_stats.append({
            "department": dept.get("name", code),
            "code": code,
            "total_requests": total,
            "resolved": resolved,
            "open": open_count,
            "resolution_rate": resolution_rate,
            "avg_resolution_minutes": avg_resolution,
            "avg_rating": avg_rating,
            "total_ratings": len(ratings),
        })
    
    return dept_stats

@router.get("/tenants/{tenant_slug}/guest-satisfaction")
async def guest_satisfaction(tenant_slug: str, days: int = 30,
                             user=Depends(get_current_user)):
    """Guest satisfaction trend analysis"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    since = (now_utc() - timedelta(days=days)).isoformat()
    
    # Request ratings
    rated_requests = await find_many_scoped("guest_requests", tid, {
        "rating": {"$ne": None}, "created_at": {"$gte": since}
    }, limit=500)
    
    # Reviews
    reviews = await find_many_scoped("reviews", tid, {"created_at": {"$gte": since}}, limit=500)
    
    # Surveys
    surveys = await find_many_scoped("guest_surveys", tid, {"created_at": {"$gte": since}}, limit=500)
    
    # Daily satisfaction
    daily = {}
    for r in rated_requests:
        day = r.get("created_at", "")[:10]
        if day not in daily:
            daily[day] = {"ratings": [], "count": 0}
        daily[day]["ratings"].append(r.get("rating", 0))
        daily[day]["count"] += 1
    
    daily_trend = []
    for day, data in sorted(daily.items()):
        avg = round(sum(data["ratings"]) / len(data["ratings"]), 1) if data["ratings"] else 0
        daily_trend.append({"date": day, "avg_rating": avg, "count": data["count"]})
    
    # Category satisfaction
    categories = {}
    for r in rated_requests:
        cat = r.get("category", "other")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r.get("rating", 0))
    
    category_ratings = {}
    for cat, ratings in categories.items():
        category_ratings[cat] = round(sum(ratings) / len(ratings), 1) if ratings else 0
    
    # NPS from surveys
    nps_scores = [s.get("overall_rating", 0) for s in surveys if s.get("overall_rating")]
    promoters = sum(1 for s in nps_scores if s >= 4)
    detractors = sum(1 for s in nps_scores if s <= 2)
    nps = round((promoters - detractors) / max(len(nps_scores), 1) * 100, 1) if nps_scores else 0
    
    return {
        "daily_trend": daily_trend,
        "category_ratings": category_ratings,
        "total_rated_requests": len(rated_requests),
        "total_reviews": len(reviews),
        "total_surveys": len(surveys),
        "nps_score": nps,
        "period_days": days,
    }

@router.get("/tenants/{tenant_slug}/peak-demand")
async def peak_demand(tenant_slug: str, days: int = 30,
                      user=Depends(get_current_user)):
    """Peak demand analysis by hour and day"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    since = (now_utc() - timedelta(days=days)).isoformat()
    
    requests = await find_many_scoped("guest_requests", tid, {"created_at": {"$gte": since}}, limit=2000)
    orders = await find_many_scoped("orders", tid, {"created_at": {"$gte": since}}, limit=2000)
    
    hourly = {str(h).zfill(2): {"requests": 0, "orders": 0} for h in range(24)}
    daily = {"Mon": 0, "Tue": 0, "Wed": 0, "Thu": 0, "Fri": 0, "Sat": 0, "Sun": 0}
    
    for r in requests:
        try:
            dt = datetime.fromisoformat(r.get("created_at", "").replace("Z", "+00:00"))
            hour = str(dt.hour).zfill(2)
            hourly[hour]["requests"] += 1
            day_name = dt.strftime("%a")
            daily[day_name] = daily.get(day_name, 0) + 1
        except:
            pass
    
    for o in orders:
        try:
            dt = datetime.fromisoformat(o.get("created_at", "").replace("Z", "+00:00"))
            hour = str(dt.hour).zfill(2)
            hourly[hour]["orders"] += 1
        except:
            pass
    
    return {
        "hourly_distribution": hourly,
        "daily_distribution": daily,
        "total_requests": len(requests),
        "total_orders": len(orders),
        "period_days": days,
    }

@router.get("/tenants/{tenant_slug}/staff-productivity")
async def staff_productivity(tenant_slug: str, days: int = 30,
                              user=Depends(get_current_user)):
    """Staff productivity report"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    since = (now_utc() - timedelta(days=days)).isoformat()
    
    # Get all requests assigned to staff
    requests = await find_many_scoped("guest_requests", tid, {"created_at": {"$gte": since}}, limit=2000)
    
    staff_stats = {}
    for r in requests:
        assigned = r.get("assigned_to") or r.get("last_updated_by", "Unassigned")
        if assigned not in staff_stats:
            staff_stats[assigned] = {"total": 0, "resolved": 0, "ratings": [], "resolution_times": []}
        
        staff_stats[assigned]["total"] += 1
        if r.get("status") in ["DONE", "CLOSED"]:
            staff_stats[assigned]["resolved"] += 1
        if r.get("rating"):
            staff_stats[assigned]["ratings"].append(r["rating"])
        if r.get("resolved_at") and r.get("created_at"):
            try:
                created = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
                resolved_dt = datetime.fromisoformat(r["resolved_at"].replace("Z", "+00:00"))
                diff_min = (resolved_dt - created).total_seconds() / 60
                staff_stats[assigned]["resolution_times"].append(diff_min)
            except:
                pass
    
    result = []
    for staff, data in staff_stats.items():
        avg_rating = round(sum(data["ratings"]) / len(data["ratings"]), 1) if data["ratings"] else 0
        avg_resolution = round(sum(data["resolution_times"]) / len(data["resolution_times"]), 1) if data["resolution_times"] else 0
        result.append({
            "staff_name": staff,
            "total_assigned": data["total"],
            "resolved": data["resolved"],
            "resolution_rate": round(data["resolved"] / max(data["total"], 1) * 100, 1),
            "avg_rating": avg_rating,
            "avg_resolution_minutes": avg_resolution,
        })
    
    result.sort(key=lambda x: x["resolved"], reverse=True)
    return result

@router.get("/tenants/{tenant_slug}/ai-performance")
async def ai_performance(tenant_slug: str, user=Depends(get_current_user)):
    """AI usage and performance report"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    # AI messages
    ai_messages = await find_many_scoped("messages", tid, {"meta.ai": True}, limit=1000)
    
    # AI sessions
    ai_sessions = await find_many_scoped("ai_sessions", tid, limit=500)
    
    # Token usage
    total_tokens = sum(m.get("meta", {}).get("tokens_used", 0) for m in ai_messages)
    
    # State distribution
    states = {}
    for s in ai_sessions:
        state = s.get("state", "unknown")
        states[state] = states.get(state, 0) + 1
    
    # Offers created by AI
    ai_offers = await count_scoped("offers", tid, {"source": "AI_WEBCHAT"})
    ai_paid = await count_scoped("offers", tid, {"source": "AI_WEBCHAT", "status": "PAID"})
    
    usage = tenant.get("usage_counters", {})
    limit_val = tenant.get("plan_limits", {}).get("monthly_ai_replies", 500)
    
    return {
        "total_ai_messages": len(ai_messages),
        "total_ai_sessions": len(ai_sessions),
        "total_tokens_used": total_tokens,
        "session_states": states,
        "ai_offers_created": ai_offers,
        "ai_offers_paid": ai_paid,
        "ai_conversion_rate": round(ai_paid / max(ai_offers, 1) * 100, 1),
        "monthly_usage": usage.get("ai_replies_this_month", 0),
        "monthly_limit": limit_val,
    }
