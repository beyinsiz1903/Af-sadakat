"""Legacy room routes - rooms CRUD plus guest requests bound to rooms."""
import os
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends

from core.config import db
from core.legacy_helpers import (
    ws_manager, get_tenant_by_slug, upsert_contact, award_loyalty_points,
    serialize_doc, new_id, now_utc,
    RoomCreate, GuestRequestCreate, GuestRequestUpdate, RequestRatingCreate,
)
from core.tenant_guard import get_optional_user

logger = logging.getLogger("omnihub.legacy.rooms")
router = APIRouter()

ROOT_DIR = Path(__file__).resolve().parent.parent


@router.post("/tenants/{tenant_slug}/rooms")
async def create_room(tenant_slug: str, data: RoomCreate):
    tenant = await get_tenant_by_slug(tenant_slug)
    usage = tenant.get("usage_counters", {})
    limits = tenant.get("plan_limits", {})
    if usage.get("rooms", 0) >= limits.get("max_rooms", 20):
        raise HTTPException(status_code=403, detail="Room limit reached")

    room_code = f"R{data.room_number}"
    room = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "room_number": data.room_number,
        "room_code": room_code,
        "room_type": data.room_type,
        "floor": data.floor,
        "qr_link": f"/g/{tenant_slug}/room/{room_code}",
        "status": "available",
        "created_at": now_utc().isoformat(),
    }
    await db.rooms.insert_one(room)
    await db.tenants.update_one({"id": tenant["id"]}, {"$inc": {"usage_counters.rooms": 1}})

    public_url = os.environ.get("PUBLIC_BASE_URL", "")
    qr_url = f"{public_url}/g/{tenant_slug}/room/{room_code}"
    try:
        from guest_system import generate_qr_png
        qr_bytes = generate_qr_png(qr_url)
        qr_filename = f"qr_room_{room['id']}.png"
        qr_path = ROOT_DIR / "uploads" / qr_filename
        qr_path.parent.mkdir(exist_ok=True)
        with open(qr_path, "wb") as f:
            f.write(qr_bytes)
        await db.rooms.update_one(
            {"id": room["id"]}, {"$set": {"qr_image": qr_filename, "qr_url": qr_url}}
        )
        room["qr_image"] = qr_filename
        room["qr_url"] = qr_url
    except Exception as e:
        logger.warning(f"QR auto-generation for room {room_code}: {e}")

    return serialize_doc(room)


@router.get("/tenants/{tenant_slug}/rooms")
async def list_rooms(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    rooms = await db.rooms.find({"tenant_id": tenant["id"]}, {"_id": 0}).to_list(200)
    return [serialize_doc(r) for r in rooms]


@router.delete("/tenants/{tenant_slug}/rooms/{room_id}")
async def delete_room(tenant_slug: str, room_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    result = await db.rooms.delete_one({"id": room_id, "tenant_id": tenant["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Room not found")
    await db.tenants.update_one({"id": tenant["id"]}, {"$inc": {"usage_counters.rooms": -1}})
    return {"deleted": True}


# ============ Guest requests (room-scoped) ============
@router.post("/g/{tenant_slug}/room/{room_code}/requests")
async def create_guest_request(tenant_slug: str, room_code: str, data: GuestRequestCreate):
    tenant = await get_tenant_by_slug(tenant_slug)
    room = await db.rooms.find_one({"tenant_id": tenant["id"], "room_code": room_code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    category_dept_map = {
        "housekeeping": "HK",
        "maintenance": "TECH",
        "room_service": "FB",
        "reception": "FRONTDESK",
        "other": "FRONTDESK",
    }
    dept_code = category_dept_map.get(data.category, "FRONTDESK")

    request_doc = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "room_id": serialize_doc(room)["id"],
        "room_code": room_code,
        "room_number": serialize_doc(room)["room_number"],
        "category": data.category,
        "department_code": dept_code,
        "description": data.description,
        "priority": data.priority,
        "status": "OPEN",
        "guest_name": data.guest_name,
        "guest_phone": data.guest_phone,
        "guest_email": data.guest_email,
        "assigned_to": None,
        "notes": "",
        "first_response_at": None,
        "resolved_at": None,
        "rating": None,
        "rating_comment": None,
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat(),
    }
    await db.guest_requests.insert_one(request_doc)

    if data.guest_phone or data.guest_email:
        await upsert_contact(tenant["id"], data.guest_name, data.guest_phone, data.guest_email)

    result = serialize_doc(request_doc)
    await ws_manager.broadcast_tenant(tenant["id"], "request", "guest_request", "created", result)
    return result


@router.get("/g/{tenant_slug}/room/{room_code}/requests")
async def list_guest_requests_by_room(tenant_slug: str, room_code: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    requests_list = await db.guest_requests.find(
        {"tenant_id": tenant["id"], "room_code": room_code}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return [serialize_doc(r) for r in requests_list]


@router.get("/tenants/{tenant_slug}/requests")
async def list_all_requests(
    tenant_slug: str,
    department: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
):
    tenant = await get_tenant_by_slug(tenant_slug)
    query = {"tenant_id": tenant["id"]}
    if department:
        query["department_code"] = department.upper()
    if status:
        query["status"] = status.upper()
    skip = (page - 1) * limit
    requests_list = (
        await db.guest_requests.find(query, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
        .to_list(limit)
    )
    total = await db.guest_requests.count_documents(query)
    return {"data": [serialize_doc(r) for r in requests_list], "total": total, "page": page}


@router.patch("/tenants/{tenant_slug}/requests/{request_id}")
async def update_guest_request(
    tenant_slug: str,
    request_id: str,
    data: GuestRequestUpdate,
    user=Depends(get_optional_user),
):
    tenant = await get_tenant_by_slug(tenant_slug)
    req = await db.guest_requests.find_one({"id": request_id, "tenant_id": tenant["id"]})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")

    update_data = {}
    if data.status:
        update_data["status"] = data.status.upper()
        if data.status.upper() == "IN_PROGRESS" and not req.get("first_response_at"):
            update_data["first_response_at"] = now_utc().isoformat()
        if data.status.upper() in ["DONE", "CLOSED"]:
            update_data["resolved_at"] = now_utc().isoformat()
            if data.status.upper() == "DONE":
                await award_loyalty_points(tenant, "request", req)
    if data.assigned_to is not None:
        update_data["assigned_to"] = data.assigned_to
    if data.notes is not None:
        update_data["notes"] = data.notes

    update_data["last_updated_by"] = user.get("name", "System") if user else "System"
    update_data["last_updated_by_id"] = user.get("id", "") if user else ""
    update_data["updated_at"] = now_utc().isoformat()
    await db.guest_requests.update_one({"id": request_id, "tenant_id": tenant["id"]}, {"$set": update_data})

    updated = await db.guest_requests.find_one({"id": request_id, "tenant_id": tenant["id"]}, {"_id": 0})
    result = serialize_doc(updated)
    await ws_manager.broadcast_tenant(tenant["id"], "request", "guest_request", "updated", result)
    return result


@router.post("/tenants/{tenant_slug}/requests/{request_id}/rate")
async def rate_request(tenant_slug: str, request_id: str, data: RequestRatingCreate):
    tenant = await get_tenant_by_slug(tenant_slug)
    req = await db.guest_requests.find_one({"id": request_id, "tenant_id": tenant["id"]})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if data.rating < 1 or data.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")

    await db.guest_requests.update_one(
        {"id": request_id, "tenant_id": tenant["id"]},
        {"$set": {"rating": data.rating, "rating_comment": data.comment, "updated_at": now_utc().isoformat()}},
    )
    updated = await db.guest_requests.find_one({"id": request_id, "tenant_id": tenant["id"]}, {"_id": 0})
    return serialize_doc(updated)
