"""Guest token resolve routes — extracted from server.py.
Endpoints: GET /api/guest/resolve-room, GET /api/guest/resolve-table, POST /api/guest/join-loyalty
Mounted under prefix=/api by include_router below.
"""
from fastapi import APIRouter, HTTPException, Request

from core.config import db
from core.legacy_helpers import (
    now_utc, new_id, serialize_doc,
    get_tenant_by_slug,
    upsert_contact as _upsert_contact,
)
from guest_system import create_guest_token, decode_guest_token
from security import rate_limiter

router = APIRouter(prefix="/api", tags=["guest-resolve"])


@router.get("/guest/resolve-room")
async def resolve_room(tenantSlug: str, roomCode: str, request: Request = None):
    """Resolve room by tenant slug + room code, issue guest token.
    Validates: room exists, is_active, QR version valid.
    Rate limited: max 10 resolves per IP per minute.
    """
    # Rate limit (Pilot Fix 4: guest spam protection)
    client_ip = request.client.host if request else "unknown"
    rate_key = f"guest_resolve:{client_ip}"
    if rate_limiter.is_rate_limited(rate_key, max_requests=10, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait.")
    
    tenant = await get_tenant_by_slug(tenantSlug)
    room = await db.rooms.find_one({"tenant_id": tenant["id"], "room_code": roomCode}, {"_id": 0})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found or QR code invalid")
    
    # Pilot Fix 3: QR version validation - inactive rooms reject
    room_doc = serialize_doc(room)
    if not room_doc.get("is_active", True):
        raise HTTPException(status_code=410, detail="This QR code has been deactivated")
    
    categories = await db.service_categories.find({"tenant_id": tenant["id"]}, {"_id": 0}).to_list(50)
    
    guest_token = create_guest_token(
        tenant_id=tenant["id"],
        room_id=room_doc["id"],
        room_code=roomCode
    )
    
    return {
        "guestToken": guest_token,
        "tenant": {"name": tenant["name"], "slug": tenant["slug"]},
        "room": room_doc,
        "serviceCategories": [serialize_doc(c) for c in categories],
        "loyaltyEnabled": tenant.get("loyalty_rules", {}).get("enabled", False)
    }

@router.get("/guest/resolve-table")
async def resolve_table(tenantSlug: str, tableCode: str, request: Request = None):
    """Resolve table with QR validation + rate limiting"""
    client_ip = request.client.host if request else "unknown"
    rate_key = f"guest_resolve:{client_ip}"
    if rate_limiter.is_rate_limited(rate_key, max_requests=10, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait.")
    
    tenant = await get_tenant_by_slug(tenantSlug)
    table = await db.tables.find_one({"tenant_id": tenant["id"], "table_code": tableCode}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Table not found or QR code invalid")
    
    table_doc = serialize_doc(table)
    if not table_doc.get("is_active", True):
        raise HTTPException(status_code=410, detail="This QR code has been deactivated")
    categories = await db.menu_categories.find({"tenant_id": tenant["id"]}, {"_id": 0}).sort("sort_order", 1).to_list(50)
    items = await db.menu_items.find({"tenant_id": tenant["id"], "available": True}, {"_id": 0}).to_list(500)
    
    guest_token = create_guest_token(
        tenant_id=tenant["id"],
        table_id=table_doc["id"],
        table_code=tableCode
    )
    
    return {
        "guestToken": guest_token,
        "tenant": {"name": tenant["name"], "slug": tenant["slug"]},
        "table": table_doc,
        "menuCategories": [serialize_doc(c) for c in categories],
        "menuItems": [serialize_doc(i) for i in items],
        "loyaltyEnabled": tenant.get("loyalty_rules", {}).get("enabled", False)
    }

@router.post("/guest/join-loyalty")
async def guest_join_loyalty(data: dict):
    """Guest joins loyalty via guest token"""
    guest_token = data.get("guestToken", "")
    try:
        payload = decode_guest_token(guest_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    
    tenant_id = payload["tenant_id"]
    phone = data.get("phone", "")
    email = data.get("email", "")
    name = data.get("name", "")
    
    if not phone and not email:
        raise HTTPException(status_code=400, detail="Phone or email required")
    
    contact = await _upsert_contact(tenant_id, name, phone, email)
    
    # Check existing loyalty
    existing = await db.loyalty_accounts.find_one({"tenant_id": tenant_id, "contact_id": contact["id"]})
    if existing:
        # Reissue token with contact_id
        new_token = create_guest_token(
            tenant_id=tenant_id,
            room_id=payload.get("room_id"),
            table_id=payload.get("table_id"),
            room_code=payload.get("room_code"),
            table_code=payload.get("table_code"),
            contact_id=contact["id"]
        )
        return {"guestToken": new_token, "loyalty": serialize_doc(existing), "otpStub": "123456"}
    
    account = {
        "id": new_id(),
        "tenant_id": tenant_id,
        "contact_id": contact["id"],
        "points": 0,
        "tier": "bronze",
        "created_at": now_utc().isoformat()
    }
    await db.loyalty_accounts.insert_one(account)
    await db.contacts.update_one({"id": contact["id"]}, {"$set": {"loyalty_account_id": account["id"]}})
    
    new_token = create_guest_token(
        tenant_id=tenant_id,
        room_id=payload.get("room_id"),
        table_id=payload.get("table_id"),
        room_code=payload.get("room_code"),
        table_code=payload.get("table_code"),
        contact_id=contact["id"]
    )
    return {"guestToken": new_token, "loyalty": serialize_doc(account), "otpStub": "123456"}
