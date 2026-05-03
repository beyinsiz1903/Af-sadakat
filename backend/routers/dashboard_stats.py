"""Dashboard stats routes (basic + enhanced).
Extracted from server.py for maintainability.
Optimized: all independent count_documents run in parallel via asyncio.gather.
"""
import asyncio
import logging
from fastapi import APIRouter

from core.config import db
from core.legacy_helpers import get_tenant_by_slug
from core import cache

logger = logging.getLogger("omnihub.dashboard_stats")
router = APIRouter(prefix="/api", tags=["stats"])


async def _agg_first(coll, pipeline, key, default=0):
    res = await coll.aggregate(pipeline).to_list(1)
    return res[0].get(key, default) if res else default


@router.get("/tenants/{tenant_slug}/stats")
async def get_dashboard_stats(tenant_slug: str):
    return await cache.cached_or_fetch(
        f"stats:{tenant_slug}", ttl=30,
        fetcher=lambda: _build_stats(tenant_slug),
    )


async def _build_stats(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    tid = tenant["id"]

    rating_pipeline = [
        {"$match": {"tenant_id": tid, "rating": {"$ne": None}}},
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}},
    ]

    (
        total_requests, open_requests, in_progress_requests, done_requests,
        total_orders, active_orders,
        total_contacts, total_conversations, rooms_count, tables_count,
        rating_result,
    ) = await asyncio.gather(
        db.guest_requests.count_documents({"tenant_id": tid}),
        db.guest_requests.count_documents({"tenant_id": tid, "status": "OPEN"}),
        db.guest_requests.count_documents({"tenant_id": tid, "status": "IN_PROGRESS"}),
        db.guest_requests.count_documents({"tenant_id": tid, "status": {"$in": ["DONE", "CLOSED"]}}),
        db.orders.count_documents({"tenant_id": tid}),
        db.orders.count_documents({"tenant_id": tid, "status": {"$in": ["RECEIVED", "PREPARING"]}}),
        db.contacts.count_documents({"tenant_id": tid}),
        db.conversations.count_documents({"tenant_id": tid}),
        db.rooms.count_documents({"tenant_id": tid}),
        db.tables.count_documents({"tenant_id": tid}),
        db.guest_requests.aggregate(rating_pipeline).to_list(1),
    )

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
    return await cache.cached_or_fetch(
        f"stats_enhanced:{tenant_slug}", ttl=30,
        fetcher=lambda: _build_enhanced_stats(tenant_slug),
    )


async def _build_enhanced_stats(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    tid = tenant["id"]

    revenue_pipeline = [
        {"$match": {"tenant_id": tid, "order_type": "dine_in"}},
        {"$group": {"_id": None, "total_revenue": {"$sum": "$total"}, "order_count": {"$sum": 1}}},
    ]
    rating_pipeline = [
        {"$match": {"tenant_id": tid, "rating": {"$ne": None}}},
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}},
    ]
    points_pipeline = [
        {"$match": {"tenant_id": tid, "type": "earn"}},
        {"$group": {"_id": None, "total_points": {"$sum": "$points"}}},
    ]

    results = await asyncio.gather(
        db.guest_requests.count_documents({"tenant_id": tid}),                                              # 0
        db.guest_requests.count_documents({"tenant_id": tid, "status": "OPEN"}),                            # 1
        db.guest_requests.count_documents({"tenant_id": tid, "status": "IN_PROGRESS"}),                     # 2
        db.guest_requests.count_documents({"tenant_id": tid, "status": {"$in": ["DONE", "CLOSED"]}}),       # 3
        db.orders.count_documents({"tenant_id": tid}),                                                      # 4
        db.orders.count_documents({"tenant_id": tid, "status": {"$in": ["RECEIVED", "PREPARING"]}}),        # 5
        db.contacts.count_documents({"tenant_id": tid}),                                                    # 6
        db.conversations.count_documents({"tenant_id": tid}),                                               # 7
        db.rooms.count_documents({"tenant_id": tid}),                                                       # 8
        db.tables.count_documents({"tenant_id": tid}),                                                      # 9
        db.orders.aggregate(revenue_pipeline).to_list(1),                                                   # 10
        db.guest_requests.aggregate(rating_pipeline).to_list(1),                                            # 11
        db.reviews.count_documents({"tenant_id": tid}),                                                     # 12
        db.reviews.count_documents({"tenant_id": tid, "sentiment": "positive"}),                            # 13
        db.reviews.count_documents({"tenant_id": tid, "sentiment": "neutral"}),                             # 14
        db.reviews.count_documents({"tenant_id": tid, "sentiment": "negative"}),                            # 15
        db.loyalty_accounts.count_documents({"tenant_id": tid}),                                            # 16
        db.loyalty_ledger.aggregate(points_pipeline).to_list(1),                                            # 17
        db.offers.count_documents({"tenant_id": tid}),                                                      # 18
        db.reservations.count_documents({"tenant_id": tid}),                                                # 19
        db.spa_bookings.count_documents({"tenant_id": tid}),                                                # 20
        db.spa_bookings.count_documents({"tenant_id": tid, "status": "PENDING"}),                           # 21
        db.restaurant_reservations.count_documents({"tenant_id": tid}),                                     # 22
        db.restaurant_reservations.count_documents({"tenant_id": tid, "status": "pending"}),                # 23
        db.restaurant_reservations.count_documents({"tenant_id": tid, "status": "confirmed"}),              # 24
        db.transport_requests.count_documents({"tenant_id": tid}),                                          # 25
        db.transport_requests.count_documents({"tenant_id": tid, "status": "PENDING"}),                     # 26
        db.laundry_requests.count_documents({"tenant_id": tid}),                                            # 27
        db.laundry_requests.count_documents({"tenant_id": tid, "status": "PENDING"}),                       # 28
        db.notifications.count_documents({"tenant_id": tid, "read": False}),                                # 29
        db.guest_surveys.count_documents({"tenant_id": tid}),                                               # 30
        db.lost_found.count_documents({"tenant_id": tid, "status": "stored"}),                              # 31
    )

    rev_result = results[10]
    rating_result = results[11]
    points_result = results[17]

    total_revenue = rev_result[0]["total_revenue"] if rev_result else 0
    avg_rating = round(rating_result[0]["avg_rating"], 1) if rating_result else 0
    rating_count = rating_result[0]["count"] if rating_result else 0
    total_points = points_result[0]["total_points"] if points_result else 0

    return {
        "requests": {"total": results[0], "open": results[1], "in_progress": results[2], "done": results[3]},
        "orders": {"total": results[4], "active": results[5]},
        "contacts": results[6],
        "conversations": results[7],
        "rooms": results[8],
        "tables": results[9],
        "avg_rating": avg_rating,
        "rating_count": rating_count,
        "revenue": {"total": total_revenue, "currency": "TRY"},
        "reviews": {"total": results[12], "sentiment": {
            "positive": results[13], "neutral": results[14], "negative": results[15],
        }},
        "loyalty": {"members": results[16], "total_points_issued": total_points},
        "offers": results[18],
        "reservations": results[19],
        "usage": tenant.get("usage_counters", {}),
        "limits": tenant.get("plan_limits", {}),
        "spa_bookings": {"total": results[20], "pending": results[21]},
        "restaurant_reservations": {"total": results[22], "pending": results[23], "confirmed": results[24]},
        "transport_requests": {"total": results[25], "pending": results[26]},
        "laundry_requests": {"total": results[27], "pending": results[28]},
        "notifications_unread": results[29],
        "surveys": {"total": results[30]},
        "lost_found": {"stored": results[31]},
    }
