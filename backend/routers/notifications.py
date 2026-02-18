"""Notifications Router - In-app notification center
Push notifications, notification preferences, department routing
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional

from core.config import db
from core.tenant_guard import (
    resolve_tenant, get_current_user, serialize_doc, new_id, now_utc,
    find_one_scoped, find_many_scoped, count_scoped,
    insert_scoped, update_scoped, delete_scoped
)

router = APIRouter(prefix="/api/v2/notifications", tags=["notifications"])

@router.get("/tenants/{tenant_slug}/notifications")
async def list_notifications(tenant_slug: str, unread_only: bool = False,
                            department: Optional[str] = None,
                            page: int = 1, limit: int = 50,
                            user=Depends(get_current_user)):
    """List notifications for the current user/department"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    query = {}
    if unread_only:
        query["read"] = False
    if department:
        query["department_code"] = department.upper()
    
    skip = (page - 1) * limit
    notifications = await find_many_scoped("notifications", tid, query,
                                           sort=[("created_at", -1)], skip=skip, limit=limit)
    total = await count_scoped("notifications", tid, query)
    unread_count = await count_scoped("notifications", tid, {"read": False})
    
    return {"data": notifications, "total": total, "unread_count": unread_count, "page": page}

@router.post("/tenants/{tenant_slug}/notifications/{notif_id}/read")
async def mark_notification_read(tenant_slug: str, notif_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    return await update_scoped("notifications", tenant["id"], notif_id, {"read": True, "read_by": user.get("id", "")})

@router.post("/tenants/{tenant_slug}/notifications/mark-all-read")
async def mark_all_read(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    await db.notifications.update_many(
        {"tenant_id": tenant["id"], "read": False},
        {"$set": {"read": True, "read_by": user.get("id", ""), "updated_at": now_utc().isoformat()}}
    )
    return {"ok": True}

@router.get("/tenants/{tenant_slug}/notifications/unread-count")
async def get_unread_count(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    count = await count_scoped("notifications", tenant["id"], {"read": False})
    return {"unread_count": count}

@router.post("/tenants/{tenant_slug}/notifications")
async def create_notification(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    """Create notification manually"""
    tenant = await resolve_tenant(tenant_slug)
    return await insert_scoped("notifications", tenant["id"], {
        "type": data.get("type", "CUSTOM"),
        "title": data.get("title", ""),
        "body": data.get("body", ""),
        "department_code": data.get("department_code", ""),
        "entity_type": data.get("entity_type", ""),
        "entity_id": data.get("entity_id", ""),
        "read": False,
        "priority": data.get("priority", "normal"),
        "sound": data.get("sound", True),
        "created_by": user.get("id", ""),
    })

# Notification Preferences
@router.get("/tenants/{tenant_slug}/notification-preferences")
async def get_notification_preferences(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    prefs = await db.notification_preferences.find_one(
        {"tenant_id": tenant["id"], "user_id": user["id"]}, {"_id": 0}
    )
    if not prefs:
        prefs = {
            "sound_enabled": True,
            "desktop_push": True,
            "email_enabled": False,
            "sms_enabled": False,
            "new_request": True,
            "request_update": True,
            "new_order": True,
            "new_message": True,
            "sla_breach": True,
            "new_review": True,
        }
    return serialize_doc(prefs) if isinstance(prefs, dict) and "_id" in prefs else prefs

@router.put("/tenants/{tenant_slug}/notification-preferences")
async def update_notification_preferences(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    uid = user["id"]
    
    existing = await db.notification_preferences.find_one({"tenant_id": tid, "user_id": uid})
    prefs = {
        "tenant_id": tid,
        "user_id": uid,
        "sound_enabled": data.get("sound_enabled", True),
        "desktop_push": data.get("desktop_push", True),
        "email_enabled": data.get("email_enabled", False),
        "sms_enabled": data.get("sms_enabled", False),
        "new_request": data.get("new_request", True),
        "request_update": data.get("request_update", True),
        "new_order": data.get("new_order", True),
        "new_message": data.get("new_message", True),
        "sla_breach": data.get("sla_breach", True),
        "new_review": data.get("new_review", True),
        "updated_at": now_utc().isoformat(),
    }
    
    if existing:
        await db.notification_preferences.update_one({"tenant_id": tid, "user_id": uid}, {"$set": prefs})
    else:
        prefs["id"] = new_id()
        prefs["created_at"] = now_utc().isoformat()
        await db.notification_preferences.insert_one(prefs)
    
    return prefs
