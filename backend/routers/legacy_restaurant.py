"""Legacy restaurant routes — extracted from server.py (T007 Faz 2).
Endpoints under /api: tables, menu-categories, menu-items, /admin/tables/qr.png, /admin/tables/print.pdf.
NOTE: This is the LEGACY /api router. The newer /api/v2/restaurant router lives in routers/restaurant.py.
"""
import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional

from core.config import db
from core.legacy_helpers import (
    now_utc, new_id, serialize_doc, get_tenant_by_slug,
)
from guest_system import generate_qr_png, generate_qr_print_pdf

router = APIRouter(prefix="/api", tags=["legacy-restaurant"])


class TableCreate(BaseModel):
    table_number: str
    capacity: Optional[int] = 4
    section: Optional[str] = ""


class MenuCategoryCreate(BaseModel):
    name: str
    sort_order: Optional[int] = 0


class MenuItemCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    price: float
    category_id: str
    image_url: Optional[str] = ""
    available: bool = True


class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    category_id: Optional[str] = None
    image_url: Optional[str] = None
    available: Optional[bool] = None


@router.post("/tenants/{tenant_slug}/tables")
async def create_table(tenant_slug: str, data: TableCreate):
    tenant = await get_tenant_by_slug(tenant_slug)
    usage = tenant.get("usage_counters", {})
    limits = tenant.get("plan_limits", {})
    if usage.get("tables", 0) >= limits.get("max_tables", 10):
        raise HTTPException(status_code=403, detail="Table limit reached")
    
    table_code = f"T{data.table_number}"
    table = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "table_number": data.table_number,
        "table_code": table_code,
        "capacity": data.capacity,
        "section": data.section,
        "qr_link": f"/g/{tenant_slug}/table/{table_code}",
        "created_at": now_utc().isoformat()
    }
    await db.tables.insert_one(table)
    await db.tenants.update_one({"id": tenant["id"]}, {"$inc": {"usage_counters.tables": 1}})
    return serialize_doc(table)

@router.get("/tenants/{tenant_slug}/tables")
async def list_tables(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    tables = await db.tables.find({"tenant_id": tenant["id"]}, {"_id": 0}).to_list(200)
    return [serialize_doc(t) for t in tables]

@router.delete("/tenants/{tenant_slug}/tables/{table_id}")
async def delete_table(tenant_slug: str, table_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    result = await db.tables.delete_one({"id": table_id, "tenant_id": tenant["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Table not found")
    await db.tenants.update_one({"id": tenant["id"]}, {"$inc": {"usage_counters.tables": -1}})
    return {"deleted": True}

@router.post("/tenants/{tenant_slug}/menu-categories")
async def create_menu_category(tenant_slug: str, data: MenuCategoryCreate):
    tenant = await get_tenant_by_slug(tenant_slug)
    cat = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "name": data.name,
        "sort_order": data.sort_order,
        "created_at": now_utc().isoformat()
    }
    await db.menu_categories.insert_one(cat)
    return serialize_doc(cat)

@router.get("/tenants/{tenant_slug}/menu-categories")
async def list_menu_categories(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    cats = await db.menu_categories.find({"tenant_id": tenant["id"]}, {"_id": 0}).sort("sort_order", 1).to_list(100)
    return [serialize_doc(c) for c in cats]

@router.delete("/tenants/{tenant_slug}/menu-categories/{cat_id}")
async def delete_menu_category(tenant_slug: str, cat_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    await db.menu_categories.delete_one({"id": cat_id, "tenant_id": tenant["id"]})
    return {"deleted": True}

@router.post("/tenants/{tenant_slug}/menu-items")
async def create_menu_item(tenant_slug: str, data: MenuItemCreate):
    tenant = await get_tenant_by_slug(tenant_slug)
    item = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "name": data.name,
        "description": data.description,
        "price": data.price,
        "category_id": data.category_id,
        "image_url": data.image_url,
        "available": data.available,
        "created_at": now_utc().isoformat()
    }
    await db.menu_items.insert_one(item)
    return serialize_doc(item)

@router.get("/tenants/{tenant_slug}/menu-items")
async def list_menu_items(tenant_slug: str, category_id: Optional[str] = None):
    tenant = await get_tenant_by_slug(tenant_slug)
    query = {"tenant_id": tenant["id"]}
    if category_id:
        query["category_id"] = category_id
    items = await db.menu_items.find(query, {"_id": 0}).to_list(500)
    return [serialize_doc(i) for i in items]

@router.patch("/tenants/{tenant_slug}/menu-items/{item_id}")
async def update_menu_item(tenant_slug: str, item_id: str, data: MenuItemUpdate):
    tenant = await get_tenant_by_slug(tenant_slug)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    await db.menu_items.update_one({"id": item_id, "tenant_id": tenant["id"]}, {"$set": update_data})
    updated = await db.menu_items.find_one({"id": item_id}, {"_id": 0})
    return serialize_doc(updated)

@router.delete("/tenants/{tenant_slug}/menu-items/{item_id}")
async def delete_menu_item(tenant_slug: str, item_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    await db.menu_items.delete_one({"id": item_id, "tenant_id": tenant["id"]})
    return {"deleted": True}

@router.get("/admin/tables/{table_id}/qr.png")
async def get_table_qr_png(table_id: str):
    """Generate QR PNG for a table"""
    table = await db.tables.find_one({"id": table_id}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    tenant = await db.tenants.find_one({"id": table["tenant_id"]}, {"_id": 0})
    public_url = os.environ.get("PUBLIC_BASE_URL", "https://kritik-billing.preview.emergentagent.com")
    qr_url = f"{public_url}/g/{tenant['slug']}/table/{table['table_code']}"
    png_bytes = generate_qr_png(qr_url)
    
    return Response(content=png_bytes, media_type="image/png",
                    headers={"Content-Disposition": f"inline; filename=table-{table['table_number']}-qr.png"})

@router.get("/admin/tables/print.pdf")
async def get_tables_print_pdf(ids: str = ""):
    """Generate printable PDF with QR codes for multiple tables"""
    table_ids = [tid.strip() for tid in ids.split(",") if tid.strip()]
    if not table_ids:
        raise HTTPException(status_code=400, detail="No table IDs provided")
    
    tables = await db.tables.find({"id": {"$in": table_ids}}, {"_id": 0}).to_list(100)
    if not tables:
        raise HTTPException(status_code=404, detail="No tables found")
    
    tenant = await db.tenants.find_one({"id": tables[0]["tenant_id"]}, {"_id": 0})
    public_url = os.environ.get("PUBLIC_BASE_URL", "https://kritik-billing.preview.emergentagent.com")
    
    items = [{
        "label": f"Table {t['table_number']}",
        "url": f"{public_url}/g/{tenant['slug']}/table/{t['table_code']}"
    } for t in tables]
    
    pdf_bytes = generate_qr_print_pdf(items, title=f"{tenant['name']} - Table QR Codes")
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=table-qr-codes.pdf"})

