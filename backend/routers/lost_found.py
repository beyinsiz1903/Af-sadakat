"""Lost & Found Router - Track lost and found items
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from core.config import db
from core.tenant_guard import (
    resolve_tenant, get_current_user, serialize_doc, new_id, now_utc,
    find_one_scoped, find_many_scoped, count_scoped,
    insert_scoped, update_scoped, delete_scoped, log_audit
)

router = APIRouter(prefix="/api/v2/lost-found", tags=["lost-found"])

@router.get("/tenants/{tenant_slug}/items")
async def list_lost_found(tenant_slug: str, status: Optional[str] = None,
                          item_type: Optional[str] = None,
                          page: int = 1, limit: int = 50,
                          user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if status:
        query["status"] = status
    if item_type:
        query["item_type"] = item_type
    skip = (page - 1) * limit
    items = await find_many_scoped("lost_found", tenant["id"], query,
                                    sort=[("created_at", -1)], skip=skip, limit=limit)
    total = await count_scoped("lost_found", tenant["id"], query)
    return {"data": items, "total": total, "page": page}

@router.post("/tenants/{tenant_slug}/items")
async def create_lost_found_item(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    item = await insert_scoped("lost_found", tenant["id"], {
        "item_type": data.get("item_type", "found"),  # lost, found
        "description": data.get("description", ""),
        "category": data.get("category", "other"),  # electronics, clothing, documents, jewelry, other
        "location_found": data.get("location_found", ""),
        "room_number": data.get("room_number", ""),
        "found_by": data.get("found_by", user.get("name", "")),
        "found_date": data.get("found_date", now_utc().strftime("%Y-%m-%d")),
        "guest_name": data.get("guest_name", ""),
        "guest_phone": data.get("guest_phone", ""),
        "guest_email": data.get("guest_email", ""),
        "status": "stored",  # stored, claimed, disposed, returned
        "storage_location": data.get("storage_location", ""),
        "notes": data.get("notes", ""),
        "image_url": data.get("image_url", ""),
    })
    await log_audit(tenant["id"], "lost_found_created", "lost_found", item["id"], user.get("id", ""))
    return item

@router.patch("/tenants/{tenant_slug}/items/{item_id}")
async def update_lost_found_item(tenant_slug: str, item_id: str, data: dict,
                                  user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    update = {}
    for key in ["status", "notes", "guest_name", "guest_phone", "guest_email",
                "storage_location", "claimed_by", "claimed_date"]:
        if key in data:
            update[key] = data[key]
    if data.get("status") == "returned":
        update["returned_at"] = now_utc().isoformat()
        update["returned_by"] = user.get("name", "")
    return await update_scoped("lost_found", tenant["id"], item_id, update)

@router.delete("/tenants/{tenant_slug}/items/{item_id}")
async def delete_lost_found_item(tenant_slug: str, item_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    await delete_scoped("lost_found", tenant["id"], item_id)
    return {"deleted": True}

@router.get("/tenants/{tenant_slug}/stats")
async def get_lost_found_stats(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    total = await count_scoped("lost_found", tid)
    stored = await count_scoped("lost_found", tid, {"status": "stored"})
    returned = await count_scoped("lost_found", tid, {"status": "returned"})
    claimed = await count_scoped("lost_found", tid, {"status": "claimed"})
    disposed = await count_scoped("lost_found", tid, {"status": "disposed"})
    
    return {
        "total": total,
        "stored": stored,
        "returned": returned,
        "claimed": claimed,
        "disposed": disposed,
    }
