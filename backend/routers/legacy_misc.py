"""Legacy misc routes — extracted from server.py (T007 Faz 2).
Endpoints under /api: requests/comments, kb-articles, reservations, contacts intelligence, audit-logs.
"""
from fastapi import APIRouter, HTTPException, Request
from datetime import timedelta

from core.config import db
from core.legacy_helpers import (
    now_utc, new_id, serialize_doc, get_tenant_by_slug,
)
from rbac import LOYALTY_TIERS, analyze_sentiment, compute_tier, next_tier_info

router = APIRouter(prefix="/api", tags=["legacy-misc"])


@router.post("/tenants/{tenant_slug}/requests/{request_id}/comments")
async def add_request_comment(tenant_slug: str, request_id: str, data: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    req = await db.guest_requests.find_one({"id": request_id, "tenant_id": tenant["id"]})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    comment = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "request_id": request_id,
        "body": data.get("body", ""),
        "created_by_user_id": data.get("user_id", ""),
        "created_by_name": data.get("user_name", ""),
        "created_at": now_utc().isoformat()
    }
    await db.request_comments.insert_one(comment)
    return serialize_doc(comment)

@router.get("/tenants/{tenant_slug}/requests/{request_id}/comments")
async def list_request_comments(tenant_slug: str, request_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    comments = await db.request_comments.find(
        {"tenant_id": tenant["id"], "request_id": request_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(100)
    return [serialize_doc(c) for c in comments]

@router.get("/tenants/{tenant_slug}/kb-articles")
async def list_kb_articles(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    articles = await db.kb_articles.find({"tenant_id": tenant["id"]}, {"_id": 0}).to_list(100)
    return [serialize_doc(a) for a in articles]

@router.post("/tenants/{tenant_slug}/kb-articles")
async def create_kb_article(tenant_slug: str, data: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    article = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "title": data.get("title", ""),
        "content": data.get("content", ""),
        "tags": data.get("tags", []),
        "created_at": now_utc().isoformat()
    }
    await db.kb_articles.insert_one(article)
    return serialize_doc(article)

@router.get("/tenants/{tenant_slug}/reservations")
async def list_reservations(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    reservations = await db.reservations.find({"tenant_id": tenant["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [serialize_doc(r) for r in reservations]

@router.get("/tenants/{tenant_slug}/contacts/{contact_id}/intelligence")
async def get_contact_intelligence(tenant_slug: str, contact_id: str):
    """Compute and return guest intelligence data"""
    tenant = await get_tenant_by_slug(tenant_slug)
    contact = await db.contacts.find_one({"id": contact_id, "tenant_id": tenant["id"]}, {"_id": 0})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    phone = contact.get("phone", "")
    email = contact.get("email", "")
    
    # Compute metrics
    req_query = {"tenant_id": tenant["id"]}
    if phone:
        req_query["guest_phone"] = phone
    
    requests_list = await db.guest_requests.find(req_query, {"_id": 0}).to_list(500)
    orders_list = await db.orders.find({"tenant_id": tenant["id"], "guest_phone": phone}, {"_id": 0}).to_list(500) if phone else []
    
    visit_count = len(set([r.get("room_code", "") for r in requests_list])) + len(set([o.get("table_code", "") for o in orders_list]))
    
    ratings = [r["rating"] for r in requests_list if r.get("rating")]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0
    
    total_spend = sum(o.get("total", 0) for o in orders_list)
    
    complaints = [r for r in requests_list if r.get("priority") in ["high", "urgent"] or analyze_sentiment(r.get("description", "")) == "negative"]
    complaint_ratio = round(len(complaints) / max(len(requests_list), 1), 2)
    
    # Last sentiment
    all_texts = [r.get("description", "") for r in requests_list] + [r.get("rating_comment", "") for r in requests_list if r.get("rating_comment")]
    last_sentiment = analyze_sentiment(all_texts[-1]) if all_texts else "neutral"
    
    # Preferred room type
    room_types = [r.get("room_code", "")[:1] for r in requests_list if r.get("room_code")]
    
    # Favorite menu items
    item_counts = {}
    for o in orders_list:
        for item in o.get("items", []):
            name = item.get("menu_item_name", "")
            item_counts[name] = item_counts.get(name, 0) + item.get("quantity", 1)
    favorite_items = sorted(item_counts.items(), key=lambda x: -x[1])[:5]
    
    # Alerts
    alerts = []
    if complaint_ratio > 0.3:
        alerts.append({"type": "warning", "message": f"High complaint ratio ({int(complaint_ratio*100)}%)"})
    for r in requests_list[-3:]:
        if r.get("priority") in ["high", "urgent"] and r.get("status") in ["OPEN", "IN_PROGRESS"]:
            alerts.append({"type": "urgent", "message": f"Active {r['priority']} request: {r['description'][:50]}"})
    if avg_rating > 0 and avg_rating < 3:
        alerts.append({"type": "warning", "message": f"Low average rating: {avg_rating}/5"})
    
    # Loyalty
    loyalty_info = None
    if contact.get("loyalty_account_id"):
        account = await db.loyalty_accounts.find_one({"id": contact["loyalty_account_id"]}, {"_id": 0})
        if account:
            tier = compute_tier(account.get("points", 0))
            loyalty_info = {
                "points": account.get("points", 0),
                "tier": tier,
                "tier_info": LOYALTY_TIERS.get(tier, {}),
                "next_tier": next_tier_info(tier, account.get("points", 0))
            }
    
    intelligence = {
        "visit_count": visit_count,
        "avg_rating": avg_rating,
        "total_spend": total_spend,
        "complaint_ratio": complaint_ratio,
        "last_sentiment": last_sentiment,
        "preferred_language": contact.get("preferred_language", "en"),
        "favorite_menu_items": [{"name": n, "count": c} for n, c in favorite_items],
        "total_requests": len(requests_list),
        "total_orders": len(orders_list),
        "alerts": alerts,
        "loyalty": loyalty_info
    }
    
    # Update contact with computed fields
    await db.contacts.update_one({"id": contact_id}, {"$set": {
        "intelligence": intelligence,
        "updated_at": now_utc().isoformat()
    }})
    
    return intelligence

@router.get("/tenants/{tenant_slug}/audit-logs")
async def list_audit_logs(tenant_slug: str, page: int = 1, limit: int = 50):
    tenant = await get_tenant_by_slug(tenant_slug)
    skip = (page - 1) * limit
    logs = await db.audit_logs.find({"tenant_id": tenant["id"]}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.audit_logs.count_documents({"tenant_id": tenant["id"]})
    return {"data": [serialize_doc(l) for l in logs], "total": total, "page": page}

