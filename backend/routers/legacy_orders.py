"""Legacy order routes - guest-facing order creation plus tenant order listing/updates."""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from core.config import db
from core.legacy_helpers import (
    ws_manager, get_tenant_by_slug, upsert_contact, award_loyalty_points,
    serialize_doc, new_id, now_utc,
    OrderCreate, OrderStatusUpdate,
)

logger = logging.getLogger("omnihub.legacy.orders")
router = APIRouter()


@router.post("/g/{tenant_slug}/table/{table_code}/orders")
async def create_order(tenant_slug: str, table_code: str, data: OrderCreate):
    tenant = await get_tenant_by_slug(tenant_slug)
    table = await db.tables.find_one({"tenant_id": tenant["id"], "table_code": table_code})
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    total = sum(item.price * item.quantity for item in data.items)

    order = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "table_id": serialize_doc(table)["id"],
        "table_code": table_code,
        "table_number": serialize_doc(table)["table_number"],
        "items": [item.model_dump() for item in data.items],
        "total": total,
        "status": "RECEIVED",
        "order_type": data.order_type,
        "guest_name": data.guest_name,
        "guest_phone": data.guest_phone,
        "guest_email": data.guest_email,
        "notes": data.notes,
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat(),
    }
    await db.orders.insert_one(order)

    if data.guest_phone or data.guest_email:
        await upsert_contact(tenant["id"], data.guest_name, data.guest_phone, data.guest_email)

    result = serialize_doc(order)
    await ws_manager.broadcast_tenant(tenant["id"], "order", "order", "created", result)
    return result


@router.get("/g/{tenant_slug}/table/{table_code}/orders")
async def list_orders_by_table(tenant_slug: str, table_code: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    orders = await db.orders.find(
        {"tenant_id": tenant["id"], "table_code": table_code}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return [serialize_doc(o) for o in orders]


@router.get("/tenants/{tenant_slug}/orders")
async def list_all_orders(
    tenant_slug: str, status: Optional[str] = None, page: int = 1, limit: int = 50
):
    tenant = await get_tenant_by_slug(tenant_slug)
    query = {"tenant_id": tenant["id"]}
    if status:
        query["status"] = status.upper()
    skip = (page - 1) * limit
    orders = (
        await db.orders.find(query, {"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
        .to_list(limit)
    )
    total = await db.orders.count_documents(query)
    return {"data": [serialize_doc(o) for o in orders], "total": total, "page": page}


@router.patch("/tenants/{tenant_slug}/orders/{order_id}")
async def update_order_status(tenant_slug: str, order_id: str, data: OrderStatusUpdate):
    tenant = await get_tenant_by_slug(tenant_slug)
    order = await db.orders.find_one({"id": order_id, "tenant_id": tenant["id"]})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    update = {"status": data.status.upper(), "updated_at": now_utc().isoformat()}
    await db.orders.update_one({"id": order_id}, {"$set": update})

    if data.status.upper() == "SERVED":
        await award_loyalty_points(tenant, "order", serialize_doc(order))

    updated = await db.orders.find_one({"id": order_id}, {"_id": 0})
    result = serialize_doc(updated)
    await ws_manager.broadcast_tenant(tenant["id"], "order", "order", "updated", result)
    return result
