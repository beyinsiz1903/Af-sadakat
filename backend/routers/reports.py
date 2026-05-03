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
from core import cache

router = APIRouter(prefix="/api/v2/reports", tags=["reports"])

@router.get("/tenants/{tenant_slug}/department-performance")
async def department_performance(tenant_slug: str, days: int = 30,
                                  user=Depends(get_current_user)):
    """Department performance report (cached 60s).
    Optimized: single aggregation pipeline replaces N+1 (was 4 queries per department)."""
    return await cache.cached_or_fetch(
        f"reports_deptperf:{tenant_slug}:{days}", ttl=60,
        fetcher=lambda: _build_department_performance(tenant_slug, days),
    )


async def _build_department_performance(tenant_slug: str, days: int):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    since = (now_utc() - timedelta(days=days)).isoformat()

    departments = await find_many_scoped("departments", tid)
    if not departments:
        return []

    # Single aggregation: group all requests by department_code in one pass.
    # Pre-parse dates (NULL on parse error) so denominator only counts valid pairs.
    pipeline = [
        {"$match": {"tenant_id": tid, "created_at": {"$gte": since}}},
        {"$addFields": {
            "_created_dt": {"$dateFromString": {"dateString": "$created_at", "onError": None}},
            "_resolved_dt": {"$dateFromString": {"dateString": {"$ifNull": ["$resolved_at", ""]}, "onError": None}},
        }},
        {"$addFields": {
            "_has_valid_pair": {"$and": [
                {"$ne": ["$_created_dt", None]},
                {"$ne": ["$_resolved_dt", None]},
            ]},
        }},
        {"$group": {
            "_id": "$department_code",
            "total": {"$sum": 1},
            "resolved": {"$sum": {"$cond": [{"$in": ["$status", ["DONE", "CLOSED"]]}, 1, 0]}},
            "open": {"$sum": {"$cond": [{"$eq": ["$status", "OPEN"]}, 1, 0]}},
            "rating_sum": {"$sum": {"$ifNull": ["$rating", 0]}},
            "rating_count": {"$sum": {"$cond": [{"$ne": ["$rating", None]}, 1, 0]}},
            "resolution_minutes_sum": {"$sum": {
                "$cond": [
                    "$_has_valid_pair",
                    {"$divide": [{"$subtract": ["$_resolved_dt", "$_created_dt"]}, 60000]},
                    0,
                ]
            }},
            "resolved_with_time_count": {"$sum": {"$cond": ["$_has_valid_pair", 1, 0]}},
        }},
    ]
    agg = {doc["_id"]: doc async for doc in db.guest_requests.aggregate(pipeline)}

    dept_stats = []
    for dept in departments:
        code = dept.get("code", "")
        d = agg.get(code, {})
        total = d.get("total", 0)
        resolved = d.get("resolved", 0)
        rating_count = d.get("rating_count", 0)
        rt_count = d.get("resolved_with_time_count", 0)
        avg_rating = round(d.get("rating_sum", 0) / rating_count, 1) if rating_count else 0
        avg_resolution = round(d.get("resolution_minutes_sum", 0) / rt_count, 1) if rt_count else 0

        dept_stats.append({
            "department": dept.get("name", code),
            "code": code,
            "total_requests": total,
            "resolved": resolved,
            "open": d.get("open", 0),
            "resolution_rate": round(resolved / max(total, 1) * 100, 1),
            "avg_resolution_minutes": avg_resolution,
            "avg_rating": avg_rating,
            "total_ratings": rating_count,
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
        except Exception:
            pass
    
    for o in orders:
        try:
            dt = datetime.fromisoformat(o.get("created_at", "").replace("Z", "+00:00"))
            hour = str(dt.hour).zfill(2)
            hourly[hour]["orders"] += 1
        except Exception:
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
            except Exception:
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


@router.get("/tenants/{tenant_slug}/ab-testing-report")
async def ab_testing_report(tenant_slug: str, user=Depends(get_current_user)):
    """A/B Testing comprehensive report"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    # All experiments
    experiments = await find_many_scoped("ab_experiments", tid, {}, sort=[("created_at", -1)])
    
    total = len(experiments)
    running = sum(1 for e in experiments if e.get("status") == "running")
    completed = sum(1 for e in experiments if e.get("status") == "completed")
    draft = sum(1 for e in experiments if e.get("status") == "draft")
    paused = sum(1 for e in experiments if e.get("status") == "paused")
    
    total_participants = await count_scoped("ab_assignments", tid)
    total_events = await count_scoped("ab_events", tid)
    
    # Per-experiment details with results
    experiment_results = []
    for exp in experiments:
        exp_id = exp.get("id", "")
        variants = exp.get("variants", [])
        
        variant_results = []
        for v in variants:
            vname = v.get("name", "")
            
            assignment_count = await db.ab_assignments.count_documents({
                "tenant_id": tid, "experiment_id": exp_id, "variant": vname
            })
            event_count = await db.ab_events.count_documents({
                "tenant_id": tid, "experiment_id": exp_id, "variant": vname
            })
            
            # Unique converters
            converter_pipeline = [
                {"$match": {
                    "tenant_id": tid, "experiment_id": exp_id, "variant": vname,
                    "event_name": {"$in": ["conversion", "purchase", "booking", "signup"]}
                }},
                {"$group": {"_id": "$user_id"}},
                {"$count": "c"}
            ]
            converters = 0
            async for doc in db.ab_events.aggregate(converter_pipeline):
                converters = doc.get("c", 0)
            
            conversion_rate = round((converters / max(assignment_count, 1)) * 100, 2)
            
            variant_results.append({
                "variant": vname,
                "traffic_percent": v.get("traffic_percent", 0),
                "participants": assignment_count,
                "events": event_count,
                "converters": converters,
                "conversion_rate": conversion_rate,
            })
        
        # Determine winner
        winner = None
        if len(variant_results) >= 2 and exp.get("status") in ["running", "completed"]:
            sorted_v = sorted(variant_results, key=lambda r: r["conversion_rate"], reverse=True)
            if sorted_v[0]["conversion_rate"] > sorted_v[1]["conversion_rate"] and sorted_v[0]["participants"] > 0:
                winner = sorted_v[0]["variant"]
        
        experiment_results.append({
            "id": exp_id,
            "name": exp.get("name", ""),
            "status": exp.get("status", ""),
            "feature_area": exp.get("feature_area", ""),
            "hypothesis": exp.get("hypothesis", ""),
            "primary_metric": exp.get("primary_metric", ""),
            "total_participants": exp.get("total_participants", 0),
            "variants": variant_results,
            "winner": winner,
            "start_date": exp.get("start_date", ""),
            "end_date": exp.get("end_date", ""),
        })
    
    # Feature area distribution
    area_dist = {}
    for exp in experiments:
        area = exp.get("feature_area", "general")
        area_dist[area] = area_dist.get(area, 0) + 1
    
    return {
        "summary": {
            "total_experiments": total,
            "running": running,
            "completed": completed,
            "draft": draft,
            "paused": paused,
            "total_participants": total_participants,
            "total_events_tracked": total_events,
        },
        "experiments": experiment_results,
        "feature_area_distribution": area_dist,
    }
