"""Analytics engine v2: revenue, ops, staff, AI metrics, guest intelligence, upsell tracking"""
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

def now_utc():
    return datetime.now(timezone.utc)

async def compute_analytics(db, tenant_id: str) -> dict:
    """Compute comprehensive analytics for a tenant"""
    
    # Revenue from orders
    order_revenue = await db.orders.aggregate([
        {"$match": {"tenant_id": tenant_id, "order_type": "dine_in"}},
        {"$group": {"_id": None, "total": {"$sum": "$total"}, "count": {"$sum": 1}}}
    ]).to_list(1)
    
    # Revenue from reservations
    res_revenue = await db.reservations.aggregate([
        {"$match": {"tenant_id": tenant_id}},
        {"$group": {"_id": None, "total": {"$sum": "$price"}, "count": {"$sum": 1}}}
    ]).to_list(1)
    
    order_rev = order_revenue[0]["total"] if order_revenue else 0
    order_count = order_revenue[0]["count"] if order_revenue else 0
    res_rev = res_revenue[0]["total"] if res_revenue else 0
    res_count = res_revenue[0]["count"] if res_revenue else 0
    
    # Repeat guests
    contact_count = await db.contacts.count_documents({"tenant_id": tenant_id})
    repeat_pipeline = [
        {"$match": {"tenant_id": tenant_id, "guest_phone": {"$ne": ""}}},
        {"$group": {"_id": "$guest_phone", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
        {"$count": "repeat"}
    ]
    repeat_result = await db.guest_requests.aggregate(repeat_pipeline).to_list(1)
    repeat_guests = repeat_result[0]["repeat"] if repeat_result else 0
    repeat_rate = round(repeat_guests / max(contact_count, 1) * 100, 1)
    
    # Avg resolution time
    resolution_pipeline = [
        {"$match": {"tenant_id": tenant_id, "first_response_at": {"$ne": None}}},
        {"$project": {
            "response_time": {
                "$subtract": [
                    {"$dateFromString": {"dateString": "$first_response_at"}},
                    {"$dateFromString": {"dateString": "$created_at"}}
                ]
            }
        }},
        {"$group": {"_id": None, "avg_ms": {"$avg": "$response_time"}}}
    ]
    try:
        resolution = await db.guest_requests.aggregate(resolution_pipeline).to_list(1)
        avg_resolution_ms = resolution[0]["avg_ms"] if resolution else 0
        avg_resolution_min = round(avg_resolution_ms / 60000, 1) if avg_resolution_ms else 0
    except Exception:
        avg_resolution_min = 0
    
    # AI efficiency
    total_ai = await db.tenants.find_one({"id": tenant_id})
    ai_replies = total_ai.get("usage_counters", {}).get("ai_replies_this_month", 0) if total_ai else 0
    total_messages = await db.messages.count_documents({"tenant_id": tenant_id})
    total_conversations = await db.conversations.count_documents({"tenant_id": tenant_id})
    ai_efficiency = min(100, round(ai_replies / max(total_messages, 1) * 100, 1))
    
    # Loyalty retention
    loyalty_count = await db.loyalty_accounts.count_documents({"tenant_id": tenant_id})
    loyalty_retention = round(loyalty_count / max(contact_count, 1) * 100, 1)
    
    # Request stats by category
    cat_pipeline = [
        {"$match": {"tenant_id": tenant_id}},
        {"$group": {"_id": "$category", "count": {"$sum": 1}}}
    ]
    categories = await db.guest_requests.aggregate(cat_pipeline).to_list(20)
    category_breakdown = {c["_id"]: c["count"] for c in categories if c["_id"]}
    
    # Rating distribution
    rating_pipeline = [
        {"$match": {"tenant_id": tenant_id, "rating": {"$ne": None}}},
        {"$group": {"_id": "$rating", "count": {"$sum": 1}}}
    ]
    ratings = await db.guest_requests.aggregate(rating_pipeline).to_list(10)
    rating_distribution = {str(r["_id"]): r["count"] for r in ratings}
    
    # Orders by status
    order_status_pipeline = [
        {"$match": {"tenant_id": tenant_id}},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}}
    ]
    order_statuses = await db.orders.aggregate(order_status_pipeline).to_list(10)
    order_by_status = {s["_id"]: s["count"] for s in order_statuses if s["_id"]}
    
    return {
        "revenue": {
            "total": order_rev + res_rev,
            "from_orders": order_rev,
            "from_reservations": res_rev,
            "order_count": order_count,
            "reservation_count": res_count,
            "currency": "TRY"
        },
        "guests": {
            "total_contacts": contact_count,
            "repeat_guests": repeat_guests,
            "repeat_rate": repeat_rate,
            "loyalty_members": loyalty_count,
            "loyalty_retention": loyalty_retention
        },
        "operations": {
            "avg_resolution_time_min": avg_resolution_min,
            "category_breakdown": category_breakdown,
            "rating_distribution": rating_distribution,
            "order_by_status": order_by_status
        },
        "ai": {
            "replies_this_month": ai_replies,
            "total_conversations": total_conversations,
            "efficiency_pct": ai_efficiency
        }
    }

async def compute_revenue_analytics(db, tenant_id: str, period_days: int = 30) -> dict:
    """Revenue analytics v2 - gelir, upsell donusum, tekrar misafir, AI verimlilik KPI"""
    cutoff = (now_utc() - timedelta(days=period_days)).isoformat()
    prev_cutoff = (now_utc() - timedelta(days=period_days * 2)).isoformat()
    
    # Current period revenue
    current_orders = await db.orders.aggregate([
        {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": cutoff}}},
        {"$group": {"_id": None, "total": {"$sum": "$total"}, "count": {"$sum": 1}}}
    ]).to_list(1)
    
    current_res = await db.reservations.aggregate([
        {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": cutoff}}},
        {"$group": {"_id": None, "total": {"$sum": "$price"}, "count": {"$sum": 1}}}
    ]).to_list(1)
    
    # Previous period
    prev_orders = await db.orders.aggregate([
        {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": prev_cutoff, "$lt": cutoff}}},
        {"$group": {"_id": None, "total": {"$sum": "$total"}, "count": {"$sum": 1}}}
    ]).to_list(1)
    
    cur_order_rev = current_orders[0]["total"] if current_orders else 0
    cur_res_rev = current_res[0]["total"] if current_res else 0
    prev_order_rev = prev_orders[0]["total"] if prev_orders else 0
    
    total_revenue = cur_order_rev + cur_res_rev
    revenue_change = round((total_revenue - prev_order_rev) / max(prev_order_rev, 1) * 100, 1) if prev_order_rev else 0
    
    # Upsell conversion (offers that became reservations)
    offers_sent = await db.offers.count_documents({"tenant_id": tenant_id, "created_at": {"$gte": cutoff}})
    offers_paid = await db.offers.count_documents({"tenant_id": tenant_id, "status": "paid", "created_at": {"$gte": cutoff}})
    upsell_rate = round(offers_paid / max(offers_sent, 1) * 100, 1)
    
    # AI contribution
    ai_offers = await db.offers.count_documents({"tenant_id": tenant_id, "source": "AI_WEBCHAT", "created_at": {"$gte": cutoff}})
    ai_paid = await db.offers.count_documents({"tenant_id": tenant_id, "source": "AI_WEBCHAT", "status": "paid", "created_at": {"$gte": cutoff}})
    
    # RevPAR (Revenue Per Available Room)
    room_count = await db.rooms.count_documents({"tenant_id": tenant_id})
    revpar = round(cur_res_rev / max(room_count * period_days, 1), 2)
    
    # Daily revenue breakdown
    daily_pipeline = [
        {"$match": {"tenant_id": tenant_id, "created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": {"$substr": ["$created_at", 0, 10]},
            "total": {"$sum": "$total"},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    daily_revenue = await db.orders.aggregate(daily_pipeline).to_list(period_days)
    
    return {
        "total_revenue": total_revenue,
        "revenue_change_pct": revenue_change,
        "order_revenue": cur_order_rev,
        "reservation_revenue": cur_res_rev,
        "upsell_conversion_rate": upsell_rate,
        "offers_sent": offers_sent,
        "offers_converted": offers_paid,
        "ai_offers_created": ai_offers,
        "ai_offers_converted": ai_paid,
        "revpar": revpar,
        "room_count": room_count,
        "period_days": period_days,
        "daily_revenue": [{"date": d["_id"], "total": d["total"], "count": d["count"]} for d in daily_revenue],
        "currency": "TRY"
    }

async def compute_staff_performance(db, tenant_id: str, period_days: int = 30) -> dict:
    """Staff performance dashboard - personel bazli verimlilik metrikleri"""
    cutoff = (now_utc() - timedelta(days=period_days)).isoformat()
    
    # Get all staff
    users = await db.users.find({"tenant_id": tenant_id}, {"_id": 0}).to_list(100)
    
    staff_metrics = []
    for user in users:
        uid = user["id"]
        name = user.get("name", "Unknown")
        role = user.get("role", "staff")
        
        # Assigned requests
        assigned = await db.guest_requests.count_documents({
            "tenant_id": tenant_id,
            "assigned_to": uid,
            "created_at": {"$gte": cutoff}
        })
        
        # Resolved requests
        resolved = await db.guest_requests.count_documents({
            "tenant_id": tenant_id,
            "assigned_to": uid,
            "status": "resolved",
            "created_at": {"$gte": cutoff}
        })
        
        # Average response time for this staff member
        response_pipeline = [
            {"$match": {
                "tenant_id": tenant_id,
                "assigned_to": uid,
                "first_response_at": {"$ne": None},
                "created_at": {"$gte": cutoff}
            }},
            {"$project": {
                "response_time": {
                    "$subtract": [
                        {"$dateFromString": {"dateString": "$first_response_at"}},
                        {"$dateFromString": {"dateString": "$created_at"}}
                    ]
                }
            }},
            {"$group": {"_id": None, "avg_ms": {"$avg": "$response_time"}}}
        ]
        try:
            resp = await db.guest_requests.aggregate(response_pipeline).to_list(1)
            avg_response_min = round(resp[0]["avg_ms"] / 60000, 1) if resp else 0
        except Exception:
            avg_response_min = 0
        
        # Ratings for this staff
        rating_pipeline = [
            {"$match": {"tenant_id": tenant_id, "assigned_to": uid, "rating": {"$ne": None}}},
            {"$group": {"_id": None, "avg": {"$avg": "$rating"}, "count": {"$sum": 1}}}
        ]
        try:
            rating_result = await db.guest_requests.aggregate(rating_pipeline).to_list(1)
            avg_rating = round(rating_result[0]["avg"], 1) if rating_result else 0
            rating_count = rating_result[0]["count"] if rating_result else 0
        except Exception:
            avg_rating = 0
            rating_count = 0
        
        resolution_rate = round(resolved / max(assigned, 1) * 100, 1)
        
        staff_metrics.append({
            "user_id": uid,
            "name": name,
            "role": role,
            "assigned_requests": assigned,
            "resolved_requests": resolved,
            "resolution_rate": resolution_rate,
            "avg_response_time_min": avg_response_min,
            "avg_rating": avg_rating,
            "rating_count": rating_count,
            "efficiency_score": round((resolution_rate * 0.4 + (avg_rating / 5 * 100) * 0.3 + max(0, 100 - avg_response_min) * 0.3), 1)
        })
    
    # Sort by efficiency score
    staff_metrics.sort(key=lambda x: x["efficiency_score"], reverse=True)
    
    return {
        "staff": staff_metrics,
        "total_staff": len(staff_metrics),
        "period_days": period_days,
        "avg_team_efficiency": round(sum(s["efficiency_score"] for s in staff_metrics) / max(len(staff_metrics), 1), 1)
    }

async def compute_investor_metrics(db) -> dict:
    """Compute investor/demo metrics across all tenants - MRR, aktif tenant, islenen mesaj, AI cevap"""
    total_tenants = await db.tenants.count_documents({})
    active_tenants = await db.tenants.count_documents({"onboarding_completed": True})
    total_users = await db.users.count_documents({})
    total_contacts = await db.contacts.count_documents({})
    total_requests = await db.guest_requests.count_documents({})
    total_orders = await db.orders.count_documents({})
    total_conversations = await db.conversations.count_documents({})
    total_messages = await db.messages.count_documents({})
    total_reviews = await db.reviews.count_documents({})
    total_reservations = await db.reservations.count_documents({})
    
    # Revenue
    rev = await db.orders.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$total"}}}
    ]).to_list(1)
    total_revenue = rev[0]["total"] if rev else 0
    
    res_rev = await db.reservations.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$price"}}}
    ]).to_list(1)
    total_res_revenue = res_rev[0]["total"] if res_rev else 0
    
    # AI usage
    ai_pipeline = await db.tenants.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$usage_counters.ai_replies_this_month"}}}
    ]).to_list(1)
    total_ai = ai_pipeline[0]["total"] if ai_pipeline else 0
    
    # MRR calculation
    plan_prices = {"basic": 49, "pro": 149, "enterprise": 499}
    mrr_pipeline = await db.tenants.aggregate([
        {"$group": {"_id": "$plan", "count": {"$sum": 1}}}
    ]).to_list(10)
    mrr = sum(plan_prices.get(p["_id"], 49) * p["count"] for p in mrr_pipeline)
    arr = mrr * 12
    
    # Plan distribution
    plan_dist = {p["_id"]: p["count"] for p in mrr_pipeline}
    
    # Loyalty metrics
    loyalty_members = await db.loyalty_accounts.count_documents({})
    
    # Growth metrics (last 30 days)
    thirty_days_ago = (now_utc() - timedelta(days=30)).isoformat()
    new_tenants_30d = await db.tenants.count_documents({"created_at": {"$gte": thirty_days_ago}})
    new_contacts_30d = await db.contacts.count_documents({"created_at": {"$gte": thirty_days_ago}})
    
    return {
        "mrr": mrr,
        "arr": arr,
        "total_tenants": total_tenants,
        "active_tenants": active_tenants or total_tenants,
        "total_users": total_users,
        "total_contacts": total_contacts,
        "total_guests_served": total_contacts,
        "total_requests_handled": total_requests,
        "total_orders_processed": total_orders,
        "total_conversations": total_conversations,
        "total_messages_processed": total_messages,
        "total_reviews": total_reviews,
        "total_reservations": total_reservations,
        "total_revenue_processed": total_revenue + total_res_revenue,
        "ai_replies_generated": total_ai,
        "loyalty_members": loyalty_members,
        "plan_distribution": plan_dist,
        "new_tenants_30d": new_tenants_30d,
        "new_contacts_30d": new_contacts_30d,
        "currency": "TRY",
        "timestamp": now_utc().isoformat()
    }
