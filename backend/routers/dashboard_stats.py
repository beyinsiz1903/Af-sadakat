"""Dashboard stats routes (basic + enhanced).
Extracted from server.py for maintainability.
"""
from fastapi import APIRouter
import logging

from core.config import db
from core.legacy_helpers import get_tenant_by_slug

logger = logging.getLogger("omnihub.dashboard_stats")
router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/tenants/{tenant_slug}/stats")
async def get_dashboard_stats(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    tid = tenant["id"]

    total_requests = await db.guest_requests.count_documents({"tenant_id": tid})
    open_requests = await db.guest_requests.count_documents({"tenant_id": tid, "status": "OPEN"})
    in_progress_requests = await db.guest_requests.count_documents({"tenant_id": tid, "status": "IN_PROGRESS"})
    done_requests = await db.guest_requests.count_documents({"tenant_id": tid, "status": {"$in": ["DONE", "CLOSED"]}})

    total_orders = await db.orders.count_documents({"tenant_id": tid})
    active_orders = await db.orders.count_documents({"tenant_id": tid, "status": {"$in": ["RECEIVED", "PREPARING"]}})

    total_contacts = await db.contacts.count_documents({"tenant_id": tid})
    total_conversations = await db.conversations.count_documents({"tenant_id": tid})
    rooms_count = await db.rooms.count_documents({"tenant_id": tid})
    tables_count = await db.tables.count_documents({"tenant_id": tid})

    pipeline = [
        {"$match": {"tenant_id": tid, "rating": {"$ne": None}}},
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}},
    ]
    rating_result = await db.guest_requests.aggregate(pipeline).to_list(1)
    avg_rating = round(rating_result[0]["avg_rating"], 1) if rating_result else 0
    rating_count = rating_result[0]["count"] if rating_result else 0

    return {
        "requests": {"total": total_requests, "open": open_requests, "in_progress": in_progress_requests, "done": done_requests},
        "orders": {"total": total_orders, "active": active_orders},
        "contacts": total_contacts,
        "conversations": total_conversations,
        "rooms": rooms_count,
        "tables": tables_count,
        "avg_rating": avg_rating,
        "rating_count": rating_count,
        "usage": tenant.get("usage_counters", {}),
        "limits": tenant.get("plan_limits", {}),
    }


@router.get("/tenants/{tenant_slug}/stats/enhanced")
async def get_enhanced_stats(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    tid = tenant["id"]

    total_requests = await db.guest_requests.count_documents({"tenant_id": tid})
    open_requests = await db.guest_requests.count_documents({"tenant_id": tid, "status": "OPEN"})
    in_progress = await db.guest_requests.count_documents({"tenant_id": tid, "status": "IN_PROGRESS"})
    done = await db.guest_requests.count_documents({"tenant_id": tid, "status": {"$in": ["DONE", "CLOSED"]}})

    total_orders = await db.orders.count_documents({"tenant_id": tid})
    active_orders = await db.orders.count_documents({"tenant_id": tid, "status": {"$in": ["RECEIVED", "PREPARING"]}})

    total_contacts = await db.contacts.count_documents({"tenant_id": tid})
    total_conversations = await db.conversations.count_documents({"tenant_id": tid})
    rooms_count = await db.rooms.count_documents({"tenant_id": tid})
    tables_count = await db.tables.count_documents({"tenant_id": tid})

    revenue_pipeline = [
        {"$match": {"tenant_id": tid, "order_type": "dine_in"}},
        {"$group": {"_id": None, "total_revenue": {"$sum": "$total"}, "order_count": {"$sum": 1}}},
    ]
    rev_result = await db.orders.aggregate(revenue_pipeline).to_list(1)
    total_revenue = rev_result[0]["total_revenue"] if rev_result else 0

    rating_pipeline = [
        {"$match": {"tenant_id": tid, "rating": {"$ne": None}}},
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}},
    ]
    rating_result = await db.guest_requests.aggregate(rating_pipeline).to_list(1)
    avg_rating = round(rating_result[0]["avg_rating"], 1) if rating_result else 0
    rating_count = rating_result[0]["count"] if rating_result else 0

    total_reviews = await db.reviews.count_documents({"tenant_id": tid})
    review_sentiment = {
        "positive": await db.reviews.count_documents({"tenant_id": tid, "sentiment": "positive"}),
        "neutral": await db.reviews.count_documents({"tenant_id": tid, "sentiment": "neutral"}),
        "negative": await db.reviews.count_documents({"tenant_id": tid, "sentiment": "negative"}),
    }

    loyalty_members = await db.loyalty_accounts.count_documents({"tenant_id": tid})
    points_pipeline = [
        {"$match": {"tenant_id": tid, "type": "earn"}},
        {"$group": {"_id": None, "total_points": {"$sum": "$points"}}},
    ]
    points_result = await db.loyalty_ledger.aggregate(points_pipeline).to_list(1)
    total_points = points_result[0]["total_points"] if points_result else 0

    total_offers = await db.offers.count_documents({"tenant_id": tid})
    total_reservations = await db.reservations.count_documents({"tenant_id": tid})

    return {
        "requests": {"total": total_requests, "open": open_requests, "in_progress": in_progress, "done": done},
        "orders": {"total": total_orders, "active": active_orders},
        "contacts": total_contacts,
        "conversations": total_conversations,
        "rooms": rooms_count,
        "tables": tables_count,
        "avg_rating": avg_rating,
        "rating_count": rating_count,
        "revenue": {"total": total_revenue, "currency": "TRY"},
        "reviews": {"total": total_reviews, "sentiment": review_sentiment},
        "loyalty": {"members": loyalty_members, "total_points_issued": total_points},
        "offers": total_offers,
        "reservations": total_reservations,
        "usage": tenant.get("usage_counters", {}),
        "limits": tenant.get("plan_limits", {}),
        "spa_bookings": {
            "total": await db.spa_bookings.count_documents({"tenant_id": tid}),
            "pending": await db.spa_bookings.count_documents({"tenant_id": tid, "status": "PENDING"}),
        },
        "restaurant_reservations": {
            "total": await db.restaurant_reservations.count_documents({"tenant_id": tid}),
            "pending": await db.restaurant_reservations.count_documents({"tenant_id": tid, "status": "pending"}),
            "confirmed": await db.restaurant_reservations.count_documents({"tenant_id": tid, "status": "confirmed"}),
        },
        "transport_requests": {
            "total": await db.transport_requests.count_documents({"tenant_id": tid}),
            "pending": await db.transport_requests.count_documents({"tenant_id": tid, "status": "PENDING"}),
        },
        "laundry_requests": {
            "total": await db.laundry_requests.count_documents({"tenant_id": tid}),
            "pending": await db.laundry_requests.count_documents({"tenant_id": tid, "status": "PENDING"}),
        },
        "notifications_unread": await db.notifications.count_documents({"tenant_id": tid, "read": False}),
        "surveys": {
            "total": await db.guest_surveys.count_documents({"tenant_id": tid}),
        },
        "lost_found": {
            "stored": await db.lost_found.count_documents({"tenant_id": tid, "status": "stored"}),
        },
    }
