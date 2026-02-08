"""CRM V2 Router: Contacts CRUD, Timeline, Merge, Export, Link
Full tenant_guard isolation. Audit logged. PII-safe.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import io, csv

from core.config import db
from core.tenant_guard import (
    resolve_tenant, get_current_user, serialize_doc,
    new_id, now_utc, find_one_scoped, find_many_scoped, count_scoped,
    insert_scoped, update_scoped, delete_scoped, log_audit
)

router = APIRouter(prefix="/api/v2/crm", tags=["crm"])


async def _emit_contact_event(tenant_id: str, contact_id: str, event_type: str,
                               title: str, body: str = "", ref_type: str = "", ref_id: str = ""):
    """Append a timeline event for a contact"""
    if not contact_id:
        return
    await db.contact_events.insert_one({
        "id": new_id(), "tenant_id": tenant_id, "contact_id": contact_id,
        "type": event_type, "title": title, "body": body,
        "ref_type": ref_type, "ref_id": ref_id,
        "created_at": now_utc().isoformat()
    })


# ============ CONTACTS CRUD ============
@router.get("/tenants/{tenant_slug}/contacts")
async def list_contacts(tenant_slug: str, q: Optional[str] = None, tag: Optional[str] = None,
                         page: int = 1, limit: int = 30, sort: str = "updated_at",
                         user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    query = {"merged_into_contact_id": {"$in": [None, ""]}}
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"phone": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}},
        ]
    if tag:
        query["tags"] = tag
    skip_val = (page - 1) * limit
    sort_field = sort if sort in ["name", "created_at", "updated_at", "last_seen_at"] else "updated_at"
    contacts = await find_many_scoped("contacts", tenant["id"], query,
                                       sort=[(sort_field, -1)], skip=skip_val, limit=limit)
    total = await count_scoped("contacts", tenant["id"], query)
    # Enrich with loyalty info
    for c in contacts:
        acct = await db.loyalty_accounts.find_one({"tenant_id": tenant["id"], "contact_id": c["id"]}, {"_id": 0})
        if acct:
            c["loyalty"] = {"points": acct.get("points_balance", 0), "tier": acct.get("tier_name", "Silver")}
    return {"data": contacts, "total": total, "page": page}


@router.post("/tenants/{tenant_slug}/contacts")
async def create_contact(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    phone = data.get("phone", "").strip()
    email = data.get("email", "").strip()
    if phone:
        existing = await db.contacts.find_one({"tenant_id": tenant["id"], "phone": phone})
        if existing:
            raise HTTPException(status_code=409, detail="Contact with this phone already exists")
    if email:
        existing = await db.contacts.find_one({"tenant_id": tenant["id"], "email": email})
        if existing:
            raise HTTPException(status_code=409, detail="Contact with this email already exists")
    contact = await insert_scoped("contacts", tenant["id"], {
        "name": data.get("name", ""), "phone": phone, "email": email,
        "tags": data.get("tags", []), "notes": data.get("notes", ""),
        "consent": data.get("consent", {"kvkk": True, "marketing": False}),
        "source_channels": data.get("source_channels", []),
        "last_seen_at": now_utc().isoformat(),
        "merged_into_contact_id": None,
        "last_updated_by": user.get("name", ""),
    })
    await log_audit(tenant["id"], "CRM_CONTACT_CREATED", "contact", contact["id"], user.get("id", ""))
    return contact


@router.get("/tenants/{tenant_slug}/contacts/{contact_id}")
async def get_contact_detail(tenant_slug: str, contact_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    contact = await find_one_scoped("contacts", tenant["id"], {"id": contact_id})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    # Compute summary
    tid = tenant["id"]
    total_messages = await count_scoped("messages", tid, {"conversation_id": {"$in":
        [c["id"] for c in await find_many_scoped("conversations", tid, {"contact_id": contact_id}, limit=100)]}})
    total_requests = 0
    total_orders = 0
    if contact.get("phone"):
        total_requests = await db.guest_requests.count_documents({"tenant_id": tid, "guest_phone": contact["phone"]})
        total_orders = await db.orders.count_documents({"tenant_id": tid, "guest_phone": contact["phone"]})
    total_convs = await count_scoped("conversations", tid, {"contact_id": contact_id})
    # Loyalty
    loyalty = None
    acct = await db.loyalty_accounts.find_one({"tenant_id": tid, "contact_id": contact_id}, {"_id": 0})
    if acct:
        loyalty = serialize_doc(acct)
    contact["summary"] = {
        "total_messages": total_messages, "total_requests": total_requests,
        "total_orders": total_orders, "total_conversations": total_convs,
    }
    contact["loyalty"] = loyalty
    return contact


@router.patch("/tenants/{tenant_slug}/contacts/{contact_id}")
async def update_contact(tenant_slug: str, contact_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    allowed = ["name", "phone", "email", "tags", "notes", "consent"]
    update = {k: v for k, v in data.items() if k in allowed}
    update["last_updated_by"] = user.get("name", "")
    updated = await update_scoped("contacts", tenant["id"], contact_id, update)
    if not updated:
        raise HTTPException(status_code=404, detail="Contact not found")
    await log_audit(tenant["id"], "CRM_CONTACT_UPDATED", "contact", contact_id, user.get("id", ""),
                    {"fields": list(update.keys())})
    return updated


@router.post("/tenants/{tenant_slug}/contacts/{contact_id}/note")
async def add_contact_note(tenant_slug: str, contact_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    contact = await find_one_scoped("contacts", tenant["id"], {"id": contact_id})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    note_text = data.get("note", data.get("text", "")).strip()
    if not note_text:
        raise HTTPException(status_code=400, detail="Note text required")
    # Append to notes
    current_notes = contact.get("notes", "")
    timestamp = now_utc().strftime("%Y-%m-%d %H:%M")
    new_notes = f"{current_notes}\n[{timestamp} - {user.get('name','')}] {note_text}".strip()
    await update_scoped("contacts", tenant["id"], contact_id, {"notes": new_notes})
    await _emit_contact_event(tenant["id"], contact_id, "NOTE_ADDED",
                               f"Note by {user.get('name','')}", note_text)
    await log_audit(tenant["id"], "CRM_NOTE_ADDED", "contact", contact_id, user.get("id", ""))
    return {"status": "ok"}


@router.get("/tenants/{tenant_slug}/contacts/{contact_id}/timeline")
async def get_contact_timeline(tenant_slug: str, contact_id: str, page: int = 1, limit: int = 30,
                                user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    skip_val = (page - 1) * limit
    events = await find_many_scoped("contact_events", tenant["id"],
                                     {"contact_id": contact_id},
                                     sort=[("created_at", -1)], skip=skip_val, limit=limit)
    total = await count_scoped("contact_events", tenant["id"], {"contact_id": contact_id})
    return {"data": events, "total": total, "page": page}


@router.post("/tenants/{tenant_slug}/contacts/merge")
async def merge_contacts(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    source_id = data.get("source_contact_id", "")
    target_id = data.get("target_contact_id", "")
    if not source_id or not target_id or source_id == target_id:
        raise HTTPException(status_code=400, detail="Two different contact IDs required")
    source = await find_one_scoped("contacts", tid, {"id": source_id})
    target = await find_one_scoped("contacts", tid, {"id": target_id})
    if not source or not target:
        raise HTTPException(status_code=404, detail="Contact not found")
    # Move references
    await db.conversations.update_many({"tenant_id": tid, "contact_id": source_id}, {"$set": {"contact_id": target_id}})
    if source.get("phone"):
        await db.guest_requests.update_many({"tenant_id": tid, "guest_phone": source["phone"]},
                                             {"$set": {"guest_phone": target.get("phone", source["phone"])}})
        await db.orders.update_many({"tenant_id": tid, "guest_phone": source["phone"]},
                                     {"$set": {"guest_phone": target.get("phone", source["phone"])}})
    await db.contact_events.update_many({"tenant_id": tid, "contact_id": source_id}, {"$set": {"contact_id": target_id}})
    # Merge loyalty
    source_acct = await db.loyalty_accounts.find_one({"tenant_id": tid, "contact_id": source_id})
    if source_acct:
        target_acct = await db.loyalty_accounts.find_one({"tenant_id": tid, "contact_id": target_id})
        if target_acct:
            await db.loyalty_accounts.update_one({"tenant_id": tid, "contact_id": target_id},
                {"$inc": {"points_balance": source_acct.get("points_balance", 0)}})
            await db.loyalty_accounts.delete_one({"tenant_id": tid, "contact_id": source_id})
        else:
            await db.loyalty_accounts.update_one({"tenant_id": tid, "contact_id": source_id},
                {"$set": {"contact_id": target_id}})
        await db.loyalty_ledger.update_many({"tenant_id": tid, "contact_id": source_id},
                                             {"$set": {"contact_id": target_id}})
    # Mark source
    await update_scoped("contacts", tid, source_id, {"merged_into_contact_id": target_id})
    await _emit_contact_event(tid, target_id, "CONTACT_MERGED",
                               f"Merged from {source.get('name','')}", ref_type="contact", ref_id=source_id)
    await log_audit(tid, "CRM_CONTACT_MERGED", "contact", target_id, user.get("id", ""),
                    {"source": source_id, "target": target_id})
    return {"status": "merged", "target_id": target_id}


@router.post("/tenants/{tenant_slug}/link")
async def link_contact_to_entity(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    entity_type = data.get("entity_type", "")
    entity_id = data.get("entity_id", "")
    contact_id = data.get("contact_id", "")
    if not all([entity_type, entity_id, contact_id]):
        raise HTTPException(status_code=400, detail="entity_type, entity_id, contact_id required")
    contact = await find_one_scoped("contacts", tid, {"id": contact_id})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    if entity_type == "conversation":
        await db.conversations.update_one({"id": entity_id, "tenant_id": tid}, {"$set": {"contact_id": contact_id}})
    elif entity_type == "request":
        await db.guest_requests.update_one({"id": entity_id, "tenant_id": tid},
            {"$set": {"contact_id": contact_id, "guest_phone": contact.get("phone", ""), "guest_name": contact.get("name", "")}})
    elif entity_type == "order":
        await db.orders.update_one({"id": entity_id, "tenant_id": tid},
            {"$set": {"contact_id": contact_id, "guest_phone": contact.get("phone", ""), "guest_name": contact.get("name", "")}})
    else:
        raise HTTPException(status_code=400, detail="entity_type must be conversation, request, or order")
    await _emit_contact_event(tid, contact_id, "CONTACT_LINKED",
                               f"Linked to {entity_type} #{entity_id[:8]}", ref_type=entity_type, ref_id=entity_id)
    await log_audit(tid, "CRM_CONTACT_LINKED", "contact", contact_id, user.get("id", ""),
                    {"entity_type": entity_type, "entity_id": entity_id})
    return {"status": "linked"}


@router.get("/tenants/{tenant_slug}/export/contacts.csv")
async def export_contacts_csv(tenant_slug: str, user=Depends(get_current_user)):
    # Admin only
    if user.get("role") not in ["owner", "admin"]:
        raise HTTPException(status_code=403, detail="Admin only")
    tenant = await resolve_tenant(tenant_slug)
    contacts = await find_many_scoped("contacts", tenant["id"],
                                       {"merged_into_contact_id": {"$in": [None, ""]}},
                                       sort=[("name", 1)], limit=5000)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["Name", "Phone", "Email", "Tags", "Points", "Tier", "Last Seen"])
    for c in contacts:
        acct = await db.loyalty_accounts.find_one({"tenant_id": tenant["id"], "contact_id": c["id"]}, {"_id": 0})
        pts = acct.get("points_balance", 0) if acct else ""
        tier = acct.get("tier_name", "") if acct else ""
        writer.writerow([c.get("name",""), c.get("phone",""), c.get("email",""),
                          ";".join(c.get("tags",[])), pts, tier, c.get("last_seen_at","")])
    buf.seek(0)
    await log_audit(tenant["id"], "CRM_CONTACTS_EXPORTED", "contacts", "", user.get("id", ""),
                    {"count": len(contacts)})
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                              headers={"Content-Disposition": "attachment; filename=contacts.csv"})


# ---- Helper for other routers to emit events ----
async def emit_contact_event(tenant_id, contact_id, event_type, title, body="", ref_type="", ref_id=""):
    await _emit_contact_event(tenant_id, contact_id, event_type, title, body, ref_type, ref_id)
