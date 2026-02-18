"""Social Dashboard Router - Unified social media management
Aggregated view of all social channels, analytics, moderation
"""
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
    """Unified social media dashboard"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    # Get conversations by channel
    channels = ["WHATSAPP", "INSTAGRAM", "FACEBOOK", "WEBCHAT"]
    channel_stats = {}
    for ch in channels:
        total = await count_scoped("conversations", tid, {"channel": ch})
        open_count = await count_scoped("conversations", tid, {"channel": ch, "status": "open"})
        channel_stats[ch.lower()] = {"total": total, "open": open_count}
    
    # Get reviews by source
    review_sources = ["FACEBOOK", "INSTAGRAM", "GOOGLE", "TRIPADVISOR", "BOOKING"]
    review_stats = {}
    for src in review_sources:
        total = await count_scoped("reviews", tid, {"source": src})
        review_stats[src.lower()] = total
    
    # Recent messages count (last 24h)
    yesterday = (now_utc() - timedelta(hours=24)).isoformat()
    recent_messages = await count_scoped("messages", tid, {"created_at": {"$gte": yesterday}})
    
    # Total reviews
    total_reviews = await count_scoped("reviews", tid)
    avg_rating = 0
    reviews = await find_many_scoped("reviews", tid, limit=500)
    if reviews:
        ratings = [r.get("rating", 0) for r in reviews if r.get("rating")]
        avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0
    
    # Sentiment breakdown
    pos = await count_scoped("reviews", tid, {"sentiment": "POS"})
    neg = await count_scoped("reviews", tid, {"sentiment": "NEG"})
    neu = await count_scoped("reviews", tid, {"sentiment": "NEU"})
    
    # Meta integration status
    meta_cred = await db.connector_credentials.find_one(
        {"tenant_id": tid, "connector_type": "META"}, {"_id": 0}
    )
    meta_status = serialize_doc(meta_cred).get("status", "DISCONNECTED") if meta_cred else "DISCONNECTED"
    
    return {
        "channel_stats": channel_stats,
        "review_stats": review_stats,
        "recent_messages_24h": recent_messages,
        "total_reviews": total_reviews,
        "avg_rating": avg_rating,
        "sentiment": {"positive": pos, "negative": neg, "neutral": neu},
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
    conversations = await find_many_scoped("conversations", tid, query,
                                            sort=[("updated_at", -1)], skip=skip, limit=limit)
    total = await count_scoped("conversations", tid, query)
    
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
        if replied:
            query["reply"] = {"$ne": None}
        else:
            query["reply"] = None
    
    skip = (page - 1) * limit
    reviews = await find_many_scoped("reviews", tid, query,
                                      sort=[("created_at", -1)], skip=skip, limit=limit)
    total = await count_scoped("reviews", tid, query)
    
    return {"data": reviews, "total": total, "page": page}

# Auto-moderation rules
@router.get("/tenants/{tenant_slug}/moderation-rules")
async def list_moderation_rules(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    return await find_many_scoped("moderation_rules", tenant["id"])

@router.post("/tenants/{tenant_slug}/moderation-rules")
async def create_moderation_rule(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    return await insert_scoped("moderation_rules", tenant["id"], {
        "name": data.get("name", ""),
        "trigger_type": data.get("trigger_type", "keyword"),  # keyword, sentiment, spam
        "trigger_value": data.get("trigger_value", ""),
        "action": data.get("action", "flag"),  # flag, hide, auto_reply, escalate
        "auto_reply_text": data.get("auto_reply_text", ""),
        "channels": data.get("channels", []),  # ["FACEBOOK", "INSTAGRAM"]
        "active": data.get("active", True),
    })

# Social Analytics
@router.get("/tenants/{tenant_slug}/analytics")
async def get_social_analytics(tenant_slug: str, days: int = 30,
                                user=Depends(get_current_user)):
    """Social media analytics"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    since = (now_utc() - timedelta(days=days)).isoformat()
    
    # Messages per day
    messages = await find_many_scoped("messages", tid, {"created_at": {"$gte": since}}, limit=5000)
    
    # Group by day
    daily_messages = {}
    for msg in messages:
        day = msg.get("created_at", "")[:10]
        daily_messages[day] = daily_messages.get(day, 0) + 1
    
    # Reviews per day
    reviews = await find_many_scoped("reviews", tid, {"created_at": {"$gte": since}}, limit=1000)
    daily_reviews = {}
    for rev in reviews:
        day = rev.get("created_at", "")[:10]
        daily_reviews[day] = daily_reviews.get(day, 0) + 1
    
    # Response rate
    total_convs = await count_scoped("conversations", tid, {"created_at": {"$gte": since}})
    replied_convs = await count_scoped("conversations", tid, {
        "created_at": {"$gte": since},
        "last_agent_message_at": {"$ne": None}
    })
    response_rate = round(replied_convs / max(total_convs, 1) * 100, 1)
    
    return {
        "daily_messages": daily_messages,
        "daily_reviews": daily_reviews,
        "total_messages": len(messages),
        "total_reviews": len(reviews),
        "response_rate": response_rate,
        "period_days": days,
    }
