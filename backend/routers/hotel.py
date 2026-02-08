"""Hotel module router: Rooms, Guest Requests, QR codes
Demonstrates the modular router pattern for the refactored architecture.
Uses centralized tenant_guard for ALL queries.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import Response
from typing import Optional
import os

from core.config import db, PUBLIC_BASE_URL
from core.tenant_guard import (
    resolve_tenant, get_current_user, serialize_doc, new_id, now_utc,
    generate_secure_code, find_one_scoped, find_many_scoped, count_scoped,
    insert_scoped, update_scoped, delete_scoped, log_audit
)
from guest_system import generate_qr_png, generate_qr_print_pdf, create_guest_token

router = APIRouter(prefix="/api/v2/hotel", tags=["hotel"])

# ============ ROOMS (Admin) ============
@router.post("/tenants/{tenant_slug}/rooms")
async def create_room_v2(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    # Plan limit check
    current_rooms = await count_scoped("rooms", tid)
    max_rooms = tenant.get("plan_limits", {}).get("max_rooms", 20)
    if current_rooms >= max_rooms:
        raise HTTPException(status_code=403, detail=f"Room limit reached ({max_rooms}). Upgrade your plan.")
    
    room_number = data.get("room_number", "")
    if not room_number:
        raise HTTPException(status_code=400, detail="Room number required")
    
    # Generate SECURE room code (unguessable)
    room_code = generate_secure_code("r", 12)
    
    room = await insert_scoped("rooms", tid, {
        "room_number": room_number,
        "room_code": room_code,
        "room_type": data.get("room_type", "standard"),
        "floor": data.get("floor", ""),
        "is_active": True,
        "qr_version": 1,
        "qr_link": f"/g/{tenant_slug}/room/{room_code}",
        "status": "available",
    })
    
    await db.tenants.update_one({"id": tid}, {"$inc": {"usage_counters.rooms": 1}})
    await log_audit(tid, "room_created", "room", room["id"], user.get("id", ""), {"room_number": room_number})
    
    return room

@router.get("/tenants/{tenant_slug}/rooms")
async def list_rooms_v2(tenant_slug: str):
    tenant = await resolve_tenant(tenant_slug)
    return await find_many_scoped("rooms", tenant["id"], sort=[("room_number", 1)], limit=200)

@router.delete("/tenants/{tenant_slug}/rooms/{room_id}")
async def delete_room_v2(tenant_slug: str, room_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    deleted = await delete_scoped("rooms", tenant["id"], room_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Room not found")
    await db.tenants.update_one({"id": tenant["id"]}, {"$inc": {"usage_counters.rooms": -1}})
    await log_audit(tenant["id"], "room_deleted", "room", room_id, user.get("id", ""))
    return {"deleted": True}

@router.post("/tenants/{tenant_slug}/rooms/{room_id}/regenerate-qr")
async def regenerate_room_qr(tenant_slug: str, room_id: str, user=Depends(get_current_user)):
    """Regenerate QR code (invalidates old one)"""
    tenant = await resolve_tenant(tenant_slug)
    room = await find_one_scoped("rooms", tenant["id"], {"id": room_id})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    new_code = generate_secure_code("r", 12)
    updated = await update_scoped("rooms", tenant["id"], room_id, {
        "room_code": new_code,
        "qr_link": f"/g/{tenant_slug}/room/{new_code}",
        "qr_version": room.get("qr_version", 1) + 1,
    })
    await log_audit(tenant["id"], "room_qr_regenerated", "room", room_id, user.get("id", ""))
    return updated

# ============ QR CODE ENDPOINTS ============
@router.get("/rooms/{room_id}/qr.png")
async def room_qr_png(room_id: str):
    room = await db.rooms.find_one({"id": room_id}, {"_id": 0})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    tenant = await db.tenants.find_one({"id": room["tenant_id"]}, {"_id": 0})
    
    qr_url = f"{PUBLIC_BASE_URL}/g/{tenant['slug']}/room/{room['room_code']}"
    png = generate_qr_png(qr_url)
    return Response(content=png, media_type="image/png",
                    headers={"Content-Disposition": f"inline; filename=room-{room['room_number']}-qr.png"})

@router.get("/rooms/print.pdf")
async def rooms_print_pdf(ids: str = ""):
    room_ids = [rid.strip() for rid in ids.split(",") if rid.strip()]
    if not room_ids:
        raise HTTPException(status_code=400, detail="No room IDs")
    
    rooms = await db.rooms.find({"id": {"$in": room_ids}}, {"_id": 0}).to_list(100)
    if not rooms:
        raise HTTPException(status_code=404, detail="No rooms found")
    
    tenant = await db.tenants.find_one({"id": rooms[0]["tenant_id"]}, {"_id": 0})
    items = [{"label": f"Room {r['room_number']}", "url": f"{PUBLIC_BASE_URL}/g/{tenant['slug']}/room/{r['room_code']}"} for r in rooms]
    pdf = generate_qr_print_pdf(items, f"{tenant['name']} - Room QR Codes")
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=room-qr-codes.pdf"})

# ============ GUEST REQUEST ENDPOINTS ============
@router.get("/tenants/{tenant_slug}/requests")
async def list_requests_v2(tenant_slug: str, department: Optional[str] = None, 
                            status: Optional[str] = None, page: int = 1, limit: int = 50):
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if department:
        query["department_code"] = department.upper()
    if status:
        query["status"] = status.upper()
    
    skip = (page - 1) * limit
    data = await find_many_scoped("guest_requests", tenant["id"], query, 
                                   sort=[("created_at", -1)], skip=skip, limit=limit)
    total = await count_scoped("guest_requests", tenant["id"], query)
    return {"data": data, "total": total, "page": page}

@router.patch("/tenants/{tenant_slug}/requests/{request_id}")
async def update_request_v2(tenant_slug: str, request_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    req = await find_one_scoped("guest_requests", tenant["id"], {"id": request_id})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    update = {}
    if "status" in data:
        new_status = data["status"].upper()
        update["status"] = new_status
        if new_status == "IN_PROGRESS" and not req.get("first_response_at"):
            update["first_response_at"] = now_utc().isoformat()
        if new_status in ["DONE", "CLOSED"]:
            update["resolved_at"] = now_utc().isoformat()
    if "assigned_to" in data:
        update["assigned_to"] = data["assigned_to"]
    if "notes" in data:
        update["notes"] = data["notes"]
    
    updated = await update_scoped("guest_requests", tenant["id"], request_id, update)
    
    # Broadcast WebSocket event
    from server import ws_manager
    await ws_manager.broadcast_tenant(tenant["id"], "request", "guest_request", "updated", updated)
    
    return updated

# ============ REQUEST COMMENTS ============
@router.post("/tenants/{tenant_slug}/requests/{request_id}/comments")
async def add_comment_v2(tenant_slug: str, request_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    req = await find_one_scoped("guest_requests", tenant["id"], {"id": request_id})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    comment = await insert_scoped("request_comments", tenant["id"], {
        "request_id": request_id,
        "body": data.get("body", ""),
        "created_by_user_id": user.get("id", ""),
        "created_by_name": user.get("name", "Staff"),
    })
    return comment

@router.get("/tenants/{tenant_slug}/requests/{request_id}/comments")
async def list_comments_v2(tenant_slug: str, request_id: str):
    tenant = await resolve_tenant(tenant_slug)
    return await find_many_scoped("request_comments", tenant["id"], 
                                   {"request_id": request_id}, sort=[("created_at", 1)])
