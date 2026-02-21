"""Push Notifications Router - Web Push via VAPID
Manages push subscriptions, sending push notifications, VAPID keys.
"""
import os
import json
import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from core.config import db
from core.tenant_guard import (
    resolve_tenant, get_current_user, serialize_doc,
    new_id, now_utc, find_one_scoped, find_many_scoped, count_scoped,
    insert_scoped, update_scoped, delete_scoped, log_audit
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2/push", tags=["push-notifications"])

# VAPID keys - generated once and stored
# In production, these would be in env vars
VAPID_PRIVATE_KEY = None
VAPID_PUBLIC_KEY = None
VAPID_CLAIMS = {"sub": "mailto:admin@hotelapp.com"}


def _get_vapid_keys():
    """Get or generate VAPID keys"""
    global VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY
    if VAPID_PRIVATE_KEY and VAPID_PUBLIC_KEY:
        return VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY
    
    # Try env vars first
    VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "").replace("\\n", "\n")
    VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
    
    if not VAPID_PRIVATE_KEY or not VAPID_PUBLIC_KEY:
        # Generate keys
        try:
            from py_vapid import Vapid
            vapid = Vapid()
            vapid.generate_keys()
            VAPID_PRIVATE_KEY = vapid.private_pem().decode('utf-8')
            VAPID_PUBLIC_KEY = vapid.public_key_urlsafe_base64()
            logger.info(f"Generated new VAPID keys. Public key: {VAPID_PUBLIC_KEY[:20]}...")
        except Exception as e:
            logger.error(f"Failed to generate VAPID keys: {e}")
            # Fallback - use dummy keys for development
            VAPID_PRIVATE_KEY = "dummy_private_key"
            VAPID_PUBLIC_KEY = "dummy_public_key"
    
    return VAPID_PRIVATE_KEY, VAPID_PUBLIC_KEY


async def send_web_push(subscription_info: dict, title: str, body: str, data: dict = None):
    """Send a web push notification"""
    private_key, public_key = _get_vapid_keys()
    if private_key == "dummy_private_key":
        logger.warning("Using dummy VAPID keys - push not actually sent")
        return False
    
    try:
        from pywebpush import webpush, WebPushException
        payload = json.dumps({
            "title": title,
            "body": body,
            "data": data or {},
            "icon": "/logo192.png",
            "badge": "/logo192.png",
            "timestamp": now_utc().isoformat(),
        })
        
        webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=private_key,
            vapid_claims=VAPID_CLAIMS
        )
        return True
    except Exception as e:
        logger.error(f"Push notification failed: {e}")
        return False


# ============ VAPID KEY ============
@router.get("/tenants/{tenant_slug}/vapid-public-key")
async def get_vapid_public_key(tenant_slug: str):
    """Get VAPID public key for push subscription (no auth required for guests)"""
    _, public_key = _get_vapid_keys()
    return {"public_key": public_key}


# ============ SUBSCRIPTIONS ============
@router.post("/tenants/{tenant_slug}/subscribe")
async def subscribe_push(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    """Subscribe to push notifications"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    subscription = data.get("subscription", {})
    if not subscription or not subscription.get("endpoint"):
        raise HTTPException(status_code=400, detail="Valid push subscription required")
    
    user_id = user.get("id", "")
    
    # Check if already subscribed with this endpoint
    existing = await db.push_subscriptions.find_one({
        "tenant_id": tid,
        "user_id": user_id,
        "subscription.endpoint": subscription["endpoint"]
    })
    
    if existing:
        # Update subscription
        await db.push_subscriptions.update_one(
            {"_id": existing["_id"]},
            {"$set": {"subscription": subscription, "updated_at": now_utc().isoformat()}}
        )
        return {"ok": True, "message": "Subscription updated"}
    
    await insert_scoped("push_subscriptions", tid, {
        "user_id": user_id,
        "user_name": user.get("name", ""),
        "subscription": subscription,
        "active": True,
        "device_info": data.get("device_info", ""),
    })
    
    await log_audit(tid, "PUSH_SUBSCRIBED", "push_subscriptions", user_id, user_id)
    return {"ok": True, "message": "Subscribed to push notifications"}


@router.delete("/tenants/{tenant_slug}/unsubscribe")
async def unsubscribe_push(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    """Unsubscribe from push notifications"""
    tenant = await resolve_tenant(tenant_slug)
    endpoint = data.get("endpoint", "")
    if endpoint:
        await db.push_subscriptions.delete_many({
            "tenant_id": tenant["id"],
            "user_id": user.get("id", ""),
            "subscription.endpoint": endpoint
        })
    else:
        await db.push_subscriptions.delete_many({
            "tenant_id": tenant["id"],
            "user_id": user.get("id", ""),
        })
    return {"ok": True, "message": "Unsubscribed from push notifications"}


@router.get("/tenants/{tenant_slug}/subscriptions")
async def list_subscriptions(tenant_slug: str, page: int = 1, limit: int = 50,
                             user=Depends(get_current_user)):
    """List all push subscriptions (admin)"""
    tenant = await resolve_tenant(tenant_slug)
    skip = (page - 1) * limit
    subs = await find_many_scoped("push_subscriptions", tenant["id"], {},
                                   sort=[("created_at", -1)], skip=skip, limit=limit)
    total = await count_scoped("push_subscriptions", tenant["id"])
    return {"data": subs, "total": total, "page": page}


# ============ SEND PUSH ============
@router.post("/tenants/{tenant_slug}/send")
async def send_push_notification(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    """Send push notification to specific user or all subscribers"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    title = data.get("title", "")
    body = data.get("body", "")
    target_user_id = data.get("user_id", "")  # specific user or empty for all
    push_data = data.get("data", {})
    
    if not title or not body:
        raise HTTPException(status_code=400, detail="Title and body required")
    
    query = {"tenant_id": tid, "active": True}
    if target_user_id:
        query["user_id"] = target_user_id
    
    subscriptions = []
    async for sub in db.push_subscriptions.find(query):
        subscriptions.append(sub)
    
    sent = 0
    failed = 0
    for sub in subscriptions:
        success = await send_web_push(sub.get("subscription", {}), title, body, push_data)
        if success:
            sent += 1
        else:
            failed += 1
    
    # Log the push notification
    await insert_scoped("push_logs", tid, {
        "title": title,
        "body": body,
        "target_user_id": target_user_id,
        "sent_count": sent,
        "failed_count": failed,
        "total_targets": len(subscriptions),
        "sent_by": user.get("id", ""),
        "sent_at": now_utc().isoformat(),
    })
    
    await log_audit(tid, "PUSH_SENT", "push_notifications", "", user.get("id", ""),
                    {"title": title, "sent": sent, "failed": failed})
    
    return {"sent": sent, "failed": failed, "total": len(subscriptions)}


@router.post("/tenants/{tenant_slug}/send-bulk")
async def send_bulk_push(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    """Send push notification to all active subscribers"""
    data["user_id"] = ""  # target all
    return await send_push_notification(tenant_slug, data, user)


# ============ PUSH LOG / STATS ============
@router.get("/tenants/{tenant_slug}/push-logs")
async def list_push_logs(tenant_slug: str, page: int = 1, limit: int = 30,
                         user=Depends(get_current_user)):
    """List push notification logs"""
    tenant = await resolve_tenant(tenant_slug)
    skip = (page - 1) * limit
    logs = await find_many_scoped("push_logs", tenant["id"], {},
                                   sort=[("sent_at", -1)], skip=skip, limit=limit)
    total = await count_scoped("push_logs", tenant["id"])
    return {"data": logs, "total": total, "page": page}


@router.get("/tenants/{tenant_slug}/stats")
async def get_push_stats(tenant_slug: str, user=Depends(get_current_user)):
    """Get push notification statistics"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    total_subscribers = await count_scoped("push_subscriptions", tid, {"active": True})
    total_sent = await count_scoped("push_logs", tid)
    
    # Calculate total pushes sent
    pipeline = [
        {"$match": {"tenant_id": tid}},
        {"$group": {"_id": None, "total_pushes": {"$sum": "$sent_count"}, "total_failed": {"$sum": "$failed_count"}}}
    ]
    totals = {"total_pushes": 0, "total_failed": 0}
    async for doc in db.push_logs.aggregate(pipeline):
        totals = {"total_pushes": doc.get("total_pushes", 0), "total_failed": doc.get("total_failed", 0)}
    
    return {
        "total_subscribers": total_subscribers,
        "total_campaigns": total_sent,
        "total_pushes_sent": totals["total_pushes"],
        "total_failed": totals["total_failed"],
        "delivery_rate": round(
            (totals["total_pushes"] / max(totals["total_pushes"] + totals["total_failed"], 1)) * 100, 1
        ) if totals["total_pushes"] > 0 else 0,
    }
