"""Shared legacy helpers extracted from server.py.
Provides ws_manager (WebSocket broadcast), tenant lookup, contact upsert,
loyalty point awarding, and the pydantic models used by legacy /api routes.
"""
from collections import defaultdict
from typing import Dict, List, Optional
import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, WebSocket
from pydantic import BaseModel

from core.config import db

logger = logging.getLogger("omnihub.legacy")


def now_utc():
    return datetime.now(timezone.utc)


def new_id():
    return str(uuid.uuid4())


def serialize_doc(doc):
    if doc is None:
        return None
    result = {}
    for key, value in doc.items():
        if key == "_id":
            result["_id"] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, list):
            result[key] = [serialize_doc(v) if isinstance(v, dict) else v for v in value]
        elif isinstance(value, dict):
            result[key] = serialize_doc(value)
        else:
            result[key] = value
    return result


class ConnectionManager:
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        self.connections[channel].append(websocket)
        logger.info(f"WS connected: {channel} (total: {len(self.connections[channel])})")

    def disconnect(self, websocket: WebSocket, channel: str):
        if websocket in self.connections[channel]:
            self.connections[channel].remove(websocket)

    async def broadcast(self, channel: str, message: dict):
        dead = []
        for ws in self.connections.get(channel, []):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, channel)

    async def broadcast_tenant(self, tenant_id: str, event_type: str, entity: str, action: str, payload: dict):
        channel = f"tenant:{tenant_id}"
        message = {
            "type": event_type,
            "tenant_id": tenant_id,
            "entity": entity,
            "action": action,
            "payload": payload,
            "ts": now_utc().isoformat(),
        }
        await self.broadcast(channel, message)


ws_manager = ConnectionManager()


async def get_tenant_by_slug(slug: str):
    tenant = await db.tenants.find_one({"slug": slug})
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant not found: {slug}")
    return serialize_doc(tenant)


async def get_tenant_by_id(tenant_id: str):
    tenant = await db.tenants.find_one({"id": tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return serialize_doc(tenant)


def normalize_phone(p: str) -> str:
    p = (p or "").strip().replace(" ", "").replace("-", "")
    if p.startswith("00"):
        p = "+" + p[2:]
    return p


async def upsert_contact(tenant_id: str, name: str = "", phone: str = "", email: str = ""):
    phone = normalize_phone(phone)
    email = (email or "").strip().lower()
    if not phone and not email:
        return None
    query = {"tenant_id": tenant_id}
    if phone:
        query["phone"] = phone
    elif email:
        query["email"] = email

    existing = await db.contacts.find_one(query)
    if existing:
        update = {"updated_at": now_utc().isoformat()}
        if name and not existing.get("name"):
            update["name"] = name
        if email and not existing.get("email"):
            update["email"] = email
        await db.contacts.update_one({"id": existing["id"]}, {"$set": update})
        return serialize_doc(existing)

    contact = {
        "id": new_id(),
        "tenant_id": tenant_id,
        "name": name or "",
        "phone": phone or "",
        "email": email or "",
        "tags": [],
        "notes": "",
        "consent_marketing": False,
        "consent_data": True,
        "loyalty_account_id": None,
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat(),
    }
    await db.contacts.insert_one(contact)
    return serialize_doc(contact)


async def award_loyalty_points(tenant: dict, event_type: str, event_data: dict):
    """Award loyalty points when request resolved or order served."""
    rules = tenant.get("loyalty_rules", {})
    if not rules.get("enabled", False):
        return

    phone = event_data.get("guest_phone", "")
    if not phone:
        return

    contact = await db.contacts.find_one({"tenant_id": tenant["id"], "phone": phone})
    if not contact or not contact.get("loyalty_account_id"):
        return

    points = 0
    if event_type == "request":
        points = rules.get("points_per_request", 10)
    elif event_type == "order":
        points = rules.get("points_per_order", 5)
        total = event_data.get("total", 0)
        points += int(total * rules.get("points_per_currency_unit", 1) / 100)

    if points > 0:
        entry = {
            "id": new_id(),
            "tenant_id": tenant["id"],
            "account_id": contact["loyalty_account_id"],
            "points": points,
            "type": "earn",
            "source": event_type,
            "description": f"Earned from {event_type}",
            "created_at": now_utc().isoformat(),
        }
        await db.loyalty_ledger.insert_one(entry)
        await db.loyalty_accounts.update_one(
            {"id": contact["loyalty_account_id"]},
            {"$inc": {"points": points}, "$set": {"updated_at": now_utc().isoformat()}},
        )
        # Outbound: notify Syroce PMS if integrated for this tenant
        try:
            from routers.syroce_integration import fire_syroce_event
            await fire_syroce_event(tenant["id"], "loyalty.points_awarded", {
                "guest_id": contact.get("id"),
                "guest_phone": phone,
                "points": points,
                "reason": event_type,
            })
        except Exception:
            pass


# ============ Pydantic models used by legacy routers ============
class RoomCreate(BaseModel):
    room_number: str
    room_type: Optional[str] = "standard"
    floor: Optional[str] = ""


class GuestRequestCreate(BaseModel):
    category: str
    description: str
    priority: Optional[str] = "normal"
    guest_name: Optional[str] = ""
    guest_phone: Optional[str] = ""
    guest_email: Optional[str] = ""


class GuestRequestUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None


class RequestRatingCreate(BaseModel):
    rating: int
    comment: Optional[str] = ""


class OrderItemInput(BaseModel):
    menu_item_id: str
    menu_item_name: str
    quantity: int = 1
    price: float
    notes: Optional[str] = ""


class OrderCreate(BaseModel):
    items: List[OrderItemInput]
    guest_name: Optional[str] = ""
    guest_phone: Optional[str] = ""
    guest_email: Optional[str] = ""
    notes: Optional[str] = ""
    order_type: str = "dine_in"


class OrderStatusUpdate(BaseModel):
    status: str
