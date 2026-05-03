"""Reviews V2 Router: Review listing, sentiment, replies, AI suggestions
Full tenant_guard isolation. AI usage enforcement.
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from core.config import db
from core.tenant_guard import (
    resolve_tenant, get_current_user, serialize_doc,
    new_id, now_utc, find_one_scoped, find_many_scoped, count_scoped,
    insert_scoped, update_scoped, log_audit
)
from ai_provider import generate_review_reply, classify_sentiment

router = APIRouter(prefix="/api/v2/reviews", tags=["reviews"])


async def _check_ai_limit(tenant_id, tenant):
    month_key = now_utc().strftime("%Y-%m")
    counter = await db.usage_counters.find_one({"tenant_id": tenant_id, "month_key": month_key}, {"_id": 0})
    used = counter.get("ai_replies_used", 0) if counter else 0
    limit = counter.get("ai_replies_limit", tenant.get("plan_limits", {}).get("monthly_ai_replies", 50)) if counter else tenant.get("plan_limits", {}).get("monthly_ai_replies", 50)
    if used >= limit:
        raise HTTPException(status_code=402, detail={"code": "AI_LIMIT_EXCEEDED",
            "message": f"AI limit reached ({used}/{limit}).", "used": used, "limit": limit})
    return used, limit

async def _increment_ai_usage(tenant_id):
    month_key = now_utc().strftime("%Y-%m")
    await db.usage_counters.update_one({"tenant_id": tenant_id, "month_key": month_key},
        {"$inc": {"ai_replies_used": 1}, "$set": {"updated_at": now_utc().isoformat()}}, upsert=True)
    await db.tenants.update_one({"id": tenant_id}, {"$inc": {"usage_counters.ai_replies_this_month": 1}})


@router.get("/tenants/{tenant_slug}")
async def list_reviews(tenant_slug: str, source: Optional[str] = None,
                        sentiment: Optional[str] = None, rating: Optional[int] = None,
                        page: int = 1, limit: int = 20, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if source:
        query["source_type"] = source.upper()
    if sentiment:
        query["sentiment"] = sentiment.upper()
    if rating:
        query["rating"] = rating

    skip_val = (page - 1) * limit
    reviews = await find_many_scoped("reviews", tenant["id"], query,
                                      sort=[("created_at", -1)], skip=skip_val, limit=limit)
    total = await count_scoped("reviews", tenant["id"], query)

    # Summary counts
    pos = await count_scoped("reviews", tenant["id"], {"sentiment": "POS"})
    neu = await count_scoped("reviews", tenant["id"], {"sentiment": "NEU"})
    neg = await count_scoped("reviews", tenant["id"], {"sentiment": "NEG"})

    # Enrich with replies
    for review in reviews:
        reply = await db.review_replies.find_one(
            {"tenant_id": tenant["id"], "review_id": review["id"]}, {"_id": 0},
            sort=[("created_at", -1)]
        )
        review["reply"] = serialize_doc(reply) if reply else None

    return {
        "data": reviews,
        "total": total,
        "page": page,
        "summary": {"positive": pos, "neutral": neu, "negative": neg}
    }

@router.get("/tenants/{tenant_slug}/{review_id}")
async def get_review(tenant_slug: str, review_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    review = await find_one_scoped("reviews", tenant["id"], {"id": review_id})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    replies = await find_many_scoped("review_replies", tenant["id"],
                                      {"review_id": review_id}, sort=[("created_at", 1)])
    return {"review": review, "replies": replies}

@router.post("/tenants/{tenant_slug}/{review_id}/reply")
async def reply_to_review(tenant_slug: str, review_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    review = await find_one_scoped("reviews", tenant["id"], {"id": review_id})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    body = data.get("text", data.get("body", "")).strip()
    if not body:
        raise HTTPException(status_code=400, detail="Reply text required")

    reply = await insert_scoped("review_replies", tenant["id"], {
        "review_id": review_id,
        "body": body,
        "created_by_user_id": user.get("id", ""),
        "created_by_name": user.get("name", "Management"),
    })

    await update_scoped("reviews", tenant["id"], review_id, {
        "replied": True, "last_updated_by": user.get("name", ""),
    })

    # If Meta comment, also reply via Graph API
    source = review.get("source_type", "")
    if source in ("FACEBOOK_COMMENT", "INSTAGRAM_COMMENT"):
        comment_id = review.get("extra", {}).get("comment_id", "")
        if comment_id:
            try:
                from services.meta_provider import get_meta_credentials, reply_to_comment, MetaAPIError
                cred = await get_meta_credentials(tenant["id"])
                if cred and cred.get("access_token"):
                    await reply_to_comment(comment_id, cred["access_token"], body)
                    await log_audit(tenant["id"], "REVIEW_REPLY_META", "review", review_id, user.get("id", ""))
            except MetaAPIError as e:
                import logging as _log
                _log.getLogger("omnihub.reviews").warning(f"Meta comment reply failed: {e}")
            except Exception:
                pass

    await log_audit(tenant["id"], "review_reply_created", "review", review_id, user.get("id", ""))

    try:
        from server import ws_manager
        await ws_manager.broadcast_tenant(tenant["id"], "review", "review_reply", "created",
                                           {"review_id": review_id, "reply": reply})
    except Exception:
        pass

    return reply

@router.post("/tenants/{tenant_slug}/{review_id}/ai-suggest")
async def ai_suggest_review(tenant_slug: str, review_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    review = await find_one_scoped("reviews", tenant["id"], {"id": review_id})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    used, limit = await _check_ai_limit(tenant["id"], tenant)

    result = generate_review_reply(
        review.get("text", ""),
        review.get("sentiment", "NEU"),
        review.get("author_name", ""),
        tenant.get("name", "Our Hotel")
    )

    await _increment_ai_usage(tenant["id"])
    await log_audit(tenant["id"], "ai_suggestion_generated", "review", review_id, user.get("id", ""),
                    {"sentiment": result["sentiment"], "usage": f"{used+1}/{limit}"})

    result["usage"] = {"used": used + 1, "limit": limit}
    return result

@router.post("/tenants/{tenant_slug}/{review_id}/mark-resolved")
async def mark_review_resolved(tenant_slug: str, review_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    updated = await update_scoped("reviews", tenant["id"], review_id,
                                   {"resolved": True, "last_updated_by": user.get("name", "")})
    if not updated:
        raise HTTPException(status_code=404, detail="Review not found")
    return updated
