"""Reservations V2 Router: List, detail, cancel, export.
Full tenant_guard isolation. Audit logged.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import io
import csv

from core.config import db
from core.tenant_guard import (
    resolve_tenant, get_current_user, serialize_doc,
    new_id, now_utc, find_one_scoped, find_many_scoped, count_scoped,
    update_scoped, log_audit
)

router = APIRouter(prefix="/api/v2/reservations", tags=["reservations"])


@router.get("/tenants/{tenant_slug}/reservations")
async def list_reservations(tenant_slug: str, propertyId: Optional[str] = None,
                            status: Optional[str] = None, q: Optional[str] = None,
                            page: int = 1, limit: int = 30, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if propertyId:
        query["property_id"] = propertyId
    if status:
        query["status"] = status.upper()
    if q:
        query["$or"] = [
            {"confirmation_code": {"$regex": q, "$options": "i"}},
            {"guest_name": {"$regex": q, "$options": "i"}},
        ]
    skip = (page - 1) * limit
    data = await find_many_scoped("reservations", tenant["id"], query,
                                   sort=[("created_at", -1)], skip=skip, limit=limit)
    total = await count_scoped("reservations", tenant["id"], query)
    return {"data": data, "total": total, "page": page}


@router.get("/tenants/{tenant_slug}/reservations/{reservation_id}")
async def get_reservation(tenant_slug: str, reservation_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    res = await find_one_scoped("reservations", tenant["id"], {"id": reservation_id})
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")
    # Enrich
    if res.get("offer_id"):
        res["offer"] = await find_one_scoped("offers", tenant["id"], {"id": res["offer_id"]})
    return res


@router.post("/tenants/{tenant_slug}/reservations/{reservation_id}/cancel")
async def cancel_reservation(tenant_slug: str, reservation_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)

    # Permission check
    if user.get("role") not in ["owner", "admin", "manager"]:
        raise HTTPException(status_code=403, detail="Only Admin/Manager can cancel reservations")

    res = await find_one_scoped("reservations", tenant["id"], {"id": reservation_id})
    if not res:
        raise HTTPException(status_code=404, detail="Reservation not found")
    if res["status"] == "CANCELLED":
        return res

    updated = await update_scoped("reservations", tenant["id"], reservation_id, {
        "status": "CANCELLED",
        "last_updated_by": user.get("name", ""),
    })

    await log_audit(tenant["id"], "RESERVATION_CANCELLED", "reservation", reservation_id,
                    user.get("id", ""), {"confirmation_code": res.get("confirmation_code", "")})

    # Emit contact event
    try:
        from routers.crm import emit_contact_event
        if res.get("contact_id"):
            await emit_contact_event(tenant["id"], res["contact_id"], "RESERVATION_CANCELLED",
                                      f"Reservation {res.get('confirmation_code', '')} cancelled",
                                      ref_type="reservation", ref_id=reservation_id)
    except Exception:
        pass

    return updated


@router.get("/tenants/{tenant_slug}/reservations/export/csv")
async def export_reservations_csv(tenant_slug: str, propertyId: Optional[str] = None,
                                   user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)

    # Admin only
    if user.get("role") not in ["owner", "admin", "manager"]:
        raise HTTPException(status_code=403, detail="Admin/Manager only")

    query = {}
    if propertyId:
        query["property_id"] = propertyId

    reservations = await find_many_scoped("reservations", tenant["id"], query,
                                           sort=[("created_at", -1)], limit=5000)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Confirmation Code", "Guest Name", "Room Type", "Check-in", "Check-out",
                     "Guests", "Total", "Currency", "Status", "Created At"])
    for r in reservations:
        writer.writerow([
            r.get("confirmation_code", ""),
            r.get("guest_name", ""),
            r.get("room_type", ""),
            r.get("check_in", ""),
            r.get("check_out", ""),
            r.get("guests_count", ""),
            r.get("price_total", ""),
            r.get("currency", ""),
            r.get("status", ""),
            r.get("created_at", ""),
        ])
    buf.seek(0)

    await log_audit(tenant["id"], "RESERVATIONS_EXPORTED", "reservations", "", user.get("id", ""),
                    {"count": len(reservations)})

    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                              headers={"Content-Disposition": "attachment; filename=reservations.csv"})
