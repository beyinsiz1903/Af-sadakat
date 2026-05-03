"""Social Dashboard Router - Unified social media management
Aggregated view of all social channels, analytics, moderation
Optimized: N+1 count loops replaced with grouped aggregation pipelines.
"""
import asyncio
from core import cache
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime, timezone, timedelta

from core.config import db
from core.tenant_guard import (
    resolve_tenant, get_current_user, serialize_doc, new_id, now_utc,
    find_one_scoped, find_many_scoped, count_scoped,
    insert_scoped, update_scoped
)

router = APIRouter(prefix="/api/v2/social", tags=["social-dashboard"])


@router.get("/tenants/{tenant_slug}/dashboard")
async def get_social_dashboard(tenant_slug: str, user=Depends(get_current_user)):
    """Unified social media dashboard (cached 60s).
    Optimized: was 13+ sequential queries, now 6 parallel aggregations."""
    return await cache.cached_or_fetch(
        f"social_dashboard:{tenant_slug}", ttl=60,
        fetcher=lambda: _build_social_dashboard(tenant_slug),
    )


async def _build_social_dashboard(tenant_slug: str):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    yesterday = (now_utc() - timedelta(hours=24)).isoformat()

    conv_pipeline = [
        {"$match": {"tenant_id": tid}},
        {"$group": {
            "_id": "$channel",
            "total": {"$sum": 1},
            "open": {"$sum": {"$cond": [{"$eq": ["$status", "open"]}, 1, 0]}},
        }},
    ]
    review_source_pipeline = [
        {"$match": {"tenant_id": tid}},
        {"$group": {"_id": "$source", "count": {"$sum": 1}}},
    ]
    sentiment_pipeline = [
        {"$match": {"tenant_id": tid}},
        {"$group": {
            "_id": None,
            "total": {"$sum": 1},
            "pos": {"$sum": {"$cond": [{"$eq": ["$sentiment", "POS"]}, 1, 0]}},
            "neg": {"$sum": {"$cond": [{"$eq": ["$sentiment", "NEG"]}, 1, 0]}},
            "neu": {"$sum": {"$cond": [{"$eq": ["$sentiment", "NEU"]}, 1, 0]}},
            "rating_sum": {"$sum": {"$ifNull": ["$rating", 0]}},
            "rating_count": {"$sum": {"$cond": [{"$gt": ["$rating", 0]}, 1, 0]}},
        }},
    ]

    conv_docs, review_src_docs, sentiment_docs, recent_messages, meta_cred = await asyncio.gather(
        db.conversations.aggregate(conv_pipeline).to_list(None),
        db.reviews.aggregate(review_source_pipeline).to_list(None),
        db.reviews.aggregate(sentiment_pipeline).to_list(1),
        db.messages.count_documents({"tenant_id": tid, "created_at": {"$gte": yesterday}}),
        db.connector_credentials.find_one({"tenant_id": tid, "connector_type": "META"}, {"_id": 0}),
    )

    channels = ["WHATSAPP", "INSTAGRAM", "FACEBOOK", "WEBCHAT"]
    conv_by_channel = {d["_id"]: d for d in conv_docs}
    channel_stats = {}
    for ch in channels:
        c = conv_by_channel.get(ch, {})
        channel_stats[ch.lower()] = {"total": c.get("total", 0), "open": c.get("open", 0)}

    review_sources = ["FACEBOOK", "INSTAGRAM", "GOOGLE", "TRIPADVISOR", "BOOKING"]
    rev_by_source = {d["_id"]: d.get("count", 0) for d in review_src_docs}
    review_stats = {src.lower(): rev_by_source.get(src, 0) for src in review_sources}

    s = sentiment_docs[0] if sentiment_docs else {}
    total_reviews = s.get("total", 0)
    rating_count = s.get("rating_count", 0)
    avg_rating = round(s.get("rating_sum", 0) / rating_count, 1) if rating_count else 0

    meta_status = serialize_doc(meta_cred).get("status", "DISCONNECTED") if meta_cred else "DISCONNECTED"

    return {
        "channel_stats": channel_stats,
        "review_stats": review_stats,
        "recent_messages_24h": recent_messages,
        "total_reviews": total_reviews,
        "avg_rating": avg_rating,
        "sentiment": {
            "positive": s.get("pos", 0),
            "negative": s.get("neg", 0),
            "neutral": s.get("neu", 0),
        },
        "meta_status": meta_status,
        "total_conversations": sum(v["total"] for v in channel_stats.values()),
        "open_conversations": sum(v["open"] for v in channel_stats.values()),
    }


@router.get("/tenants/{tenant_slug}/unified-inbox")
async def get_unified_inbox(tenant_slug: str, channel: Optional[str] = None,
                            status: Optional[str] = None,
                            page: int = 1, limit: int = 50,
                            user=Depends(get_current_user)):
    """All conversations from all social channels in one view"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    query = {}
    if channel:
        query["channel"] = channel.upper()
    if status:
        query["status"] = status

    skip = (page - 1) * limit
    conversations, total = await asyncio.gather(
        find_many_scoped("conversations", tid, query, sort=[("updated_at", -1)], skip=skip, limit=limit),
        count_scoped("conversations", tid, query),
    )
    return {"data": conversations, "total": total, "page": page}


@router.get("/tenants/{tenant_slug}/all-reviews")
async def get_all_reviews(tenant_slug: str, source: Optional[str] = None,
                          sentiment: Optional[str] = None,
                          replied: Optional[bool] = None,
                          page: int = 1, limit: int = 50,
                          user=Depends(get_current_user)):
    """All reviews from all platforms"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    query = {}
    if source:
        query["source"] = source.upper()
    if sentiment:
        query["sentiment"] = sentiment.upper()
    if replied is not None:
        query["reply"] = {"$ne": None} if replied else None

    skip = (page - 1) * limit
    reviews, total = await asyncio.gather(
        find_many_scoped("reviews", tid, query, sort=[("created_at", -1)], skip=skip, limit=limit),
        count_scoped("reviews", tid, query),
    )
    return {"data": reviews, "total": total, "page": page}


@router.get("/tenants/{tenant_slug}/moderation-rules")
async def list_moderation_rules(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    return await find_many_scoped("moderation_rules", tenant["id"])


@router.post("/tenants/{tenant_slug}/moderation-rules")
async def create_moderation_rule(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    return await insert_scoped("moderation_rules", tenant["id"], {
        "name": data.get("name", ""),
        "trigger_type": data.get("trigger_type", "keyword"),
        "trigger_value": data.get("trigger_value", ""),
        "action": data.get("action", "flag"),
        "auto_reply_text": data.get("auto_reply_text", ""),
        "channels": data.get("channels", []),
        "active": data.get("active", True),
    })


@router.get("/tenants/{tenant_slug}/analytics")
async def get_social_analytics(tenant_slug: str, days: int = 30,
                                user=Depends(get_current_user)):
    """Social media analytics (cached 60s).
    Optimized: 4 parallel queries replace sequential calls."""
    return await cache.cached_or_fetch(
        f"social_analytics:{tenant_slug}:{days}", ttl=60,
        fetcher=lambda: _build_social_analytics(tenant_slug, days),
    )


async def _build_social_analytics(tenant_slug: str, days: int):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    since = (now_utc() - timedelta(days=days)).isoformat()

    msgs_pipeline = [
        {"$match": {"tenant_id": tid, "created_at": {"$gte": since}}},
        {"$group": {"_id": {"$substr": ["$created_at", 0, 10]}, "count": {"$sum": 1}}},
    ]
    revs_pipeline = [
        {"$match": {"tenant_id": tid, "created_at": {"$gte": since}}},
        {"$group": {"_id": {"$substr": ["$created_at", 0, 10]}, "count": {"$sum": 1}}},
    ]

    msg_docs, rev_docs, total_convs, replied_convs = await asyncio.gather(
        db.messages.aggregate(msgs_pipeline).to_list(None),
        db.reviews.aggregate(revs_pipeline).to_list(None),
        count_scoped("conversations", tid, {"created_at": {"$gte": since}}),
        count_scoped("conversations", tid, {"created_at": {"$gte": since}, "last_agent_message_at": {"$ne": None}}),
    )

    daily_messages = {d["_id"]: d["count"] for d in msg_docs if d["_id"]}
    daily_reviews = {d["_id"]: d["count"] for d in rev_docs if d["_id"]}
    total_messages = sum(daily_messages.values())
    total_reviews_period = sum(daily_reviews.values())
    response_rate = round(replied_convs / max(total_convs, 1) * 100, 1)

    return {
        "daily_messages": daily_messages,
        "daily_reviews": daily_reviews,
        "total_messages": total_messages,
        "total_reviews": total_reviews_period,
        "response_rate": response_rate,
        "period_days": days,
    }
