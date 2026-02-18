"""Platform Integrations Router - Google Business, TripAdvisor, Booking.com
Connector framework for review/message aggregation from external platforms
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, Dict, List
import os
import logging

from core.config import db
from core.tenant_guard import (
    resolve_tenant, get_current_user, serialize_doc, new_id, now_utc,
    find_one_scoped, find_many_scoped, count_scoped,
    insert_scoped, update_scoped, log_audit
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/platforms", tags=["platform-integrations"])

# ---- Platform Definitions ----
PLATFORMS = {
    "google_business": {
        "name": "Google Business Profile",
        "description": "Manage Google reviews and messages",
        "icon": "google",
        "features": ["reviews", "messages", "q_and_a", "posts"],
        "auth_type": "oauth2",
        "setup_url": "https://business.google.com",
        "api_docs": "https://developers.google.com/my-business",
    },
    "tripadvisor": {
        "name": "TripAdvisor",
        "description": "Manage TripAdvisor reviews and respond",
        "icon": "tripadvisor",
        "features": ["reviews", "responses"],
        "auth_type": "api_key",
        "setup_url": "https://www.tripadvisor.com/Owners",
        "api_docs": "https://developer-tripadvisor.com/content-api/",
    },
    "booking_com": {
        "name": "Booking.com",
        "description": "Manage Booking.com guest reviews",
        "icon": "booking",
        "features": ["reviews", "responses", "messaging"],
        "auth_type": "api_key",
        "setup_url": "https://admin.booking.com",
        "api_docs": "https://connect.booking.com",
    },
}

# ---- Platform Status ----
@router.get("/tenants/{tenant_slug}/platforms")
async def list_platforms(tenant_slug: str, user=Depends(get_current_user)):
    """List all available platforms with connection status"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    result = []
    for platform_id, platform_info in PLATFORMS.items():
        cred = await db.platform_credentials.find_one(
            {"tenant_id": tid, "platform": platform_id}, {"_id": 0}
        )
        status = "disconnected"
        if cred:
            cred = serialize_doc(cred)
            status = cred.get("status", "disconnected")
        
        result.append({
            "id": platform_id,
            **platform_info,
            "status": status,
            "connected_at": cred.get("connected_at") if cred else None,
            "last_sync_at": cred.get("last_sync_at") if cred else None,
        })
    
    return result

@router.get("/tenants/{tenant_slug}/platforms/{platform_id}")
async def get_platform_detail(tenant_slug: str, platform_id: str, user=Depends(get_current_user)):
    """Get detailed platform status"""
    tenant = await resolve_tenant(tenant_slug)
    if platform_id not in PLATFORMS:
        raise HTTPException(status_code=404, detail="Platform not found")
    
    cred = await db.platform_credentials.find_one(
        {"tenant_id": tenant["id"], "platform": platform_id}, {"_id": 0}
    )
    
    # Count reviews from this platform
    source_map = {"google_business": "GOOGLE", "tripadvisor": "TRIPADVISOR", "booking_com": "BOOKING"}
    source = source_map.get(platform_id, platform_id.upper())
    review_count = await count_scoped("reviews", tenant["id"], {"source": source})
    
    return {
        "platform": PLATFORMS[platform_id],
        "status": serialize_doc(cred) if cred else {"status": "disconnected"},
        "review_count": review_count,
    }

# ---- Configure Platform ----
@router.post("/tenants/{tenant_slug}/platforms/{platform_id}/configure")
async def configure_platform(tenant_slug: str, platform_id: str, data: dict,
                              user=Depends(get_current_user)):
    """Configure platform credentials"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    if platform_id not in PLATFORMS:
        raise HTTPException(status_code=404, detail="Platform not found")
    
    platform = PLATFORMS[platform_id]
    
    cred_data = {
        "tenant_id": tid,
        "platform": platform_id,
        "status": "configured",
        "updated_at": now_utc().isoformat(),
    }
    
    if platform["auth_type"] == "api_key":
        cred_data["api_key"] = data.get("api_key", "")
        cred_data["api_secret"] = data.get("api_secret", "")
        cred_data["property_id"] = data.get("property_id", "")
        if cred_data["api_key"]:
            cred_data["status"] = "connected"
            cred_data["connected_at"] = now_utc().isoformat()
    elif platform["auth_type"] == "oauth2":
        cred_data["client_id"] = data.get("client_id", "")
        cred_data["client_secret"] = data.get("client_secret", "")
        cred_data["location_id"] = data.get("location_id", "")
        cred_data["account_id"] = data.get("account_id", "")
        if data.get("access_token"):
            cred_data["access_token"] = data["access_token"]
            cred_data["refresh_token"] = data.get("refresh_token", "")
            cred_data["status"] = "connected"
            cred_data["connected_at"] = now_utc().isoformat()
    
    existing = await db.platform_credentials.find_one({"tenant_id": tid, "platform": platform_id})
    if existing:
        await db.platform_credentials.update_one(
            {"tenant_id": tid, "platform": platform_id},
            {"$set": cred_data}
        )
    else:
        cred_data["id"] = new_id()
        cred_data["created_at"] = now_utc().isoformat()
        await db.platform_credentials.insert_one(cred_data)
    
    await log_audit(tid, f"platform_{platform_id}_configured", "platform", platform_id, user.get("id", ""))
    
    result = await db.platform_credentials.find_one({"tenant_id": tid, "platform": platform_id}, {"_id": 0})
    return serialize_doc(result)

# ---- Disconnect Platform ----
@router.post("/tenants/{tenant_slug}/platforms/{platform_id}/disconnect")
async def disconnect_platform(tenant_slug: str, platform_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    await db.platform_credentials.update_one(
        {"tenant_id": tenant["id"], "platform": platform_id},
        {"$set": {"status": "disconnected", "access_token": "", "api_key": "", "updated_at": now_utc().isoformat()}}
    )
    await log_audit(tenant["id"], f"platform_{platform_id}_disconnected", "platform", platform_id, user.get("id", ""))
    return {"ok": True, "status": "disconnected"}

# ---- Pull Reviews (Manual Sync) ----
@router.post("/tenants/{tenant_slug}/platforms/{platform_id}/sync")
async def sync_platform(tenant_slug: str, platform_id: str, user=Depends(get_current_user)):
    """Manually trigger a sync/pull from platform"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    cred = await db.platform_credentials.find_one(
        {"tenant_id": tid, "platform": platform_id}, {"_id": 0}
    )
    if not cred or serialize_doc(cred).get("status") != "connected":
        raise HTTPException(status_code=400, detail="Platform not connected")
    
    # Simulate pull - in real implementation, this would call the platform API
    source_map = {"google_business": "GOOGLE", "tripadvisor": "TRIPADVISOR", "booking_com": "BOOKING"}
    source = source_map.get(platform_id, platform_id.upper())
    
    # Update last sync time
    await db.platform_credentials.update_one(
        {"tenant_id": tid, "platform": platform_id},
        {"$set": {"last_sync_at": now_utc().isoformat()}}
    )
    
    review_count = await count_scoped("reviews", tid, {"source": source})
    
    return {
        "ok": True,
        "platform": platform_id,
        "reviews_synced": review_count,
        "last_sync_at": now_utc().isoformat(),
    }

# ---- Platform Reviews ----
@router.get("/tenants/{tenant_slug}/platforms/{platform_id}/reviews")
async def list_platform_reviews(tenant_slug: str, platform_id: str, 
                                 page: int = 1, limit: int = 50,
                                 user=Depends(get_current_user)):
    """List reviews from a specific platform"""
    tenant = await resolve_tenant(tenant_slug)
    source_map = {"google_business": "GOOGLE", "tripadvisor": "TRIPADVISOR", "booking_com": "BOOKING"}
    source = source_map.get(platform_id, platform_id.upper())
    
    skip = (page - 1) * limit
    reviews = await find_many_scoped("reviews", tenant["id"], {"source": source},
                                      sort=[("created_at", -1)], skip=skip, limit=limit)
    total = await count_scoped("reviews", tenant["id"], {"source": source})
    
    return {"data": reviews, "total": total, "page": page}

# ---- Email/SMS Notification Settings ----
@router.get("/tenants/{tenant_slug}/notification-settings")
async def get_notification_settings(tenant_slug: str, user=Depends(get_current_user)):
    """Get email/SMS notification settings"""
    tenant = await resolve_tenant(tenant_slug)
    settings = await db.email_sms_settings.find_one({"tenant_id": tenant["id"]}, {"_id": 0})
    if not settings:
        settings = {
            "email_enabled": False,
            "sms_enabled": False,
            "smtp_host": "",
            "smtp_port": 587,
            "smtp_user": "",
            "smtp_from": "",
            "sms_provider": "",
            "sms_from": "",
            "notify_on_request_received": True,
            "notify_on_request_updated": True,
            "notify_on_request_completed": True,
            "notify_on_spa_confirmed": True,
            "notify_on_transport_confirmed": True,
            "default_language": "tr",
        }
    return serialize_doc(settings) if isinstance(settings, dict) and "_id" in settings else settings

@router.put("/tenants/{tenant_slug}/notification-settings")
async def update_notification_settings(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    """Update email/SMS notification settings"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    settings = {
        "tenant_id": tid,
        "email_enabled": data.get("email_enabled", False),
        "sms_enabled": data.get("sms_enabled", False),
        "smtp_host": data.get("smtp_host", ""),
        "smtp_port": data.get("smtp_port", 587),
        "smtp_user": data.get("smtp_user", ""),
        "smtp_pass": data.get("smtp_pass", ""),
        "smtp_from": data.get("smtp_from", ""),
        "sms_provider": data.get("sms_provider", ""),
        "sms_api_key": data.get("sms_api_key", ""),
        "sms_api_secret": data.get("sms_api_secret", ""),
        "sms_from": data.get("sms_from", ""),
        "notify_on_request_received": data.get("notify_on_request_received", True),
        "notify_on_request_updated": data.get("notify_on_request_updated", True),
        "notify_on_request_completed": data.get("notify_on_request_completed", True),
        "notify_on_spa_confirmed": data.get("notify_on_spa_confirmed", True),
        "notify_on_transport_confirmed": data.get("notify_on_transport_confirmed", True),
        "default_language": data.get("default_language", "tr"),
        "updated_at": now_utc().isoformat(),
    }
    
    existing = await db.email_sms_settings.find_one({"tenant_id": tid})
    if existing:
        await db.email_sms_settings.update_one({"tenant_id": tid}, {"$set": settings})
    else:
        settings["id"] = new_id()
        settings["created_at"] = now_utc().isoformat()
        await db.email_sms_settings.insert_one(settings)
    
    result = await db.email_sms_settings.find_one({"tenant_id": tid}, {"_id": 0})
    return serialize_doc(result)

# ---- Notification Log ----
@router.get("/tenants/{tenant_slug}/notification-logs")
async def list_notification_logs(tenant_slug: str, page: int = 1, limit: int = 50,
                                  user=Depends(get_current_user)):
    """List email/SMS notification logs"""
    tenant = await resolve_tenant(tenant_slug)
    skip = (page - 1) * limit
    logs = await find_many_scoped("notification_logs", tenant["id"], {},
                                   sort=[("created_at", -1)], skip=skip, limit=limit)
    total = await count_scoped("notification_logs", tenant["id"])
    return {"data": logs, "total": total, "page": page}

# ---- Test Email/SMS ----
@router.post("/tenants/{tenant_slug}/test-email")
async def test_email(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    """Send test email"""
    from services.notification_engine import send_email
    to_email = data.get("to_email", user.get("email", ""))
    success = await send_email(to_email, "Test Email from OmniHub", "This is a test email. If you received this, email notifications are working!")
    return {"success": success, "to_email": to_email}

@router.post("/tenants/{tenant_slug}/test-sms")
async def test_sms(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    """Send test SMS"""
    from services.notification_engine import send_sms
    phone = data.get("phone", "")
    if not phone:
        raise HTTPException(status_code=400, detail="Phone number required")
    success = await send_sms(phone, "Test SMS from OmniHub. Notifications are working!")
    return {"success": success, "phone": phone}
