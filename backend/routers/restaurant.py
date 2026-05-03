"""Restaurant V2 Router: Tables, Menu, Orders
Full tenant_guard isolation. Secure QR codes. Status validation.
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import Response
from typing import Optional

from core.config import db, PUBLIC_BASE_URL
from core.tenant_guard import (
    resolve_tenant, get_current_user, get_optional_user, serialize_doc,
    new_id, now_utc, generate_secure_code, find_one_scoped, find_many_scoped,
    count_scoped, insert_scoped, update_scoped, delete_scoped, log_audit
)
from guest_system import generate_qr_png, generate_qr_print_pdf

router = APIRouter(prefix="/api/v2/restaurant", tags=["restaurant"])

# Valid order status transitions (no going backward)
VALID_ORDER_TRANSITIONS = {
    "RECEIVED": ["PREPARING", "CANCELLED"],
    "PREPARING": ["SERVED", "CANCELLED"],
    "SERVED": ["COMPLETED"],
    "COMPLETED": [],
    "CANCELLED": [],
}

# ============ TABLES ============
@router.post("/tenants/{tenant_slug}/tables")
async def create_table_v2(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    current = await count_scoped("tables", tid)
    max_tables = tenant.get("plan_limits", {}).get("max_tables", 10)
    if current >= max_tables:
        raise HTTPException(status_code=403, detail=f"Table limit reached ({max_tables}). Upgrade your plan.")
    
    table_number = data.get("table_number", "")
    if not table_number:
        raise HTTPException(status_code=400, detail="Table number required")
    
    table_code = generate_secure_code("t", 12)
    table = await insert_scoped("tables", tid, {
        "table_number": table_number,
        "table_code": table_code,
        "capacity": data.get("capacity", 4),
        "section": data.get("section", ""),
        "is_active": True,
        "qr_version": 1,
        "qr_link": f"/g/{tenant_slug}/table/{table_code}",
    })
    
    await db.tenants.update_one({"id": tid}, {"$inc": {"usage_counters.tables": 1}})
    await log_audit(tid, "table_created", "table", table["id"], user.get("id", ""))
    return table

@router.get("/tenants/{tenant_slug}/tables")
async def list_tables_v2(tenant_slug: str):
    tenant = await resolve_tenant(tenant_slug)
    return await find_many_scoped("tables", tenant["id"], sort=[("table_number", 1)], limit=200)

@router.patch("/tenants/{tenant_slug}/tables/{table_id}")
async def update_table_v2(tenant_slug: str, table_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    allowed = ["table_number", "capacity", "section", "is_active"]
    update = {k: v for k, v in data.items() if k in allowed}
    if not update:
        raise HTTPException(status_code=400, detail="No valid fields")
    updated = await update_scoped("tables", tenant["id"], table_id, update)
    if not updated:
        raise HTTPException(status_code=404, detail="Table not found")
    await log_audit(tenant["id"], "table_updated", "table", table_id, user.get("id", ""))
    return updated

@router.delete("/tenants/{tenant_slug}/tables/{table_id}")
async def delete_table_v2(tenant_slug: str, table_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    deleted = await delete_scoped("tables", tenant["id"], table_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Table not found")
    await db.tenants.update_one({"id": tenant["id"]}, {"$inc": {"usage_counters.tables": -1}})
    await log_audit(tenant["id"], "table_deleted", "table", table_id, user.get("id", ""))
    return {"deleted": True}

@router.post("/tenants/{tenant_slug}/tables/{table_id}/regenerate-qr")
async def regenerate_table_qr(tenant_slug: str, table_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    table = await find_one_scoped("tables", tenant["id"], {"id": table_id})
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    new_code = generate_secure_code("t", 12)
    updated = await update_scoped("tables", tenant["id"], table_id, {
        "table_code": new_code,
        "qr_link": f"/g/{tenant_slug}/table/{new_code}",
        "qr_version": table.get("qr_version", 1) + 1,
    })
    await log_audit(tenant["id"], "table_qr_regenerated", "table", table_id, user.get("id", ""))
    return updated

@router.get("/tables/{table_id}/qr.png")
async def table_qr_png(table_id: str):
    table = await db.tables.find_one({"id": table_id}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    tenant = await db.tenants.find_one({"id": table["tenant_id"]}, {"_id": 0})
    qr_url = f"{PUBLIC_BASE_URL}/g/{tenant['slug']}/table/{table['table_code']}"
    png = generate_qr_png(qr_url)
    return Response(content=png, media_type="image/png",
                    headers={"Content-Disposition": f"inline; filename=table-{table['table_number']}-qr.png"})

@router.get("/tables/print.pdf")
async def tables_print_pdf(ids: str = ""):
    table_ids = [tid.strip() for tid in ids.split(",") if tid.strip()]
    if not table_ids:
        raise HTTPException(status_code=400, detail="No table IDs")
    tables = await db.tables.find({"id": {"$in": table_ids}}, {"_id": 0}).to_list(100)
    if not tables:
        raise HTTPException(status_code=404, detail="No tables found")
    tenant = await db.tenants.find_one({"id": tables[0]["tenant_id"]}, {"_id": 0})
    items = [{"label": f"Table {t['table_number']}", "url": f"{PUBLIC_BASE_URL}/g/{tenant['slug']}/table/{t['table_code']}"} for t in tables]
    pdf = generate_qr_print_pdf(items, f"{tenant['name']} - Table QR Codes")
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=table-qr-codes.pdf"})

# ============ MENU CATEGORIES ============
@router.post("/tenants/{tenant_slug}/menu/categories")
async def create_menu_category_v2(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    cat = await insert_scoped("menu_categories", tenant["id"], {
        "name": data.get("name", ""),
        "sort_order": data.get("sort_order", 0),
    })
    await log_audit(tenant["id"], "menu_category_created", "menu_category", cat["id"], user.get("id", ""))
    return cat

@router.get("/tenants/{tenant_slug}/menu/categories")
async def list_menu_categories_v2(tenant_slug: str):
    tenant = await resolve_tenant(tenant_slug)
    return await find_many_scoped("menu_categories", tenant["id"], sort=[("sort_order", 1)])

# ============ MENU ITEMS ============
@router.post("/tenants/{tenant_slug}/menu/items")
async def create_menu_item_v2(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    item = await insert_scoped("menu_items", tenant["id"], {
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "price": float(data.get("price", 0)),
        "category_id": data.get("category_id", ""),
        "image_url": data.get("image_url", ""),
        "available": data.get("available", True),
        "tags": data.get("tags", []),
    })
    await log_audit(tenant["id"], "menu_item_created", "menu_item", item["id"], user.get("id", ""))
    return item

@router.get("/tenants/{tenant_slug}/menu/items")
async def list_menu_items_v2(tenant_slug: str, category_id: Optional[str] = None):
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if category_id:
        query["category_id"] = category_id
    return await find_many_scoped("menu_items", tenant["id"], query, limit=500)

@router.patch("/tenants/{tenant_slug}/menu/items/{item_id}")
async def update_menu_item_v2(tenant_slug: str, item_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    allowed = ["name", "description", "price", "category_id", "available", "image_url", "tags"]
    update = {k: v for k, v in data.items() if k in allowed}
    if "price" in update:
        update["price"] = float(update["price"])
    updated = await update_scoped("menu_items", tenant["id"], item_id, update)
    if not updated:
        raise HTTPException(status_code=404, detail="Menu item not found")
    return updated

# ============ ORDERS ============
@router.post("/tenants/{tenant_slug}/orders")
async def create_order_v2(tenant_slug: str, data: dict):
    """Create order - works for both guest (via guestToken) and staff"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    table_code = data.get("table_code", "")
    table = await find_one_scoped("tables", tid, {"table_code": table_code}) if table_code else None
    
    items = data.get("items", [])
    
    # Validate menu items are available
    for item in items:
        menu_item = await find_one_scoped("menu_items", tid, {"id": item.get("menu_item_id", "")})
        if menu_item and not menu_item.get("available", True):
            raise HTTPException(status_code=400, detail=f"Item '{menu_item['name']}' is not available")
    
    total = sum(float(i.get("price", 0)) * int(i.get("quantity", 1)) for i in items)
    
    order = await insert_scoped("orders", tid, {
        "table_id": table["id"] if table else "",
        "table_code": table_code,
        "table_number": table["table_number"] if table else "",
        "items": items,
        "total": total,
        "status": "RECEIVED",
        "order_type": data.get("order_type", "dine_in"),
        "guest_name": data.get("guest_name", ""),
        "guest_phone": data.get("guest_phone", ""),
        "notes": data.get("notes", ""),
        "last_updated_by": data.get("updated_by", "guest"),
    })
    
    # Broadcast WebSocket
    try:
        from server import ws_manager
        await ws_manager.broadcast_tenant(tid, "order", "order", "created", order)
    except Exception:
        pass
    
    return order

@router.get("/tenants/{tenant_slug}/orders")
async def list_orders_v2(tenant_slug: str, status: Optional[str] = None, page: int = 1, limit: int = 50):
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if status:
        query["status"] = status.upper()
    skip = (page - 1) * limit
    data = await find_many_scoped("orders", tenant["id"], query,
                                   sort=[("created_at", -1)], skip=skip, limit=limit)
    total = await count_scoped("orders", tenant["id"], query)
    return {"data": data, "total": total, "page": page}

@router.get("/tenants/{tenant_slug}/orders/{order_id}")
async def get_order_v2(tenant_slug: str, order_id: str):
    tenant = await resolve_tenant(tenant_slug)
    order = await find_one_scoped("orders", tenant["id"], {"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.patch("/tenants/{tenant_slug}/orders/{order_id}/status")
async def update_order_status_v2(tenant_slug: str, order_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    order = await find_one_scoped("orders", tenant["id"], {"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    new_status = data.get("status", "").upper()
    current_status = order.get("status", "RECEIVED")
    
    # Validate status transition (no going backward)
    valid_next = VALID_ORDER_TRANSITIONS.get(current_status, [])
    if new_status not in valid_next:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid transition: {current_status} → {new_status}. Valid: {valid_next}"
        )
    
    updated = await update_scoped("orders", tenant["id"], order_id, {
        "status": new_status,
        "last_updated_by": user.get("name", "staff"),
        "last_updated_by_id": user.get("id", ""),
    })
    
    await log_audit(tenant["id"], "order_status_changed", "order", order_id, user.get("id", ""),
                    {"from": current_status, "to": new_status})
    
    # Broadcast
    try:
        from server import ws_manager
        await ws_manager.broadcast_tenant(tenant["id"], "order", "order", "updated", updated)
    except Exception:
        pass
    
    try:
        from routers.guest_services import notify_guest_status_change
        room_code = order.get("room_code", "")
        desc_parts = [f'{i.get("menu_item_name","")} x{i.get("quantity",1)}' for i in order.get("items", [])[:2]]
        desc = ", ".join(desc_parts)
        await notify_guest_status_change(tenant["id"], room_code, "room_service", new_status, desc)
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Guest notify error: {e}")
    
    return updated
