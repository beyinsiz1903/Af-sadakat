"""Analytics engine: revenue, ops, staff, AI metrics"""
from datetime import datetime, timezone, timedelta

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
    except:
        avg_resolution_min = 0
    
    # AI efficiency (% of conversations with AI-assisted replies)
    total_ai = await db.tenants.find_one({"id": tenant_id})
    ai_replies = total_ai.get("usage_counters", {}).get("ai_replies_this_month", 0) if total_ai else 0
    total_messages = await db.messages.count_documents({"tenant_id": tenant_id})
    total_conversations = await db.conversations.count_documents({"tenant_id": tenant_id})
    # AI assists ratio: how many messages got AI help (capped at 100%)
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
