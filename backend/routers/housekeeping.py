"""Housekeeping Router - Room cleaning schedules, checklists, room status
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from core.config import db
from core.tenant_guard import (
    resolve_tenant, get_current_user, serialize_doc, new_id, now_utc,
    find_one_scoped, find_many_scoped, count_scoped,
    insert_scoped, update_scoped, delete_scoped, log_audit
)

router = APIRouter(prefix="/api/v2/housekeeping", tags=["housekeeping"])

# Room Status
@router.get("/tenants/{tenant_slug}/room-status")
async def get_room_status_board(tenant_slug: str, floor: Optional[str] = None,
                                 user=Depends(get_current_user)):
    """Get room status board (clean/dirty/inspecting/maintenance/occupied)"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    query = {}
    if floor:
        query["floor"] = floor
    
    rooms = await find_many_scoped("rooms", tid, query, sort=[("room_number", 1)], limit=500)
    
    # Get housekeeping status for each room
    for room in rooms:
        hk = await db.room_hk_status.find_one(
            {"tenant_id": tid, "room_id": room["id"]}, {"_id": 0}
        )
        room["hk_status"] = serialize_doc(hk) if hk else {
            "cleaning_status": "unknown",
            "last_cleaned_at": None,
            "last_cleaned_by": None,
            "last_inspected_at": None,
            "notes": "",
        }
    
    return rooms

@router.patch("/tenants/{tenant_slug}/rooms/{room_id}/hk-status")
async def update_room_hk_status(tenant_slug: str, room_id: str, data: dict,
                                 user=Depends(get_current_user)):
    """Update room housekeeping status"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    existing = await db.room_hk_status.find_one({"tenant_id": tid, "room_id": room_id})
    
    update_data = {
        "tenant_id": tid,
        "room_id": room_id,
        "cleaning_status": data.get("cleaning_status", "clean"),  # clean, dirty, in_progress, inspecting, maintenance
        "updated_at": now_utc().isoformat(),
    }
    
    if data.get("cleaning_status") == "clean":
        update_data["last_cleaned_at"] = now_utc().isoformat()
        update_data["last_cleaned_by"] = user.get("name", "")
    if data.get("cleaning_status") == "inspecting":
        update_data["last_inspected_at"] = now_utc().isoformat()
    if "notes" in data:
        update_data["notes"] = data["notes"]
    if "assigned_to" in data:
        update_data["assigned_to"] = data["assigned_to"]
    
    if existing:
        await db.room_hk_status.update_one(
            {"tenant_id": tid, "room_id": room_id},
            {"$set": update_data}
        )
    else:
        update_data["id"] = new_id()
        update_data["created_at"] = now_utc().isoformat()
        await db.room_hk_status.insert_one(update_data)
    
    result = await db.room_hk_status.find_one({"tenant_id": tid, "room_id": room_id}, {"_id": 0})
    return serialize_doc(result)

# Cleaning Checklists
@router.get("/tenants/{tenant_slug}/checklists")
async def list_checklists(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    return await find_many_scoped("hk_checklists", tenant["id"], sort=[("name", 1)])

@router.post("/tenants/{tenant_slug}/checklists")
async def create_checklist(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    return await insert_scoped("hk_checklists", tenant["id"], {
        "name": data.get("name", ""),
        "room_type": data.get("room_type", "all"),
        "items": data.get("items", []),  # [{"text": "Make bed", "required": True}]
        "active": True,
    })

@router.patch("/tenants/{tenant_slug}/checklists/{checklist_id}")
async def update_checklist(tenant_slug: str, checklist_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    update = {}
    if "name" in data:
        update["name"] = data["name"]
    if "items" in data:
        update["items"] = data["items"]
    if "room_type" in data:
        update["room_type"] = data["room_type"]
    if "active" in data:
        update["active"] = data["active"]
    return await update_scoped("hk_checklists", tenant["id"], checklist_id, update)

@router.delete("/tenants/{tenant_slug}/checklists/{checklist_id}")
async def delete_checklist(tenant_slug: str, checklist_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    await delete_scoped("hk_checklists", tenant["id"], checklist_id)
    return {"deleted": True}

# Cleaning Tasks (daily assignments)
@router.get("/tenants/{tenant_slug}/cleaning-tasks")
async def list_cleaning_tasks(tenant_slug: str, date: Optional[str] = None,
                              status: Optional[str] = None,
                              user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if date:
        query["date"] = date
    if status:
        query["status"] = status
    return await find_many_scoped("cleaning_tasks", tenant["id"], query,
                                   sort=[("room_number", 1)])

@router.post("/tenants/{tenant_slug}/cleaning-tasks")
async def create_cleaning_task(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    return await insert_scoped("cleaning_tasks", tenant["id"], {
        "room_id": data.get("room_id", ""),
        "room_number": data.get("room_number", ""),
        "date": data.get("date", now_utc().strftime("%Y-%m-%d")),
        "assigned_to": data.get("assigned_to", ""),
        "assigned_to_name": data.get("assigned_to_name", ""),
        "checklist_id": data.get("checklist_id", ""),
        "checklist_progress": [],  # [{"item": "Make bed", "done": False}]
        "status": "pending",  # pending, in_progress, completed, inspected
        "priority": data.get("priority", "normal"),
        "notes": data.get("notes", ""),
    })

@router.patch("/tenants/{tenant_slug}/cleaning-tasks/{task_id}")
async def update_cleaning_task(tenant_slug: str, task_id: str, data: dict,
                               user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    update = {}
    for key in ["status", "assigned_to", "assigned_to_name", "checklist_progress", "notes"]:
        if key in data:
            update[key] = data[key]
    if data.get("status") == "completed":
        update["completed_at"] = now_utc().isoformat()
        update["completed_by"] = user.get("name", "")
    return await update_scoped("cleaning_tasks", tenant["id"], task_id, update)

# Housekeeping Stats
@router.get("/tenants/{tenant_slug}/hk-stats")
async def get_hk_stats(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    total_rooms = await count_scoped("rooms", tid)
    
    # Count by hk status
    clean = await db.room_hk_status.count_documents({"tenant_id": tid, "cleaning_status": "clean"})
    dirty = await db.room_hk_status.count_documents({"tenant_id": tid, "cleaning_status": "dirty"})
    in_progress = await db.room_hk_status.count_documents({"tenant_id": tid, "cleaning_status": "in_progress"})
    inspecting = await db.room_hk_status.count_documents({"tenant_id": tid, "cleaning_status": "inspecting"})
    maintenance = await db.room_hk_status.count_documents({"tenant_id": tid, "cleaning_status": "maintenance"})
    
    today = now_utc().strftime("%Y-%m-%d")
    tasks_today = await count_scoped("cleaning_tasks", tid, {"date": today})
    tasks_completed = await count_scoped("cleaning_tasks", tid, {"date": today, "status": "completed"})
    
    return {
        "total_rooms": total_rooms,
        "clean": clean,
        "dirty": dirty,
        "in_progress": in_progress,
        "inspecting": inspecting,
        "maintenance": maintenance,
        "unknown": total_rooms - clean - dirty - in_progress - inspecting - maintenance,
        "tasks_today": tasks_today,
        "tasks_completed": tasks_completed,
    }
