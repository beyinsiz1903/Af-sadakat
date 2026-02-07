from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
from collections import defaultdict
import asyncio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'omni_inbox_hub')]

# Create the main app
app = FastAPI(title="Omni Inbox Hub API", version="0.1.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ============ HELPERS ============
def serialize_doc(doc):
    """Convert MongoDB document to JSON-safe dict"""
    if doc is None:
        return None
    result = {}
    for key, value in doc.items():
        if key == '_id':
            result['_id'] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, list):
            result[key] = [serialize_doc(v) if isinstance(v, dict) else v for v in value]
        elif isinstance(value, dict):
            result[key] = serialize_doc(value)
        else:
            result[key] = value
    return result

def now_utc():
    return datetime.now(timezone.utc)

def new_id():
    return str(uuid.uuid4())

# ============ WEBSOCKET MANAGER ============
class ConnectionManager:
    """Manages WebSocket connections per tenant channel"""
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = defaultdict(list)
    
    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        self.connections[channel].append(websocket)
        logger.info(f"WS connected to channel: {channel} (total: {len(self.connections[channel])})")
    
    def disconnect(self, websocket: WebSocket, channel: str):
        if websocket in self.connections[channel]:
            self.connections[channel].remove(websocket)
        logger.info(f"WS disconnected from channel: {channel} (remaining: {len(self.connections[channel])})")
    
    async def broadcast(self, channel: str, message: dict):
        """Broadcast message to all connections on a channel"""
        dead = []
        for ws in self.connections.get(channel, []):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, channel)
    
    async def broadcast_tenant(self, tenant_id: str, event_type: str, entity: str, action: str, payload: dict):
        """Broadcast a tenant-scoped event"""
        channel = f"tenant:{tenant_id}"
        message = {
            "type": event_type,
            "tenant_id": tenant_id,
            "entity": entity,
            "action": action,
            "payload": payload,
            "ts": now_utc().isoformat()
        }
        await self.broadcast(channel, message)

ws_manager = ConnectionManager()

# ============ PYDANTIC MODELS ============

# --- Tenant ---
class TenantCreate(BaseModel):
    name: str
    slug: str
    business_type: str = "hotel"  # hotel, restaurant, agency, clinic
    plan: str = "basic"  # basic, pro

class TenantUpdate(BaseModel):
    name: Optional[str] = None
    hotel_enabled: Optional[bool] = None
    restaurant_enabled: Optional[bool] = None
    agency_enabled: Optional[bool] = None
    clinic_enabled: Optional[bool] = None

# --- Department ---
class DepartmentCreate(BaseModel):
    name: str
    code: str  # HK, TECH, FB, FRONTDESK
    description: Optional[str] = ""

# --- Service Category ---
class ServiceCategoryCreate(BaseModel):
    name: str
    department_code: str
    icon: Optional[str] = ""

# --- Room ---
class RoomCreate(BaseModel):
    room_number: str
    room_type: Optional[str] = "standard"
    floor: Optional[str] = ""

# --- Guest Request ---
class GuestRequestCreate(BaseModel):
    category: str  # housekeeping, maintenance, room_service, reception, other
    description: str
    priority: Optional[str] = "normal"  # low, normal, high, urgent
    guest_name: Optional[str] = ""
    guest_phone: Optional[str] = ""
    guest_email: Optional[str] = ""

class GuestRequestUpdate(BaseModel):
    status: Optional[str] = None  # OPEN, IN_PROGRESS, DONE, CLOSED
    assigned_to: Optional[str] = None
    notes: Optional[str] = None

class RequestRatingCreate(BaseModel):
    rating: int  # 1-5
    comment: Optional[str] = ""

# --- Table ---
class TableCreate(BaseModel):
    table_number: str
    capacity: Optional[int] = 4
    section: Optional[str] = ""

# --- Menu ---
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

# --- Order ---
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
    order_type: str = "dine_in"  # dine_in, call_waiter, request_bill

class OrderStatusUpdate(BaseModel):
    status: str  # RECEIVED, PREPARING, SERVED, COMPLETED, CANCELLED

# ============ TENANT ISOLATION MIDDLEWARE ============
async def get_tenant_by_slug(slug: str):
    """Resolve tenant by slug - core isolation function"""
    tenant = await db.tenants.find_one({"slug": slug})
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant not found: {slug}")
    return serialize_doc(tenant)

async def get_tenant_by_id(tenant_id: str):
    tenant = await db.tenants.find_one({"id": tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant not found")
    return serialize_doc(tenant)

# ============ API ROUTES ============

# --- Health ---
@api_router.get("/")
async def root():
    return {"message": "Omni Inbox Hub API", "version": "0.1.0"}

@api_router.get("/health")
async def health():
    return {"status": "ok", "timestamp": now_utc().isoformat()}

# ============ TENANT ROUTES ============
@api_router.post("/tenants")
async def create_tenant(data: TenantCreate):
    existing = await db.tenants.find_one({"slug": data.slug})
    if existing:
        raise HTTPException(status_code=400, detail="Tenant slug already exists")
    
    tenant = {
        "id": new_id(),
        "name": data.name,
        "slug": data.slug,
        "business_type": data.business_type,
        "plan": data.plan,
        "hotel_enabled": data.business_type in ["hotel"],
        "restaurant_enabled": data.business_type in ["restaurant", "hotel"],
        "agency_enabled": False,
        "clinic_enabled": False,
        "plan_limits": {
            "max_users": 5 if data.plan == "basic" else 25,
            "max_rooms": 20 if data.plan == "basic" else 100,
            "max_tables": 10 if data.plan == "basic" else 50,
            "monthly_ai_replies": 50 if data.plan == "basic" else 500,
        },
        "usage_counters": {
            "users": 1,
            "rooms": 0,
            "tables": 0,
            "ai_replies_this_month": 0
        },
        "loyalty_rules": {
            "enabled": False,
            "points_per_request": 10,
            "points_per_order": 5,
            "points_per_currency_unit": 1
        },
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat()
    }
    await db.tenants.insert_one(tenant)
    return serialize_doc(tenant)

@api_router.get("/tenants")
async def list_tenants():
    tenants = await db.tenants.find({}, {"_id": 0}).to_list(100)
    return [serialize_doc(t) for t in tenants]

@api_router.get("/tenants/{tenant_slug}")
async def get_tenant(tenant_slug: str):
    return await get_tenant_by_slug(tenant_slug)

@api_router.patch("/tenants/{tenant_slug}")
async def update_tenant(tenant_slug: str, data: TenantUpdate):
    tenant = await get_tenant_by_slug(tenant_slug)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now_utc().isoformat()
    await db.tenants.update_one({"id": tenant["id"]}, {"$set": update_data})
    updated = await db.tenants.find_one({"id": tenant["id"]}, {"_id": 0})
    return serialize_doc(updated)

# ============ DEPARTMENT ROUTES ============
@api_router.post("/tenants/{tenant_slug}/departments")
async def create_department(tenant_slug: str, data: DepartmentCreate):
    tenant = await get_tenant_by_slug(tenant_slug)
    dept = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "name": data.name,
        "code": data.code.upper(),
        "description": data.description,
        "created_at": now_utc().isoformat()
    }
    await db.departments.insert_one(dept)
    return serialize_doc(dept)

@api_router.get("/tenants/{tenant_slug}/departments")
async def list_departments(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    depts = await db.departments.find({"tenant_id": tenant["id"]}, {"_id": 0}).to_list(100)
    return [serialize_doc(d) for d in depts]

# ============ SERVICE CATEGORY ROUTES ============
@api_router.post("/tenants/{tenant_slug}/service-categories")
async def create_service_category(tenant_slug: str, data: ServiceCategoryCreate):
    tenant = await get_tenant_by_slug(tenant_slug)
    cat = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "name": data.name,
        "department_code": data.department_code.upper(),
        "icon": data.icon,
        "created_at": now_utc().isoformat()
    }
    await db.service_categories.insert_one(cat)
    return serialize_doc(cat)

@api_router.get("/tenants/{tenant_slug}/service-categories")
async def list_service_categories(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    cats = await db.service_categories.find({"tenant_id": tenant["id"]}, {"_id": 0}).to_list(100)
    return [serialize_doc(c) for c in cats]

# ============ ROOM ROUTES ============
@api_router.post("/tenants/{tenant_slug}/rooms")
async def create_room(tenant_slug: str, data: RoomCreate):
    tenant = await get_tenant_by_slug(tenant_slug)
    # Check plan limit
    usage = tenant.get("usage_counters", {})
    limits = tenant.get("plan_limits", {})
    if usage.get("rooms", 0) >= limits.get("max_rooms", 20):
        raise HTTPException(status_code=403, detail="Room limit reached for your plan")
    
    room_code = f"R{data.room_number}"
    room = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "room_number": data.room_number,
        "room_code": room_code,
        "room_type": data.room_type,
        "floor": data.floor,
        "qr_link": f"/g/{tenant_slug}/room/{room_code}",
        "created_at": now_utc().isoformat()
    }
    await db.rooms.insert_one(room)
    await db.tenants.update_one({"id": tenant["id"]}, {"$inc": {"usage_counters.rooms": 1}})
    return serialize_doc(room)

@api_router.get("/tenants/{tenant_slug}/rooms")
async def list_rooms(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    rooms = await db.rooms.find({"tenant_id": tenant["id"]}, {"_id": 0}).to_list(200)
    return [serialize_doc(r) for r in rooms]

# ============ GUEST REQUEST ROUTES (Hotel QR) ============
@api_router.post("/g/{tenant_slug}/room/{room_code}/requests")
async def create_guest_request(tenant_slug: str, room_code: str, data: GuestRequestCreate):
    tenant = await get_tenant_by_slug(tenant_slug)
    room = await db.rooms.find_one({"tenant_id": tenant["id"], "room_code": room_code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    # Map category to department
    category_dept_map = {
        "housekeeping": "HK",
        "maintenance": "TECH",
        "room_service": "FB",
        "reception": "FRONTDESK",
        "other": "FRONTDESK"
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
        "updated_at": now_utc().isoformat()
    }
    await db.guest_requests.insert_one(request_doc)
    
    # Link to contact if phone/email provided
    if data.guest_phone or data.guest_email:
        await _upsert_contact(tenant["id"], data.guest_name, data.guest_phone, data.guest_email)
    
    result = serialize_doc(request_doc)
    
    # Broadcast via WebSocket
    await ws_manager.broadcast_tenant(tenant["id"], "request", "guest_request", "created", result)
    
    return result

@api_router.get("/g/{tenant_slug}/room/{room_code}/requests")
async def list_guest_requests_by_room(tenant_slug: str, room_code: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    requests = await db.guest_requests.find(
        {"tenant_id": tenant["id"], "room_code": room_code}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return [serialize_doc(r) for r in requests]

@api_router.get("/tenants/{tenant_slug}/requests")
async def list_all_requests(tenant_slug: str, department: Optional[str] = None, status: Optional[str] = None):
    tenant = await get_tenant_by_slug(tenant_slug)
    query = {"tenant_id": tenant["id"]}
    if department:
        query["department_code"] = department.upper()
    if status:
        query["status"] = status.upper()
    requests = await db.guest_requests.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [serialize_doc(r) for r in requests]

@api_router.patch("/tenants/{tenant_slug}/requests/{request_id}")
async def update_guest_request(tenant_slug: str, request_id: str, data: GuestRequestUpdate):
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
    if data.assigned_to is not None:
        update_data["assigned_to"] = data.assigned_to
    if data.notes is not None:
        update_data["notes"] = data.notes
    
    update_data["updated_at"] = now_utc().isoformat()
    await db.guest_requests.update_one({"id": request_id}, {"$set": update_data})
    
    updated = await db.guest_requests.find_one({"id": request_id}, {"_id": 0})
    result = serialize_doc(updated)
    
    # Broadcast update
    await ws_manager.broadcast_tenant(tenant["id"], "request", "guest_request", "updated", result)
    
    return result

@api_router.post("/tenants/{tenant_slug}/requests/{request_id}/rate")
async def rate_request(tenant_slug: str, request_id: str, data: RequestRatingCreate):
    tenant = await get_tenant_by_slug(tenant_slug)
    req = await db.guest_requests.find_one({"id": request_id, "tenant_id": tenant["id"]})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    if data.rating < 1 or data.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be 1-5")
    
    await db.guest_requests.update_one({"id": request_id}, {"$set": {
        "rating": data.rating,
        "rating_comment": data.comment,
        "updated_at": now_utc().isoformat()
    }})
    updated = await db.guest_requests.find_one({"id": request_id}, {"_id": 0})
    return serialize_doc(updated)

# ============ TABLE ROUTES (Restaurant) ============
@api_router.post("/tenants/{tenant_slug}/tables")
async def create_table(tenant_slug: str, data: TableCreate):
    tenant = await get_tenant_by_slug(tenant_slug)
    usage = tenant.get("usage_counters", {})
    limits = tenant.get("plan_limits", {})
    if usage.get("tables", 0) >= limits.get("max_tables", 10):
        raise HTTPException(status_code=403, detail="Table limit reached for your plan")
    
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

@api_router.get("/tenants/{tenant_slug}/tables")
async def list_tables(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    tables = await db.tables.find({"tenant_id": tenant["id"]}, {"_id": 0}).to_list(200)
    return [serialize_doc(t) for t in tables]

# ============ MENU ROUTES ============
@api_router.post("/tenants/{tenant_slug}/menu-categories")
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

@api_router.get("/tenants/{tenant_slug}/menu-categories")
async def list_menu_categories(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    cats = await db.menu_categories.find({"tenant_id": tenant["id"]}, {"_id": 0}).sort("sort_order", 1).to_list(100)
    return [serialize_doc(c) for c in cats]

@api_router.post("/tenants/{tenant_slug}/menu-items")
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

@api_router.get("/tenants/{tenant_slug}/menu-items")
async def list_menu_items(tenant_slug: str, category_id: Optional[str] = None):
    tenant = await get_tenant_by_slug(tenant_slug)
    query = {"tenant_id": tenant["id"]}
    if category_id:
        query["category_id"] = category_id
    items = await db.menu_items.find(query, {"_id": 0}).to_list(500)
    return [serialize_doc(i) for i in items]

# ============ ORDER ROUTES (Restaurant QR) ============
@api_router.post("/g/{tenant_slug}/table/{table_code}/orders")
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
        "updated_at": now_utc().isoformat()
    }
    await db.orders.insert_one(order)
    
    # Link to contact
    if data.guest_phone or data.guest_email:
        await _upsert_contact(tenant["id"], data.guest_name, data.guest_phone, data.guest_email)
    
    result = serialize_doc(order)
    
    # Broadcast via WebSocket
    await ws_manager.broadcast_tenant(tenant["id"], "order", "order", "created", result)
    
    return result

@api_router.get("/g/{tenant_slug}/table/{table_code}/orders")
async def list_orders_by_table(tenant_slug: str, table_code: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    orders = await db.orders.find(
        {"tenant_id": tenant["id"], "table_code": table_code}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return [serialize_doc(o) for o in orders]

@api_router.get("/tenants/{tenant_slug}/orders")
async def list_all_orders(tenant_slug: str, status: Optional[str] = None):
    tenant = await get_tenant_by_slug(tenant_slug)
    query = {"tenant_id": tenant["id"]}
    if status:
        query["status"] = status.upper()
    orders = await db.orders.find(query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [serialize_doc(o) for o in orders]

@api_router.patch("/tenants/{tenant_slug}/orders/{order_id}")
async def update_order_status(tenant_slug: str, order_id: str, data: OrderStatusUpdate):
    tenant = await get_tenant_by_slug(tenant_slug)
    order = await db.orders.find_one({"id": order_id, "tenant_id": tenant["id"]})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    await db.orders.update_one({"id": order_id}, {"$set": {
        "status": data.status.upper(),
        "updated_at": now_utc().isoformat()
    }})
    
    updated = await db.orders.find_one({"id": order_id}, {"_id": 0})
    result = serialize_doc(updated)
    
    # Broadcast update
    await ws_manager.broadcast_tenant(tenant["id"], "order", "order", "updated", result)
    
    return result

# ============ CONTACT / CRM ROUTES ============
async def _upsert_contact(tenant_id: str, name: str = "", phone: str = "", email: str = ""):
    """Create or update contact by phone/email"""
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
        "updated_at": now_utc().isoformat()
    }
    await db.contacts.insert_one(contact)
    return serialize_doc(contact)

@api_router.get("/tenants/{tenant_slug}/contacts")
async def list_contacts(tenant_slug: str, page: int = 1, limit: int = 20):
    tenant = await get_tenant_by_slug(tenant_slug)
    skip = (page - 1) * limit
    contacts = await db.contacts.find(
        {"tenant_id": tenant["id"]}, {"_id": 0}
    ).sort("updated_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.contacts.count_documents({"tenant_id": tenant["id"]})
    return {"data": [serialize_doc(c) for c in contacts], "total": total, "page": page, "limit": limit}

@api_router.get("/tenants/{tenant_slug}/contacts/{contact_id}")
async def get_contact(tenant_slug: str, contact_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    contact = await db.contacts.find_one({"id": contact_id, "tenant_id": tenant["id"]}, {"_id": 0})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return serialize_doc(contact)

@api_router.get("/tenants/{tenant_slug}/contacts/{contact_id}/timeline")
async def get_contact_timeline(tenant_slug: str, contact_id: str):
    """Get unified timeline for a contact (requests, orders, messages)"""
    tenant = await get_tenant_by_slug(tenant_slug)
    contact = await db.contacts.find_one({"id": contact_id, "tenant_id": tenant["id"]}, {"_id": 0})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    timeline = []
    phone = contact.get("phone", "")
    email = contact.get("email", "")
    
    # Fetch requests
    req_query = {"tenant_id": tenant["id"]}
    if phone:
        req_query["guest_phone"] = phone
    requests = await db.guest_requests.find(req_query, {"_id": 0}).to_list(100)
    for r in requests:
        timeline.append({"type": "request", "data": serialize_doc(r), "timestamp": r.get("created_at", "")})
    
    # Fetch orders
    order_query = {"tenant_id": tenant["id"]}
    if phone:
        order_query["guest_phone"] = phone
    orders = await db.orders.find(order_query, {"_id": 0}).to_list(100)
    for o in orders:
        timeline.append({"type": "order", "data": serialize_doc(o), "timestamp": o.get("created_at", "")})
    
    # Sort by timestamp
    timeline.sort(key=lambda x: x["timestamp"], reverse=True)
    return timeline

# ============ WEBCHAT / CONVERSATION ROUTES ============
@api_router.post("/g/{tenant_slug}/chat/start")
async def start_chat(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    conversation = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "channel": "webchat",
        "status": "open",
        "guest_name": "",
        "assigned_agent": None,
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat()
    }
    await db.conversations.insert_one(conversation)
    return serialize_doc(conversation)

@api_router.post("/g/{tenant_slug}/chat/{conversation_id}/messages")
async def send_chat_message(tenant_slug: str, conversation_id: str, message: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    conv = await db.conversations.find_one({"id": conversation_id, "tenant_id": tenant["id"]})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    msg = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "conversation_id": conversation_id,
        "sender_type": message.get("sender_type", "guest"),  # guest, agent, ai
        "sender_name": message.get("sender_name", "Guest"),
        "content": message.get("content", ""),
        "created_at": now_utc().isoformat()
    }
    await db.messages.insert_one(msg)
    await db.conversations.update_one({"id": conversation_id}, {"$set": {"updated_at": now_utc().isoformat()}})
    
    result = serialize_doc(msg)
    
    # Check for escalation keywords
    urgent_keywords = ["urgent", "emergency", "broken", "complaint", "terrible", "acil", "sorun", "korkunç"]
    content_lower = message.get("content", "").lower()
    needs_attention = any(kw in content_lower for kw in urgent_keywords)
    if needs_attention:
        await db.conversations.update_one({"id": conversation_id}, {"$set": {"needs_attention": True}})
    
    # Broadcast via WebSocket
    await ws_manager.broadcast_tenant(tenant["id"], "message", "message", "created", result)
    
    return result

@api_router.get("/g/{tenant_slug}/chat/{conversation_id}/messages")
async def get_chat_messages(tenant_slug: str, conversation_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    messages = await db.messages.find(
        {"tenant_id": tenant["id"], "conversation_id": conversation_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(500)
    return [serialize_doc(m) for m in messages]

@api_router.get("/tenants/{tenant_slug}/conversations")
async def list_conversations(tenant_slug: str, status: Optional[str] = None):
    tenant = await get_tenant_by_slug(tenant_slug)
    query = {"tenant_id": tenant["id"]}
    if status:
        query["status"] = status
    convs = await db.conversations.find(query, {"_id": 0}).sort("updated_at", -1).to_list(100)
    return [serialize_doc(c) for c in convs]

# ============ AI MOCK PROVIDER ============
@api_router.post("/tenants/{tenant_slug}/ai/suggest-reply")
async def ai_suggest_reply(tenant_slug: str, context: dict):
    """Generate AI suggested reply using template-based mock"""
    tenant = await get_tenant_by_slug(tenant_slug)
    
    message_text = context.get("message", "")
    language = context.get("language", "en")
    sector = context.get("sector", tenant.get("business_type", "hotel"))
    
    # Simple language detection
    turkish_words = ["merhaba", "teşekkür", "lütfen", "rica", "oda", "yardım", "sipariş"]
    if any(w in message_text.lower() for w in turkish_words):
        language = "tr"
    
    # Template-based responses
    templates = {
        "hotel": {
            "en": {
                "greeting": "Welcome! Thank you for reaching out. How can we assist you during your stay?",
                "request": "We've received your request and our team is working on it. Is there anything else you need?",
                "complaint": "We sincerely apologize for the inconvenience. Our team has been notified and will address this immediately.",
                "checkout": "Thank you for staying with us! We hope you had a wonderful experience. Safe travels!",
                "default": "Thank you for your message. Our team will get back to you shortly."
            },
            "tr": {
                "greeting": "Hoş geldiniz! Bize ulaştığınız için teşekkür ederiz. Konaklamanız süresince size nasıl yardımcı olabiliriz?",
                "request": "Talebinizi aldık ve ekibimiz üzerinde çalışıyor. Başka bir ihtiyacınız var mı?",
                "complaint": "Yaşadığınız rahatsızlık için içtenlikle özür dileriz. Ekibimiz bilgilendirildi.",
                "checkout": "Bizde kaldığınız için teşekkür ederiz! Harika bir deneyim yaşamış olmanızı umuyoruz.",
                "default": "Mesajınız için teşekkür ederiz. Ekibimiz en kısa sürede size dönüş yapacaktır."
            }
        },
        "restaurant": {
            "en": {
                "greeting": "Welcome! Thank you for dining with us. How can we help?",
                "order": "Your order has been received and is being prepared. We'll update you when it's ready!",
                "complaint": "We're sorry about that. We'll make it right. A team member will be with you shortly.",
                "bill": "Your bill is being prepared. Thank you for dining with us!",
                "default": "Thank you for your message. How can we help you today?"
            },
            "tr": {
                "greeting": "Hoş geldiniz! Bizi tercih ettiğiniz için teşekkür ederiz. Size nasıl yardımcı olabiliriz?",
                "order": "Siparişiniz alındı ve hazırlanıyor. Hazır olduğunda sizi bilgilendireceğiz!",
                "complaint": "Bunun için üzgünüz. Hemen düzelteceğiz.",
                "bill": "Hesabınız hazırlanıyor. Bizi tercih ettiğiniz için teşekkür ederiz!",
                "default": "Mesajınız için teşekkürler. Bugün size nasıl yardımcı olabiliriz?"
            }
        }
    }
    
    # Intent detection
    intent = "default"
    lower = message_text.lower()
    if any(w in lower for w in ["hello", "hi", "merhaba", "selam"]):
        intent = "greeting"
    elif any(w in lower for w in ["order", "sipariş", "menu"]):
        intent = "order"
    elif any(w in lower for w in ["request", "need", "talep", "istiyorum"]):
        intent = "request"
    elif any(w in lower for w in ["complaint", "problem", "issue", "şikayet", "sorun"]):
        intent = "complaint"
    elif any(w in lower for w in ["bill", "check", "hesap", "ödeme"]):
        intent = "bill"
    elif any(w in lower for w in ["checkout", "leaving", "çıkış"]):
        intent = "checkout"
    
    sector_templates = templates.get(sector, templates["hotel"])
    lang_templates = sector_templates.get(language, sector_templates["en"])
    reply = lang_templates.get(intent, lang_templates["default"])
    
    # Update AI usage counter
    await db.tenants.update_one(
        {"id": tenant["id"]},
        {"$inc": {"usage_counters.ai_replies_this_month": 1}}
    )
    
    return {
        "suggestion": reply,
        "intent": intent,
        "language": language,
        "sector": sector,
        "provider": "mock_template_v1"
    }

# ============ LOYALTY ROUTES ============
@api_router.post("/g/{tenant_slug}/loyalty/join")
async def join_loyalty(tenant_slug: str, data: dict):
    """Guest joins loyalty program"""
    tenant = await get_tenant_by_slug(tenant_slug)
    phone = data.get("phone", "")
    email = data.get("email", "")
    name = data.get("name", "")
    
    if not phone and not email:
        raise HTTPException(status_code=400, detail="Phone or email required")
    
    # Create/update contact
    contact = await _upsert_contact(tenant["id"], name, phone, email)
    
    # Check if loyalty account exists
    existing = await db.loyalty_accounts.find_one({
        "tenant_id": tenant["id"],
        "contact_id": contact["id"]
    })
    if existing:
        return serialize_doc(existing)
    
    account = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "contact_id": contact["id"],
        "points": 0,
        "tier": "bronze",
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat()
    }
    await db.loyalty_accounts.insert_one(account)
    
    # Update contact with loyalty reference
    await db.contacts.update_one({"id": contact["id"]}, {"$set": {"loyalty_account_id": account["id"]}})
    
    # OTP stub - in production this would send SMS/email
    otp_code = "123456"  # TODO: Implement real OTP via SMS/email provider
    
    return {**serialize_doc(account), "otp_stub": otp_code, "message": "OTP sent (stub)"}

@api_router.get("/tenants/{tenant_slug}/loyalty/accounts")
async def list_loyalty_accounts(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    accounts = await db.loyalty_accounts.find({"tenant_id": tenant["id"]}, {"_id": 0}).to_list(200)
    return [serialize_doc(a) for a in accounts]

@api_router.get("/tenants/{tenant_slug}/loyalty/{account_id}/ledger")
async def get_loyalty_ledger(tenant_slug: str, account_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    entries = await db.loyalty_ledger.find(
        {"tenant_id": tenant["id"], "account_id": account_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    return [serialize_doc(e) for e in entries]

# ============ WEBSOCKET ENDPOINT ============
@app.websocket("/ws/{tenant_id}")
async def websocket_endpoint(websocket: WebSocket, tenant_id: str):
    channel = f"tenant:{tenant_id}"
    await ws_manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle ping/pong for keepalive
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket, channel)

# ============ GUEST INFO ROUTES ============
@api_router.get("/g/{tenant_slug}/room/{room_code}/info")
async def get_room_info(tenant_slug: str, room_code: str):
    """Public route for guest QR - returns room info + available services"""
    tenant = await get_tenant_by_slug(tenant_slug)
    room = await db.rooms.find_one({"tenant_id": tenant["id"], "room_code": room_code}, {"_id": 0})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    categories = await db.service_categories.find({"tenant_id": tenant["id"]}, {"_id": 0}).to_list(50)
    
    return {
        "tenant": {"name": tenant["name"], "slug": tenant["slug"]},
        "room": serialize_doc(room),
        "service_categories": [serialize_doc(c) for c in categories],
        "loyalty_enabled": tenant.get("loyalty_rules", {}).get("enabled", False)
    }

@api_router.get("/g/{tenant_slug}/table/{table_code}/info")
async def get_table_info(tenant_slug: str, table_code: str):
    """Public route for guest QR - returns table info + menu"""
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

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
