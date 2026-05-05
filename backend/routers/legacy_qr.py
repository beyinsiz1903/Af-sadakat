"""Legacy QR routes — extracted from server.py (T007 Faz 2).
Endpoints: /api/g/{slug}/room/info, /api/g/{slug}/table/info, /api/admin/rooms/{id}/qr.png, /api/admin/rooms/print.pdf
"""
import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from core.config import db
from core.legacy_helpers import (
    now_utc, serialize_doc, get_tenant_by_slug,
)
from guest_system import generate_qr_png, generate_qr_print_pdf

router = APIRouter(prefix="/api", tags=["legacy-qr"])


@router.get("/g/{tenant_slug}/room/{room_code}/info")
async def get_room_info(tenant_slug: str, room_code: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    room = await db.rooms.find_one({"tenant_id": tenant["id"], "room_code": room_code}, {"_id": 0})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    categories = await db.service_categories.find({"tenant_id": tenant["id"]}, {"_id": 0}).to_list(50)
    return {
        "tenant": {"name": tenant["name"], "slug": tenant["slug"]},
        "room": serialize_doc(room),
        "service_categories": [serialize_doc(c) for c in categories],
        "loyalty_enabled": tenant.get("loyalty_rules", {}).get("enabled", False),
        "current_guest_name": room.get("current_guest_name", ""),
        "current_guest_check_in": room.get("current_guest_check_in", ""),
        "current_guest_check_out": room.get("current_guest_check_out", ""),
    }

@router.get("/g/{tenant_slug}/table/{table_code}/info")
async def get_table_info(tenant_slug: str, table_code: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    table = await db.tables.find_one({"tenant_id": tenant["id"], "table_code": table_code}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    categories = await db.menu_categories.find({"tenant_id": tenant["id"]}, {"_id": 0}).sort("sort_order", 1).to_list(50)
    items = await db.menu_items.find({"tenant_id": tenant["id"], "available": True}, {"_id": 0}).to_list(500)
    return {
        "tenant": {"name": tenant["name"], "slug": tenant["slug"]},
        "table": serialize_doc(table),
        "menu_categories": [serialize_doc(c) for c in categories],
        "menu_items": [serialize_doc(i) for i in items],
        "loyalty_enabled": tenant.get("loyalty_rules", {}).get("enabled", False)
    }

@router.get("/admin/rooms/{room_id}/qr.png")
async def get_room_qr_png(room_id: str):
    """Generate QR PNG for a room"""
    room = await db.rooms.find_one({"id": room_id}, {"_id": 0})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    tenant = await db.tenants.find_one({"id": room["tenant_id"]}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    public_url = os.environ.get("PUBLIC_BASE_URL", "https://kritik-billing.preview.emergentagent.com")
    qr_url = f"{public_url}/g/{tenant['slug']}/room/{room['room_code']}"
    png_bytes = generate_qr_png(qr_url)
    
    return Response(content=png_bytes, media_type="image/png", 
                    headers={"Content-Disposition": f"inline; filename=room-{room['room_number']}-qr.png"})

@router.get("/admin/rooms/print.pdf")
async def get_rooms_print_pdf(ids: str = ""):
    """Generate printable PDF with QR codes for multiple rooms"""
    room_ids = [rid.strip() for rid in ids.split(",") if rid.strip()]
    if not room_ids:
        raise HTTPException(status_code=400, detail="No room IDs provided")
    
    rooms = await db.rooms.find({"id": {"$in": room_ids}}, {"_id": 0}).to_list(100)
    if not rooms:
        raise HTTPException(status_code=404, detail="No rooms found")
    
    tenant = await db.tenants.find_one({"id": rooms[0]["tenant_id"]}, {"_id": 0})
    public_url = os.environ.get("PUBLIC_BASE_URL", "https://kritik-billing.preview.emergentagent.com")
    
    items = [{
        "label": f"Room {r['room_number']}",
        "url": f"{public_url}/g/{tenant['slug']}/room/{r['room_code']}"
    } for r in rooms]
    
    pdf_bytes = generate_qr_print_pdf(items, title=f"{tenant['name']} - Room QR Codes")
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=room-qr-codes.pdf"})

