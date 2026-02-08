from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
import sys
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import asyncio
import jwt
import bcrypt
import random

# Add backend dir to path for local imports
sys.path.insert(0, str(Path(__file__).parent))
from rbac import ROLES, has_permission, get_accessible_modules, LOYALTY_TIERS, compute_tier, next_tier_info, analyze_sentiment, CONNECTOR_TYPES, FAKE_REVIEWS
from connectors_legacy import get_connector, StripeStubProvider
from security import rate_limiter, brute_force, create_session_doc, encrypt_field, decrypt_field, mask_email, mask_phone, PLAN_LIMITS, get_plan_limits, check_limit
from billing import create_billing_account, create_subscription, create_invoice, generate_mock_invoices
from analytics_engine import compute_analytics
from compliance import export_guest_data, forget_guest, log_consent
from referral import get_or_create_referral, track_referral_click, track_referral_signup, generate_referral_code
from guest_system import create_guest_token, decode_guest_token, generate_qr_png, generate_qr_print_pdf, encrypt_credentials, decrypt_credentials, ConnectorPollingTask

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'omni_inbox_hub')]

# Create the main app
app = FastAPI(title="Omni Inbox Hub API", version="0.1.0")
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# JWT Config
JWT_SECRET = os.environ.get("JWT_SECRET", "omni-inbox-hub-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

security = HTTPBearer(auto_error=False)

# ============ HELPERS ============
def serialize_doc(doc):
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

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, tenant_id: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return serialize_doc(user)

async def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None
    try:
        payload = decode_token(credentials.credentials)
        user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
        return serialize_doc(user) if user else None
    except:
        return None

# ============ WEBSOCKET MANAGER ============
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
            "ts": now_utc().isoformat()
        }
        await self.broadcast(channel, message)

ws_manager = ConnectionManager()

# ============ PYDANTIC MODELS ============
class TenantCreate(BaseModel):
    name: str
    slug: str
    business_type: str = "hotel"
    plan: str = "basic"

class TenantUpdate(BaseModel):
    name: Optional[str] = None
    hotel_enabled: Optional[bool] = None
    restaurant_enabled: Optional[bool] = None
    agency_enabled: Optional[bool] = None
    clinic_enabled: Optional[bool] = None

class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: str = "agent"

class LoginRequest(BaseModel):
    email: str
    password: str

class DepartmentCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = ""

class ServiceCategoryCreate(BaseModel):
    name: str
    department_code: str
    icon: Optional[str] = ""

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

class LoyaltyRulesUpdate(BaseModel):
    enabled: Optional[bool] = None
    points_per_request: Optional[int] = None
    points_per_order: Optional[int] = None
    points_per_currency_unit: Optional[int] = None

# ============ TENANT ISOLATION ============
async def get_tenant_by_slug(slug: str):
    tenant = await db.tenants.find_one({"slug": slug})
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant not found: {slug}")
    return serialize_doc(tenant)

async def get_tenant_by_id(tenant_id: str):
    tenant = await db.tenants.find_one({"id": tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant not found")
    return serialize_doc(tenant)

# ============ AUTH ROUTES ============
@api_router.post("/auth/register")
async def register(data: dict):
    """Register new tenant + owner user"""
    tenant_name = data.get("tenant_name", "")
    tenant_slug = data.get("tenant_slug", "")
    business_type = data.get("business_type", "hotel")
    plan = data.get("plan", "basic")
    email = data.get("email", "")
    password = data.get("password", "")
    name = data.get("name", "")
    
    if not all([tenant_name, tenant_slug, email, password, name]):
        raise HTTPException(status_code=400, detail="All fields required")
    
    existing_tenant = await db.tenants.find_one({"slug": tenant_slug})
    if existing_tenant:
        raise HTTPException(status_code=400, detail="Tenant slug already exists")
    
    existing_user = await db.users.find_one({"email": email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    tenant = {
        "id": new_id(),
        "name": tenant_name,
        "slug": tenant_slug,
        "business_type": business_type,
        "plan": plan,
        "hotel_enabled": business_type in ["hotel"],
        "restaurant_enabled": business_type in ["restaurant", "hotel"],
        "agency_enabled": False,
        "clinic_enabled": False,
        "plan_limits": {
            "max_users": 5 if plan == "basic" else 25,
            "max_rooms": 20 if plan == "basic" else 100,
            "max_tables": 10 if plan == "basic" else 50,
            "monthly_ai_replies": 50 if plan == "basic" else 500,
        },
        "usage_counters": {"users": 1, "rooms": 0, "tables": 0, "ai_replies_this_month": 0},
        "loyalty_rules": {"enabled": False, "points_per_request": 10, "points_per_order": 5, "points_per_currency_unit": 1},
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat()
    }
    await db.tenants.insert_one(tenant)
    
    user = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "email": email,
        "password_hash": hash_password(password),
        "name": name,
        "role": "owner",
        "department_code": None,
        "active": True,
        "created_at": now_utc().isoformat()
    }
    await db.users.insert_one(user)
    
    token = create_token(user["id"], tenant["id"], user["role"])
    
    return {
        "token": token,
        "user": {k: v for k, v in serialize_doc(user).items() if k != "password_hash"},
        "tenant": serialize_doc(tenant)
    }

@api_router.post("/auth/login")
async def login(data: LoginRequest):
    user = await db.users.find_one({"email": data.email})
    if not user or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not user.get("active", True):
        raise HTTPException(status_code=403, detail="Account disabled")
    
    tenant = await db.tenants.find_one({"id": user["tenant_id"]})
    token = create_token(user["id"], user["tenant_id"], user["role"])
    
    user_doc = serialize_doc(user)
    user_doc.pop("password_hash", None)
    user_doc.pop("_id", None)
    
    return {
        "token": token,
        "user": user_doc,
        "tenant": serialize_doc(tenant)
    }

@api_router.get("/auth/me")
async def get_me(user=Depends(get_current_user)):
    tenant = await get_tenant_by_id(user["tenant_id"])
    user_data = {k: v for k, v in user.items() if k != "password_hash"}
    return {"user": user_data, "tenant": tenant}

# ============ HEALTH ============
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
        "usage_counters": {"users": 1, "rooms": 0, "tables": 0, "ai_replies_this_month": 0},
        "loyalty_rules": {"enabled": False, "points_per_request": 10, "points_per_order": 5, "points_per_currency_unit": 1},
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

@api_router.patch("/tenants/{tenant_slug}/loyalty-rules")
async def update_loyalty_rules(tenant_slug: str, data: LoyaltyRulesUpdate):
    tenant = await get_tenant_by_slug(tenant_slug)
    rules = tenant.get("loyalty_rules", {})
    update = {}
    if data.enabled is not None:
        update["loyalty_rules.enabled"] = data.enabled
    if data.points_per_request is not None:
        update["loyalty_rules.points_per_request"] = data.points_per_request
    if data.points_per_order is not None:
        update["loyalty_rules.points_per_order"] = data.points_per_order
    if data.points_per_currency_unit is not None:
        update["loyalty_rules.points_per_currency_unit"] = data.points_per_currency_unit
    update["updated_at"] = now_utc().isoformat()
    await db.tenants.update_one({"id": tenant["id"]}, {"$set": update})
    updated = await db.tenants.find_one({"id": tenant["id"]}, {"_id": 0})
    return serialize_doc(updated)

# ============ USER MANAGEMENT ============
@api_router.post("/tenants/{tenant_slug}/users")
async def create_user(tenant_slug: str, data: UserCreate):
    tenant = await get_tenant_by_slug(tenant_slug)
    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    user = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "email": data.email,
        "password_hash": hash_password(data.password),
        "name": data.name,
        "role": data.role,
        "department_code": None,
        "active": True,
        "created_at": now_utc().isoformat()
    }
    await db.users.insert_one(user)
    await db.tenants.update_one({"id": tenant["id"]}, {"$inc": {"usage_counters.users": 1}})
    
    result = serialize_doc(user)
    result.pop("password_hash", None)
    return result

@api_router.get("/tenants/{tenant_slug}/users")
async def list_users(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    users = await db.users.find({"tenant_id": tenant["id"]}, {"_id": 0, "password_hash": 0}).to_list(100)
    return [serialize_doc(u) for u in users]

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

@api_router.delete("/tenants/{tenant_slug}/departments/{dept_id}")
async def delete_department(tenant_slug: str, dept_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    result = await db.departments.delete_one({"id": dept_id, "tenant_id": tenant["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Department not found")
    return {"deleted": True}

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
    usage = tenant.get("usage_counters", {})
    limits = tenant.get("plan_limits", {})
    if usage.get("rooms", 0) >= limits.get("max_rooms", 20):
        raise HTTPException(status_code=403, detail="Room limit reached")
    
    room_code = f"R{data.room_number}"
    room = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "room_number": data.room_number,
        "room_code": room_code,
        "room_type": data.room_type,
        "floor": data.floor,
        "qr_link": f"/g/{tenant_slug}/room/{room_code}",
        "status": "available",
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

@api_router.delete("/tenants/{tenant_slug}/rooms/{room_id}")
async def delete_room(tenant_slug: str, room_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    result = await db.rooms.delete_one({"id": room_id, "tenant_id": tenant["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Room not found")
    await db.tenants.update_one({"id": tenant["id"]}, {"$inc": {"usage_counters.rooms": -1}})
    return {"deleted": True}

# ============ GUEST REQUEST ROUTES ============
@api_router.post("/g/{tenant_slug}/room/{room_code}/requests")
async def create_guest_request(tenant_slug: str, room_code: str, data: GuestRequestCreate):
    tenant = await get_tenant_by_slug(tenant_slug)
    room = await db.rooms.find_one({"tenant_id": tenant["id"], "room_code": room_code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
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
    
    if data.guest_phone or data.guest_email:
        await _upsert_contact(tenant["id"], data.guest_name, data.guest_phone, data.guest_email)
    
    result = serialize_doc(request_doc)
    await ws_manager.broadcast_tenant(tenant["id"], "request", "guest_request", "created", result)
    return result

@api_router.get("/g/{tenant_slug}/room/{room_code}/requests")
async def list_guest_requests_by_room(tenant_slug: str, room_code: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    requests_list = await db.guest_requests.find(
        {"tenant_id": tenant["id"], "room_code": room_code}, {"_id": 0}
    ).sort("created_at", -1).to_list(100)
    return [serialize_doc(r) for r in requests_list]

@api_router.get("/tenants/{tenant_slug}/requests")
async def list_all_requests(tenant_slug: str, department: Optional[str] = None, status: Optional[str] = None, page: int = 1, limit: int = 50):
    tenant = await get_tenant_by_slug(tenant_slug)
    query = {"tenant_id": tenant["id"]}
    if department:
        query["department_code"] = department.upper()
    if status:
        query["status"] = status.upper()
    skip = (page - 1) * limit
    requests_list = await db.guest_requests.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.guest_requests.count_documents(query)
    return {"data": [serialize_doc(r) for r in requests_list], "total": total, "page": page}

@api_router.patch("/tenants/{tenant_slug}/requests/{request_id}")
async def update_guest_request(tenant_slug: str, request_id: str, data: GuestRequestUpdate, user=Depends(get_optional_user)):
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
            if data.status.upper() == "DONE":
                await _award_loyalty_points(tenant, "request", req)
    if data.assigned_to is not None:
        update_data["assigned_to"] = data.assigned_to
    if data.notes is not None:
        update_data["notes"] = data.notes
    
    # Pilot Fix 1: Track who made the update
    update_data["last_updated_by"] = user.get("name", "System") if user else "System"
    update_data["last_updated_by_id"] = user.get("id", "") if user else ""
    update_data["updated_at"] = now_utc().isoformat()
    await db.guest_requests.update_one({"id": request_id}, {"$set": update_data})
    
    updated = await db.guest_requests.find_one({"id": request_id}, {"_id": 0})
    result = serialize_doc(updated)
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
        "rating": data.rating, "rating_comment": data.comment, "updated_at": now_utc().isoformat()
    }})
    updated = await db.guest_requests.find_one({"id": request_id}, {"_id": 0})
    return serialize_doc(updated)

# ============ TABLE ROUTES ============
@api_router.post("/tenants/{tenant_slug}/tables")
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

@api_router.get("/tenants/{tenant_slug}/tables")
async def list_tables(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    tables = await db.tables.find({"tenant_id": tenant["id"]}, {"_id": 0}).to_list(200)
    return [serialize_doc(t) for t in tables]

@api_router.delete("/tenants/{tenant_slug}/tables/{table_id}")
async def delete_table(tenant_slug: str, table_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    result = await db.tables.delete_one({"id": table_id, "tenant_id": tenant["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Table not found")
    await db.tenants.update_one({"id": tenant["id"]}, {"$inc": {"usage_counters.tables": -1}})
    return {"deleted": True}

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

@api_router.delete("/tenants/{tenant_slug}/menu-categories/{cat_id}")
async def delete_menu_category(tenant_slug: str, cat_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    await db.menu_categories.delete_one({"id": cat_id, "tenant_id": tenant["id"]})
    return {"deleted": True}

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

@api_router.patch("/tenants/{tenant_slug}/menu-items/{item_id}")
async def update_menu_item(tenant_slug: str, item_id: str, data: MenuItemUpdate):
    tenant = await get_tenant_by_slug(tenant_slug)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    await db.menu_items.update_one({"id": item_id, "tenant_id": tenant["id"]}, {"$set": update_data})
    updated = await db.menu_items.find_one({"id": item_id}, {"_id": 0})
    return serialize_doc(updated)

@api_router.delete("/tenants/{tenant_slug}/menu-items/{item_id}")
async def delete_menu_item(tenant_slug: str, item_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    await db.menu_items.delete_one({"id": item_id, "tenant_id": tenant["id"]})
    return {"deleted": True}

# ============ ORDER ROUTES ============
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
    
    if data.guest_phone or data.guest_email:
        await _upsert_contact(tenant["id"], data.guest_name, data.guest_phone, data.guest_email)
    
    result = serialize_doc(order)
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
async def list_all_orders(tenant_slug: str, status: Optional[str] = None, page: int = 1, limit: int = 50):
    tenant = await get_tenant_by_slug(tenant_slug)
    query = {"tenant_id": tenant["id"]}
    if status:
        query["status"] = status.upper()
    skip = (page - 1) * limit
    orders = await db.orders.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.orders.count_documents(query)
    return {"data": [serialize_doc(o) for o in orders], "total": total, "page": page}

@api_router.patch("/tenants/{tenant_slug}/orders/{order_id}")
async def update_order_status(tenant_slug: str, order_id: str, data: OrderStatusUpdate):
    tenant = await get_tenant_by_slug(tenant_slug)
    order = await db.orders.find_one({"id": order_id, "tenant_id": tenant["id"]})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    update = {"status": data.status.upper(), "updated_at": now_utc().isoformat()}
    await db.orders.update_one({"id": order_id}, {"$set": update})
    
    if data.status.upper() == "SERVED":
        await _award_loyalty_points(tenant, "order", serialize_doc(order))
    
    updated = await db.orders.find_one({"id": order_id}, {"_id": 0})
    result = serialize_doc(updated)
    await ws_manager.broadcast_tenant(tenant["id"], "order", "order", "updated", result)
    return result

# ============ CONTACT / CRM ROUTES ============
async def _upsert_contact(tenant_id: str, name: str = "", phone: str = "", email: str = ""):
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
        "updated_at": now_utc().isoformat()
    }
    await db.contacts.insert_one(contact)
    return serialize_doc(contact)

@api_router.get("/tenants/{tenant_slug}/contacts")
async def list_contacts(tenant_slug: str, page: int = 1, limit: int = 20, search: Optional[str] = None):
    tenant = await get_tenant_by_slug(tenant_slug)
    query = {"tenant_id": tenant["id"]}
    if search:
        query["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]
    skip = (page - 1) * limit
    contacts = await db.contacts.find(query, {"_id": 0}).sort("updated_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.contacts.count_documents(query)
    return {"data": [serialize_doc(c) for c in contacts], "total": total, "page": page, "limit": limit}

@api_router.get("/tenants/{tenant_slug}/contacts/{contact_id}")
async def get_contact(tenant_slug: str, contact_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    contact = await db.contacts.find_one({"id": contact_id, "tenant_id": tenant["id"]}, {"_id": 0})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return serialize_doc(contact)

@api_router.patch("/tenants/{tenant_slug}/contacts/{contact_id}")
async def update_contact(tenant_slug: str, contact_id: str, data: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    allowed = ["name", "tags", "notes", "consent_marketing", "consent_data"]
    update_data = {k: v for k, v in data.items() if k in allowed}
    update_data["updated_at"] = now_utc().isoformat()
    await db.contacts.update_one({"id": contact_id, "tenant_id": tenant["id"]}, {"$set": update_data})
    updated = await db.contacts.find_one({"id": contact_id}, {"_id": 0})
    return serialize_doc(updated)

@api_router.get("/tenants/{tenant_slug}/contacts/{contact_id}/timeline")
async def get_contact_timeline(tenant_slug: str, contact_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    contact = await db.contacts.find_one({"id": contact_id, "tenant_id": tenant["id"]}, {"_id": 0})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    timeline = []
    phone = contact.get("phone", "")
    email = contact.get("email", "")
    
    if phone:
        reqs = await db.guest_requests.find({"tenant_id": tenant["id"], "guest_phone": phone}, {"_id": 0}).to_list(100)
        for r in reqs:
            timeline.append({"type": "request", "data": serialize_doc(r), "timestamp": r.get("created_at", "")})
        
        ords = await db.orders.find({"tenant_id": tenant["id"], "guest_phone": phone}, {"_id": 0}).to_list(100)
        for o in ords:
            timeline.append({"type": "order", "data": serialize_doc(o), "timestamp": o.get("created_at", "")})
    
    if email:
        reqs = await db.guest_requests.find({"tenant_id": tenant["id"], "guest_email": email}, {"_id": 0}).to_list(100)
        for r in reqs:
            if not any(t["data"].get("id") == r.get("id") for t in timeline):
                timeline.append({"type": "request", "data": serialize_doc(r), "timestamp": r.get("created_at", "")})
    
    # Loyalty ledger
    if contact.get("loyalty_account_id"):
        ledger = await db.loyalty_ledger.find({"account_id": contact["loyalty_account_id"]}, {"_id": 0}).to_list(100)
        for l in ledger:
            timeline.append({"type": "loyalty", "data": serialize_doc(l), "timestamp": l.get("created_at", "")})
    
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
        "needs_attention": False,
        "last_message": "",
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat()
    }
    await db.conversations.insert_one(conversation)
    result = serialize_doc(conversation)
    await ws_manager.broadcast_tenant(tenant["id"], "conversation", "conversation", "created", result)
    return result

@api_router.post("/g/{tenant_slug}/chat/{conversation_id}/messages")
async def send_chat_message(tenant_slug: str, conversation_id: str, message: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    conv = await db.conversations.find_one({"id": conversation_id, "tenant_id": tenant["id"]})
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    content = message.get("content", "")
    msg = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "conversation_id": conversation_id,
        "sender_type": message.get("sender_type", "guest"),
        "sender_name": message.get("sender_name", "Guest"),
        "content": content,
        "created_at": now_utc().isoformat()
    }
    await db.messages.insert_one(msg)
    
    # Update conversation
    update = {"updated_at": now_utc().isoformat(), "last_message": content[:100]}
    
    # Check for escalation
    urgent_keywords = ["urgent", "emergency", "broken", "complaint", "terrible", "acil", "sorun", "korkunç"]
    if any(kw in content.lower() for kw in urgent_keywords):
        update["needs_attention"] = True
    
    if message.get("sender_name"):
        update["guest_name"] = message["sender_name"]
    
    await db.conversations.update_one({"id": conversation_id}, {"$set": update})
    
    result = serialize_doc(msg)
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

@api_router.patch("/tenants/{tenant_slug}/conversations/{conv_id}")
async def update_conversation(tenant_slug: str, conv_id: str, data: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    allowed = ["status", "assigned_agent", "needs_attention"]
    update_data = {k: v for k, v in data.items() if k in allowed}
    update_data["updated_at"] = now_utc().isoformat()
    await db.conversations.update_one({"id": conv_id, "tenant_id": tenant["id"]}, {"$set": update_data})
    updated = await db.conversations.find_one({"id": conv_id}, {"_id": 0})
    return serialize_doc(updated)

# ============ AI MOCK PROVIDER ============
@api_router.post("/tenants/{tenant_slug}/ai/suggest-reply")
async def ai_suggest_reply(tenant_slug: str, context: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    
    message_text = context.get("message", "")
    language = context.get("language", "en")
    sector = context.get("sector", tenant.get("business_type", "hotel"))
    
    turkish_words = ["merhaba", "teşekkür", "lütfen", "rica", "oda", "yardım", "sipariş", "garson", "hesap"]
    if any(w in message_text.lower() for w in turkish_words):
        language = "tr"
    
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
                "greeting": "Hos geldiniz! Bize ulastiginiz icin tesekkur ederiz. Konaklamaniz suresince size nasil yardimci olabiliriz?",
                "request": "Talebinizi aldik ve ekibimiz uzerinde calisiyor. Baska bir ihtiyaciniz var mi?",
                "complaint": "Yasadiginiz rahatsizlik icin ictenlikle ozur dileriz. Ekibimiz bilgilendirildi.",
                "checkout": "Bizde kaldiginiz icin tesekkur ederiz! Harika bir deneyim yasamis olmanizi umuyoruz.",
                "default": "Mesajiniz icin tesekkur ederiz. Ekibimiz en kisa surede size donus yapacaktir."
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
                "greeting": "Hos geldiniz! Bizi tercih ettiginiz icin tesekkur ederiz.",
                "order": "Siparisinis alindi ve hazirlaniyor. Hazir oldugunda sizi bilgilendireceğiz!",
                "complaint": "Bunun icin uzgunuz. Hemen duzelteceğiz.",
                "bill": "Hesabiniz hazirlaniyor. Bizi tercih ettiginiz icin tesekkur ederiz!",
                "default": "Mesajiniz icin tesekkurler. Bugün size nasil yardimci olabiliriz?"
            }
        }
    }
    
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
    
    await db.tenants.update_one({"id": tenant["id"]}, {"$inc": {"usage_counters.ai_replies_this_month": 1}})
    
    return {"suggestion": reply, "intent": intent, "language": language, "sector": sector, "provider": "mock_template_v1"}

# ============ LOYALTY ROUTES ============
@api_router.post("/g/{tenant_slug}/loyalty/join")
async def join_loyalty(tenant_slug: str, data: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    phone = data.get("phone", "")
    email = data.get("email", "")
    name = data.get("name", "")
    
    if not phone and not email:
        raise HTTPException(status_code=400, detail="Phone or email required")
    
    contact = await _upsert_contact(tenant["id"], name, phone, email)
    
    existing = await db.loyalty_accounts.find_one({"tenant_id": tenant["id"], "contact_id": contact["id"]})
    if existing:
        return serialize_doc(existing)
    
    account = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "contact_id": contact["id"],
        "contact_name": name,
        "contact_phone": phone,
        "contact_email": email,
        "points": 0,
        "tier": "bronze",
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat()
    }
    await db.loyalty_accounts.insert_one(account)
    await db.contacts.update_one({"id": contact["id"]}, {"$set": {"loyalty_account_id": account["id"]}})
    
    return {**serialize_doc(account), "otp_stub": "123456", "message": "OTP sent (stub)"}

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

async def _award_loyalty_points(tenant: dict, event_type: str, event_data: dict):
    """Award loyalty points when request resolved or order served"""
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
            "created_at": now_utc().isoformat()
        }
        await db.loyalty_ledger.insert_one(entry)
        await db.loyalty_accounts.update_one(
            {"id": contact["loyalty_account_id"]},
            {"$inc": {"points": points}, "$set": {"updated_at": now_utc().isoformat()}}
        )

# ============ DASHBOARD STATS ============
@api_router.get("/tenants/{tenant_slug}/stats")
async def get_dashboard_stats(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    tid = tenant["id"]
    
    total_requests = await db.guest_requests.count_documents({"tenant_id": tid})
    open_requests = await db.guest_requests.count_documents({"tenant_id": tid, "status": "OPEN"})
    in_progress_requests = await db.guest_requests.count_documents({"tenant_id": tid, "status": "IN_PROGRESS"})
    done_requests = await db.guest_requests.count_documents({"tenant_id": tid, "status": {"$in": ["DONE", "CLOSED"]}})
    
    total_orders = await db.orders.count_documents({"tenant_id": tid})
    active_orders = await db.orders.count_documents({"tenant_id": tid, "status": {"$in": ["RECEIVED", "PREPARING"]}})
    
    total_contacts = await db.contacts.count_documents({"tenant_id": tid})
    total_conversations = await db.conversations.count_documents({"tenant_id": tid})
    
    rooms_count = await db.rooms.count_documents({"tenant_id": tid})
    tables_count = await db.tables.count_documents({"tenant_id": tid})
    
    # Average rating
    pipeline = [
        {"$match": {"tenant_id": tid, "rating": {"$ne": None}}},
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}}
    ]
    rating_result = await db.guest_requests.aggregate(pipeline).to_list(1)
    avg_rating = round(rating_result[0]["avg_rating"], 1) if rating_result else 0
    rating_count = rating_result[0]["count"] if rating_result else 0
    
    return {
        "requests": {"total": total_requests, "open": open_requests, "in_progress": in_progress_requests, "done": done_requests},
        "orders": {"total": total_orders, "active": active_orders},
        "contacts": total_contacts,
        "conversations": total_conversations,
        "rooms": rooms_count,
        "tables": tables_count,
        "avg_rating": avg_rating,
        "rating_count": rating_count,
        "usage": tenant.get("usage_counters", {}),
        "limits": tenant.get("plan_limits", {})
    }

# ============ GUEST INFO ROUTES ============
@api_router.get("/g/{tenant_slug}/room/{room_code}/info")
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
        "loyalty_enabled": tenant.get("loyalty_rules", {}).get("enabled", False)
    }

@api_router.get("/g/{tenant_slug}/table/{table_code}/info")
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

# ============ SEED DATA ============
@api_router.post("/seed")
async def seed_data():
    """Create sample data for demo purposes"""
    # Check if already seeded
    existing = await db.tenants.find_one({"slug": "grand-hotel"})
    if existing:
        return {"message": "Already seeded", "tenant_slug": "grand-hotel"}
    
    # Create tenant
    tenant_id = new_id()
    tenant = {
        "id": tenant_id,
        "name": "Grand Hotel Istanbul",
        "slug": "grand-hotel",
        "business_type": "hotel",
        "plan": "pro",
        "hotel_enabled": True,
        "restaurant_enabled": True,
        "agency_enabled": False,
        "clinic_enabled": False,
        "plan_limits": {"max_users": 25, "max_rooms": 100, "max_tables": 50, "monthly_ai_replies": 500},
        "usage_counters": {"users": 1, "rooms": 5, "tables": 3, "ai_replies_this_month": 12},
        "loyalty_rules": {"enabled": True, "points_per_request": 10, "points_per_order": 5, "points_per_currency_unit": 1},
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat()
    }
    await db.tenants.insert_one(tenant)
    
    # Create owner user
    owner_id = new_id()
    await db.users.insert_one({
        "id": owner_id,
        "tenant_id": tenant_id,
        "email": "admin@grandhotel.com",
        "password_hash": hash_password("admin123"),
        "name": "Admin User",
        "role": "owner",
        "department_code": None,
        "active": True,
        "created_at": now_utc().isoformat()
    })
    
    # Departments
    departments = [
        {"id": new_id(), "tenant_id": tenant_id, "name": "Housekeeping", "code": "HK", "description": "Room cleaning and amenities", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Technical", "code": "TECH", "description": "Maintenance and repairs", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Food & Beverage", "code": "FB", "description": "Room service and minibar", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Front Desk", "code": "FRONTDESK", "description": "Reception and concierge", "created_at": now_utc().isoformat()},
    ]
    await db.departments.insert_many(departments)
    
    # Service categories
    service_cats = [
        {"id": new_id(), "tenant_id": tenant_id, "name": "Extra Towels", "department_code": "HK", "icon": "towel", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Room Cleaning", "department_code": "HK", "icon": "sparkles", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "AC/Heating", "department_code": "TECH", "icon": "thermometer", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Plumbing", "department_code": "TECH", "icon": "wrench", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Room Service", "department_code": "FB", "icon": "utensils", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Wake-up Call", "department_code": "FRONTDESK", "icon": "bell", "created_at": now_utc().isoformat()},
    ]
    await db.service_categories.insert_many(service_cats)
    
    # Rooms (using simple codes for demo - production uses secure random codes)
    rooms = []
    for floor in range(1, 4):
        for room_num in range(1, 3):
            rn = f"{floor}0{room_num}"
            rooms.append({
                "id": new_id(), "tenant_id": tenant_id,
                "room_number": rn, "room_code": f"R{rn}",
                "room_type": "deluxe" if floor == 3 else "standard",
                "floor": str(floor),
                "is_active": True,
                "qr_version": 1,
                "qr_link": f"/g/grand-hotel/room/R{rn}",
                "status": "available",
                "created_at": now_utc().isoformat()
            })
    await db.rooms.insert_many(rooms)
    
    # Tables (using simple codes for demo)
    tables = []
    for t in range(1, 4):
        tables.append({
            "id": new_id(), "tenant_id": tenant_id,
            "table_number": str(t), "table_code": f"T{t}",
            "capacity": 4, "section": "terrace" if t <= 2 else "indoor",
            "is_active": True,
            "qr_version": 1,
            "qr_link": f"/g/grand-hotel/table/T{t}",
            "created_at": now_utc().isoformat()
        })
    await db.tables.insert_many(tables)
    
    # Menu categories
    cat_main_id = new_id()
    cat_app_id = new_id()
    cat_bev_id = new_id()
    cat_dessert_id = new_id()
    menu_cats = [
        {"id": cat_app_id, "tenant_id": tenant_id, "name": "Appetizers", "sort_order": 0, "created_at": now_utc().isoformat()},
        {"id": cat_main_id, "tenant_id": tenant_id, "name": "Main Course", "sort_order": 1, "created_at": now_utc().isoformat()},
        {"id": cat_dessert_id, "tenant_id": tenant_id, "name": "Desserts", "sort_order": 2, "created_at": now_utc().isoformat()},
        {"id": cat_bev_id, "tenant_id": tenant_id, "name": "Beverages", "sort_order": 3, "created_at": now_utc().isoformat()},
    ]
    await db.menu_categories.insert_many(menu_cats)
    
    # Menu items
    menu_items = [
        {"id": new_id(), "tenant_id": tenant_id, "name": "Hummus", "description": "Classic chickpea dip with olive oil", "price": 85.0, "category_id": cat_app_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Mercimek Soup", "description": "Traditional red lentil soup", "price": 65.0, "category_id": cat_app_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Adana Kebab", "description": "Spicy minced meat kebab on skewers", "price": 250.0, "category_id": cat_main_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Iskender", "description": "Doner on bread with tomato sauce and yogurt", "price": 280.0, "category_id": cat_main_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Grilled Sea Bass", "description": "Fresh daily catch, grilled with herbs", "price": 350.0, "category_id": cat_main_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Kunefe", "description": "Crispy kadayif with melted cheese and syrup", "price": 120.0, "category_id": cat_dessert_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Baklava", "description": "Pistachio baklava, 4 pieces", "price": 95.0, "category_id": cat_dessert_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Turkish Tea", "description": "Classic cay", "price": 25.0, "category_id": cat_bev_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Turkish Coffee", "description": "Traditional Turkish coffee", "price": 45.0, "category_id": cat_bev_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Ayran", "description": "Traditional yogurt drink", "price": 35.0, "category_id": cat_bev_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Fresh Orange Juice", "description": "Freshly squeezed", "price": 55.0, "category_id": cat_bev_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
    ]
    await db.menu_items.insert_many(menu_items)
    
    # Sample guest requests
    sample_requests = [
        {"id": new_id(), "tenant_id": tenant_id, "room_id": rooms[0]["id"], "room_code": rooms[0]["room_code"], "room_number": rooms[0]["room_number"], "category": "housekeeping", "department_code": "HK", "description": "Need extra towels and pillows", "priority": "normal", "status": "OPEN", "guest_name": "John Smith", "guest_phone": "+905551234567", "guest_email": "", "assigned_to": None, "notes": "", "first_response_at": None, "resolved_at": None, "rating": None, "rating_comment": None, "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "room_id": rooms[1]["id"], "room_code": rooms[1]["room_code"], "room_number": rooms[1]["room_number"], "category": "maintenance", "department_code": "TECH", "description": "Air conditioning not working properly", "priority": "high", "status": "IN_PROGRESS", "guest_name": "Maria Garcia", "guest_phone": "+905559876543", "guest_email": "maria@email.com", "assigned_to": "Maintenance Team", "notes": "Technician dispatched", "first_response_at": now_utc().isoformat(), "resolved_at": None, "rating": None, "rating_comment": None, "created_at": (now_utc() - timedelta(hours=2)).isoformat(), "updated_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "room_id": rooms[2]["id"], "room_code": rooms[2]["room_code"], "room_number": rooms[2]["room_number"], "category": "room_service", "department_code": "FB", "description": "Breakfast order: 2x eggs, toast, coffee", "priority": "normal", "status": "DONE", "guest_name": "Ahmed Hassan", "guest_phone": "+905553456789", "guest_email": "", "assigned_to": "Room Service", "notes": "Delivered", "first_response_at": (now_utc() - timedelta(hours=1)).isoformat(), "resolved_at": now_utc().isoformat(), "rating": 5, "rating_comment": "Excellent service!", "created_at": (now_utc() - timedelta(hours=3)).isoformat(), "updated_at": now_utc().isoformat()},
    ]
    await db.guest_requests.insert_many(sample_requests)
    
    # Sample contacts
    contacts = [
        {"id": new_id(), "tenant_id": tenant_id, "name": "John Smith", "phone": "+905551234567", "email": "john@email.com", "tags": ["vip", "repeat"], "notes": "Prefers high floor", "consent_marketing": True, "consent_data": True, "loyalty_account_id": None, "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Maria Garcia", "phone": "+905559876543", "email": "maria@email.com", "tags": ["new"], "notes": "", "consent_marketing": False, "consent_data": True, "loyalty_account_id": None, "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Ahmed Hassan", "phone": "+905553456789", "email": "ahmed@email.com", "tags": ["loyalty"], "notes": "Allergic to nuts", "consent_marketing": True, "consent_data": True, "loyalty_account_id": None, "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat()},
    ]
    await db.contacts.insert_many(contacts)
    
    # Sample orders
    sample_orders = [
        {"id": new_id(), "tenant_id": tenant_id, "table_id": tables[0]["id"], "table_code": "T1", "table_number": "1", "items": [{"menu_item_id": menu_items[2]["id"], "menu_item_name": "Adana Kebab", "quantity": 2, "price": 250.0, "notes": ""}, {"menu_item_id": menu_items[7]["id"], "menu_item_name": "Turkish Tea", "quantity": 2, "price": 25.0, "notes": ""}], "total": 550.0, "status": "PREPARING", "order_type": "dine_in", "guest_name": "Table 1 Guest", "guest_phone": "", "guest_email": "", "notes": "Extra spicy", "created_at": (now_utc() - timedelta(minutes=15)).isoformat(), "updated_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "table_id": tables[1]["id"], "table_code": "T2", "table_number": "2", "items": [{"menu_item_id": menu_items[3]["id"], "menu_item_name": "Iskender", "quantity": 1, "price": 280.0, "notes": ""}, {"menu_item_id": menu_items[9]["id"], "menu_item_name": "Ayran", "quantity": 1, "price": 35.0, "notes": ""}], "total": 315.0, "status": "RECEIVED", "order_type": "dine_in", "guest_name": "Table 2 Guest", "guest_phone": "", "guest_email": "", "notes": "", "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat()},
    ]
    await db.orders.insert_many(sample_orders)
    
    # Sprint 3: Seed conversations + messages
    conv1_id = new_id()
    conv2_id = new_id()
    conv3_id = new_id()
    await db.conversations.insert_many([
        {"id": conv1_id, "tenant_id": tenant_id, "channel_type": "WEBCHAT", "contact_id": contacts[0]["id"],
         "status": "OPEN", "assigned_user_id": None, "guest_name": "John Smith",
         "last_message_at": now_utc().isoformat(), "needs_attention": False, "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat()},
        {"id": conv2_id, "tenant_id": tenant_id, "channel_type": "WHATSAPP", "contact_id": contacts[1]["id"],
         "status": "OPEN", "assigned_user_id": None, "guest_name": "Maria Garcia",
         "last_message_at": (now_utc() - timedelta(hours=1)).isoformat(), "needs_attention": True, "created_at": (now_utc() - timedelta(hours=2)).isoformat(), "updated_at": now_utc().isoformat()},
        {"id": conv3_id, "tenant_id": tenant_id, "channel_type": "INSTAGRAM", "contact_id": None,
         "status": "OPEN", "assigned_user_id": None, "guest_name": "@travel_adventures",
         "last_message_at": (now_utc() - timedelta(hours=3)).isoformat(), "created_at": (now_utc() - timedelta(hours=3)).isoformat(), "updated_at": now_utc().isoformat()},
    ])
    await db.messages.insert_many([
        {"id": new_id(), "tenant_id": tenant_id, "conversation_id": conv1_id, "direction": "IN",
         "body": "Hello, I'd like to request late checkout for tomorrow.", "created_at": (now_utc() - timedelta(minutes=30)).isoformat(),
         "meta": {"sender_type": "guest", "sender_name": "John Smith"}},
        {"id": new_id(), "tenant_id": tenant_id, "conversation_id": conv1_id, "direction": "OUT",
         "body": "Of course! We can extend your checkout to 2 PM. Would that work?", "created_at": (now_utc() - timedelta(minutes=25)).isoformat(),
         "last_updated_by": "Admin User", "meta": {"sender_type": "agent"}},
        {"id": new_id(), "tenant_id": tenant_id, "conversation_id": conv1_id, "direction": "IN",
         "body": "Perfect, thank you so much!", "created_at": now_utc().isoformat(),
         "meta": {"sender_type": "guest", "sender_name": "John Smith"}},
        {"id": new_id(), "tenant_id": tenant_id, "conversation_id": conv2_id, "direction": "IN",
         "body": "The AC in my room is not working. This is urgent!", "created_at": (now_utc() - timedelta(hours=1)).isoformat(),
         "meta": {"sender_type": "guest", "channel": "WHATSAPP", "is_stub": True}},
        {"id": new_id(), "tenant_id": tenant_id, "conversation_id": conv3_id, "direction": "IN",
         "body": "Love your hotel photos! Do you have availability next month?", "created_at": (now_utc() - timedelta(hours=3)).isoformat(),
         "meta": {"sender_type": "guest", "channel": "INSTAGRAM", "is_stub": True}},
    ])

    # Sprint 3: Seed connector credentials (enabled stubs)
    for ct in ["WEBCHAT", "WHATSAPP", "INSTAGRAM", "GOOGLE_REVIEWS", "TRIPADVISOR"]:
        await db.connector_credentials.insert_one({
            "id": new_id(), "tenant_id": tenant_id, "connector_type": ct,
            "enabled": True, "encrypted_json": "", "last_sync_at": now_utc().isoformat() if ct != "WEBCHAT" else None,
            "status": "active" if ct == "WEBCHAT" else "synced",
            "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat(),
        })

    # Sprint 3: Seed usage counter
    month_key = now_utc().strftime("%Y-%m")
    await db.usage_counters.insert_one({
        "id": new_id(), "tenant_id": tenant_id, "month_key": month_key,
        "ai_replies_used": 13, "ai_replies_limit": 500, "updated_at": now_utc().isoformat(),
    })

    return {
        "message": "Seed data created successfully",
        "tenant_slug": "grand-hotel",
        "login": {"email": "admin@grandhotel.com", "password": "admin123"},
        "sample_qr_links": {
            "room": "/g/grand-hotel/room/R101",
            "table": "/g/grand-hotel/table/T1"
        }
    }

# ============ RBAC ROUTES ============
@api_router.get("/rbac/roles")
async def get_roles():
    return ROLES

@api_router.get("/rbac/modules")
async def get_user_modules(user=Depends(get_current_user)):
    return {"modules": get_accessible_modules(user.get("role", "agent")), "role": user.get("role")}

@api_router.get("/rbac/tiers")
async def get_loyalty_tiers():
    return LOYALTY_TIERS

# ============ PHASE 5: SECURITY HARDENING ============
from fastapi import Request

@api_router.post("/auth/refresh")
async def refresh_token(data: dict):
    """Refresh access token"""
    old_token = data.get("token", "")
    try:
        payload = decode_token(old_token)
        user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        new_token = create_token(user["id"], user["tenant_id"], user["role"])
        return {"token": new_token, "user": {k: v for k, v in serialize_doc(user).items() if k != "password_hash"}}
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

@api_router.post("/auth/logout")
async def logout(request: Request, user=Depends(get_current_user)):
    """Logout and invalidate session"""
    await _log_audit(user["tenant_id"], "logout", "user", user["id"], user["id"])
    return {"status": "logged_out"}

@api_router.get("/auth/sessions")
async def list_sessions(user=Depends(get_current_user)):
    """List active sessions for current user"""
    sessions = await db.sessions.find(
        {"user_id": user["id"], "is_active": True}, {"_id": 0}
    ).sort("last_seen_at", -1).to_list(20)
    return [serialize_doc(s) for s in sessions]

@api_router.delete("/auth/sessions/{session_id}")
async def revoke_session(session_id: str, user=Depends(get_current_user)):
    """Revoke a specific session"""
    result = await db.sessions.update_one(
        {"id": session_id, "user_id": user["id"]},
        {"$set": {"is_active": False}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"revoked": True}

# ============ PHASE 5: PLAN ENFORCEMENT ============
@api_router.get("/plans")
async def get_plans():
    return PLAN_LIMITS

@api_router.get("/tenants/{tenant_slug}/usage")
async def get_usage(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    plan = tenant.get("plan", "basic")
    limits = get_plan_limits(plan)
    usage = tenant.get("usage_counters", {})
    
    # Count current usage
    contacts = await db.contacts.count_documents({"tenant_id": tenant["id"]})
    active_offers = await db.offers.count_documents({"tenant_id": tenant["id"], "status": {"$in": ["draft", "sent"]}})
    reservations = await db.reservations.count_documents({"tenant_id": tenant["id"]})
    
    return {
        "plan": plan,
        "plan_label": limits.get("label", plan),
        "metrics": {
            "users": {"current": usage.get("users", 1), "limit": limits["max_users"]},
            "rooms": {"current": usage.get("rooms", 0), "limit": limits["max_rooms"]},
            "tables": {"current": usage.get("tables", 0), "limit": limits["max_tables"]},
            "contacts": {"current": contacts, "limit": limits["max_contacts"]},
            "ai_replies": {"current": usage.get("ai_replies_this_month", 0), "limit": limits["monthly_ai_replies"]},
            "reservations": {"current": reservations, "limit": limits["max_monthly_reservations"]},
            "active_offers": {"current": active_offers, "limit": limits["max_active_offers"]},
        }
    }

@api_router.post("/tenants/{tenant_slug}/upgrade")
async def upgrade_plan(tenant_slug: str, data: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    new_plan = data.get("plan", "pro")
    if new_plan not in PLAN_LIMITS:
        raise HTTPException(status_code=400, detail="Invalid plan")
    
    new_limits = get_plan_limits(new_plan)
    await db.tenants.update_one({"id": tenant["id"]}, {"$set": {
        "plan": new_plan,
        "plan_limits": {
            "max_users": new_limits["max_users"],
            "max_rooms": new_limits["max_rooms"],
            "max_tables": new_limits["max_tables"],
            "monthly_ai_replies": new_limits["monthly_ai_replies"],
        },
        "updated_at": now_utc().isoformat()
    }})
    await _log_audit(tenant["id"], "plan_upgraded", "tenant", tenant["id"], details={"from": tenant.get("plan"), "to": new_plan})
    
    updated = await db.tenants.find_one({"id": tenant["id"]}, {"_id": 0})
    return serialize_doc(updated)

# ============ PHASE 5: BILLING ============
@api_router.get("/tenants/{tenant_slug}/billing")
async def get_billing(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    billing = await db.billing_accounts.find_one({"tenant_id": tenant["id"]}, {"_id": 0})
    if not billing:
        billing = create_billing_account(tenant["id"], tenant.get("plan", "basic"))
        await db.billing_accounts.insert_one(billing)
    
    subscription = await db.subscriptions.find_one({"tenant_id": tenant["id"]}, {"_id": 0})
    if not subscription:
        subscription = create_subscription(tenant["id"], tenant.get("plan", "basic"))
        await db.subscriptions.insert_one(subscription)
    
    invoices = await db.invoices.find({"tenant_id": tenant["id"]}, {"_id": 0}).sort("created_at", -1).to_list(20)
    if not invoices:
        invoices = generate_mock_invoices(tenant["id"], tenant.get("plan", "basic"))
        if invoices:
            await db.invoices.insert_many(invoices)
    
    return {
        "billing_account": serialize_doc(billing),
        "subscription": serialize_doc(subscription),
        "invoices": [serialize_doc(i) for i in invoices],
        "plan": tenant.get("plan", "basic"),
        "plan_details": get_plan_limits(tenant.get("plan", "basic"))
    }

@api_router.post("/billing/webhook/stripe")
async def stripe_webhook(data: dict):
    """Placeholder for Stripe webhook - TODO: implement real webhook validation"""
    logger.info(f"Stripe webhook received (stub): {data.get('type', 'unknown')}")
    return {"received": True}

# ============ PHASE 5: ONBOARDING ============
@api_router.get("/tenants/{tenant_slug}/onboarding")
async def get_onboarding_status(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    onboarding = await db.onboarding.find_one({"tenant_id": tenant["id"]}, {"_id": 0})
    if not onboarding:
        onboarding = {
            "id": new_id(),
            "tenant_id": tenant["id"],
            "completed": False,
            "current_step": 1,
            "steps": {
                "1": {"label": "Business Info", "completed": True},
                "2": {"label": "Create Departments", "completed": False},
                "3": {"label": "Add Rooms / Tables", "completed": False},
                "4": {"label": "Configure Menu", "completed": False},
                "5": {"label": "Loyalty Rules", "completed": False},
                "6": {"label": "Generate QR Codes", "completed": False},
                "7": {"label": "Invite Team", "completed": False},
            },
            "created_at": now_utc().isoformat()
        }
        await db.onboarding.insert_one(onboarding)
    
    # Auto-check completed steps
    depts = await db.departments.count_documents({"tenant_id": tenant["id"]})
    rooms = await db.rooms.count_documents({"tenant_id": tenant["id"]})
    tables = await db.tables.count_documents({"tenant_id": tenant["id"]})
    menu_items = await db.menu_items.count_documents({"tenant_id": tenant["id"]})
    users = await db.users.count_documents({"tenant_id": tenant["id"]})
    
    steps = onboarding.get("steps", {})
    steps["2"]["completed"] = depts > 0
    steps["3"]["completed"] = rooms > 0 or tables > 0
    steps["4"]["completed"] = menu_items > 0 or not tenant.get("restaurant_enabled", False)
    steps["5"]["completed"] = tenant.get("loyalty_rules", {}).get("enabled", False) or True  # Optional step
    steps["6"]["completed"] = rooms > 0 or tables > 0
    steps["7"]["completed"] = users > 1
    
    completed_count = sum(1 for s in steps.values() if s.get("completed"))
    all_complete = completed_count >= 5  # At least 5 of 7 steps
    
    await db.onboarding.update_one(
        {"tenant_id": tenant["id"]},
        {"$set": {"steps": steps, "completed": all_complete, "current_step": min(7, completed_count + 1)}}
    )
    
    return {**serialize_doc(onboarding), "steps": steps, "completed": all_complete, "progress": round(completed_count / 7 * 100)}

@api_router.post("/tenants/{tenant_slug}/onboarding/complete")
async def complete_onboarding(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    await db.onboarding.update_one({"tenant_id": tenant["id"]}, {"$set": {"completed": True}})
    await db.tenants.update_one({"id": tenant["id"]}, {"$set": {"onboarding_completed": True}})
    return {"completed": True}

# ============ PHASE 5: ANALYTICS ============
@api_router.get("/tenants/{tenant_slug}/analytics")
async def get_analytics(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    return await compute_analytics(db, tenant["id"])

# ============ PHASE 5: GUEST INTELLIGENCE v2 ============
@api_router.get("/tenants/{tenant_slug}/contacts/{contact_id}/intelligence-v2")
async def get_intelligence_v2(tenant_slug: str, contact_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    contact = await db.contacts.find_one({"id": contact_id, "tenant_id": tenant["id"]}, {"_id": 0})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    phone = contact.get("phone", "")
    
    # Requests
    reqs = await db.guest_requests.find({"tenant_id": tenant["id"], "guest_phone": phone}, {"_id": 0}).to_list(500) if phone else []
    orders = await db.orders.find({"tenant_id": tenant["id"], "guest_phone": phone}, {"_id": 0}).to_list(500) if phone else []
    
    # Lifetime value
    order_total = sum(o.get("total", 0) for o in orders)
    res_list = await db.reservations.find({"tenant_id": tenant["id"], "guest_phone": phone}, {"_id": 0}).to_list(100) if phone else []
    res_total = sum(r.get("price", 0) for r in res_list)
    lifetime_value = order_total + res_total
    
    # Avg response time
    response_times = []
    for r in reqs:
        if r.get("first_response_at") and r.get("created_at"):
            try:
                created = datetime.fromisoformat(r["created_at"].replace('Z', '+00:00'))
                responded = datetime.fromisoformat(r["first_response_at"].replace('Z', '+00:00'))
                diff = (responded - created).total_seconds() / 60
                response_times.append(diff)
            except:
                pass
    avg_response_time = round(sum(response_times) / len(response_times), 1) if response_times else 0
    
    # Ratings
    ratings = [r["rating"] for r in reqs if r.get("rating")]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0
    
    # Satisfaction trend
    recent_ratings = ratings[-5:] if ratings else []
    older_ratings = ratings[:-5] if len(ratings) > 5 else []
    if recent_ratings and older_ratings:
        trend = "improving" if sum(recent_ratings)/len(recent_ratings) > sum(older_ratings)/len(older_ratings) else "declining"
    elif recent_ratings:
        trend = "stable"
    else:
        trend = "unknown"
    
    # Churn risk
    days_since_last = 999
    all_dates = [r.get("created_at", "") for r in reqs + orders]
    if all_dates:
        try:
            latest = max(all_dates)
            last_dt = datetime.fromisoformat(latest.replace('Z', '+00:00'))
            days_since_last = (now_utc() - last_dt).days
        except:
            pass
    
    if days_since_last > 90:
        churn_risk = "high"
    elif days_since_last > 30:
        churn_risk = "medium"
    else:
        churn_risk = "low"
    
    # Complaint analysis
    complaints = [r for r in reqs if r.get("priority") in ["high", "urgent"] or analyze_sentiment(r.get("description", "")) == "negative"]
    complaint_ratio = round(len(complaints) / max(len(reqs), 1), 2)
    
    # Service preferences
    categories = {}
    for r in reqs:
        cat = r.get("category", "other")
        categories[cat] = categories.get(cat, 0) + 1
    
    # Favorite items
    item_counts = {}
    for o in orders:
        for item in o.get("items", []):
            name = item.get("menu_item_name", "")
            item_counts[name] = item_counts.get(name, 0) + item.get("quantity", 1)
    
    # Loyalty
    loyalty_info = None
    if contact.get("loyalty_account_id"):
        account = await db.loyalty_accounts.find_one({"id": contact["loyalty_account_id"]}, {"_id": 0})
        if account:
            tier = compute_tier(account.get("points", 0))
            loyalty_info = {
                "points": account.get("points", 0),
                "tier": tier,
                "tier_info": LOYALTY_TIERS.get(tier, {}),
                "next_tier": next_tier_info(tier, account.get("points", 0))
            }
    
    # Alerts
    alerts = []
    if churn_risk == "high":
        alerts.append({"type": "danger", "message": "High churn risk - no activity in 90+ days"})
    if complaint_ratio > 0.3:
        alerts.append({"type": "warning", "message": f"High complaint ratio ({int(complaint_ratio*100)}%)"})
    if avg_rating > 0 and avg_rating < 3:
        alerts.append({"type": "warning", "message": f"Low satisfaction: {avg_rating}/5"})
    if lifetime_value > 5000:
        alerts.append({"type": "success", "message": f"High-value guest: {lifetime_value} TRY"})
    for r in complaints[-2:]:
        alerts.append({"type": "danger", "message": f"Complaint: {r.get('description', '')[:60]}"})
    
    return {
        "lifetime_value": lifetime_value,
        "avg_response_time_min": avg_response_time,
        "avg_rating": avg_rating,
        "satisfaction_trend": trend,
        "predicted_churn_risk": churn_risk,
        "complaint_ratio": complaint_ratio,
        "total_requests": len(reqs),
        "total_orders": len(orders),
        "total_reservations": len(res_list),
        "service_preferences": categories,
        "favorite_items": sorted(item_counts.items(), key=lambda x: -x[1])[:5],
        "loyalty": loyalty_info,
        "alerts": alerts,
        "days_since_last_activity": days_since_last
    }

# ============ PHASE 5: COMPLIANCE ============
@api_router.post("/tenants/{tenant_slug}/compliance/export/{contact_id}")
async def export_contact_data(tenant_slug: str, contact_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    bundle = await export_guest_data(db, tenant["id"], contact_id)
    if not bundle:
        raise HTTPException(status_code=404, detail="Contact not found")
    await _log_audit(tenant["id"], "data_export", "contact", contact_id)
    return bundle

@api_router.post("/tenants/{tenant_slug}/compliance/forget/{contact_id}")
async def forget_contact(tenant_slug: str, contact_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    result = await forget_guest(db, tenant["id"], contact_id)
    if not result:
        raise HTTPException(status_code=404, detail="Contact not found")
    await _log_audit(tenant["id"], "data_forget", "contact", contact_id)
    return result

@api_router.get("/tenants/{tenant_slug}/compliance/consent-logs")
async def list_consent_logs(tenant_slug: str, page: int = 1, limit: int = 50):
    tenant = await get_tenant_by_slug(tenant_slug)
    skip = (page - 1) * limit
    logs = await db.consent_logs.find({"tenant_id": tenant["id"]}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.consent_logs.count_documents({"tenant_id": tenant["id"]})
    return {"data": [serialize_doc(l) for l in logs], "total": total}

@api_router.get("/tenants/{tenant_slug}/compliance/retention")
async def get_retention_policy(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    policy = await db.retention_policies.find_one({"tenant_id": tenant["id"]}, {"_id": 0})
    if not policy:
        policy = {
            "id": new_id(), "tenant_id": tenant["id"],
            "retention_months": 24, "auto_purge": False,
            "created_at": now_utc().isoformat()
        }
        await db.retention_policies.insert_one(policy)
    return serialize_doc(policy)

@api_router.patch("/tenants/{tenant_slug}/compliance/retention")
async def update_retention_policy(tenant_slug: str, data: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    update = {}
    if "retention_months" in data:
        update["retention_months"] = data["retention_months"]
    if "auto_purge" in data:
        update["auto_purge"] = data["auto_purge"]
    update["updated_at"] = now_utc().isoformat()
    await db.retention_policies.update_one({"tenant_id": tenant["id"]}, {"$set": update}, upsert=True)
    return await get_retention_policy(tenant_slug)

# ============ PHASE 5: GROWTH & REFERRAL ============
@api_router.get("/tenants/{tenant_slug}/growth/referral")
async def get_referral(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    referral = await get_or_create_referral(db, tenant["id"], tenant_slug)
    return serialize_doc(referral)

@api_router.get("/r/{referral_code}")
async def referral_landing(referral_code: str):
    """Public referral landing page data"""
    referral = await db.referrals.find_one({"code": referral_code})
    if not referral:
        raise HTTPException(status_code=404, detail="Referral not found")
    await track_referral_click(db, referral_code)
    tenant = await db.tenants.find_one({"id": referral["tenant_id"]}, {"_id": 0})
    return {
        "referral_code": referral_code,
        "referrer": tenant.get("name", "") if tenant else "",
        "message": "Join OmniHub and get premium features!"
    }

@api_router.get("/tenants/{tenant_slug}/growth/stats")
async def get_growth_stats(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    referral = await get_or_create_referral(db, tenant["id"], tenant_slug)
    events = await db.referral_events.find({"referrer_tenant_id": tenant["id"]}, {"_id": 0}).to_list(100)
    return {
        "referral": serialize_doc(referral),
        "events": [serialize_doc(e) for e in events],
        "total_clicks": referral.get("clicks", 0),
        "total_signups": referral.get("signups", 0),
        "total_rewards": referral.get("rewards_earned", 0)
    }

# ============ PHASE 5: OBSERVABILITY ============
@api_router.get("/system/status")
async def system_status():
    try:
        await db.command("ping")
        db_status = "connected"
    except:
        db_status = "error"
    
    return {
        "status": "operational",
        "version": "2.0.0",
        "database": db_status,
        "timestamp": now_utc().isoformat(),
        "uptime": "running"
    }

@api_router.get("/system/metrics")
async def system_metrics():
    total_tenants = await db.tenants.count_documents({})
    total_users = await db.users.count_documents({})
    total_requests = await db.guest_requests.count_documents({})
    total_orders = await db.orders.count_documents({})
    total_conversations = await db.conversations.count_documents({})
    total_messages = await db.messages.count_documents({})
    total_reviews = await db.reviews.count_documents({})
    total_reservations = await db.reservations.count_documents({})
    
    # Revenue
    rev = await db.orders.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$total"}}}
    ]).to_list(1)
    total_revenue = rev[0]["total"] if rev else 0
    
    # AI usage
    ai_pipeline = await db.tenants.aggregate([
        {"$group": {"_id": None, "total": {"$sum": "$usage_counters.ai_replies_this_month"}}}
    ]).to_list(1)
    total_ai = ai_pipeline[0]["total"] if ai_pipeline else 0
    
    return {
        "tenants": total_tenants,
        "users": total_users,
        "requests_handled": total_requests,
        "orders_processed": total_orders,
        "conversations": total_conversations,
        "messages": total_messages,
        "reviews": total_reviews,
        "reservations": total_reservations,
        "total_revenue": total_revenue,
        "ai_replies_generated": total_ai,
        "mrr_stub": total_tenants * 99,
        "timestamp": now_utc().isoformat()
    }

# ============ PHASE 5: DEMO MODE ============
@api_router.post("/demo/reset")
async def reset_demo():
    """Reset demo tenant data for fresh demo"""
    collections = ["tenants", "users", "departments", "service_categories", "rooms",
                    "guest_requests", "tables", "menu_categories", "menu_items",
                    "orders", "contacts", "conversations", "messages",
                    "loyalty_accounts", "loyalty_ledger", "reviews", "review_replies",
                    "offers", "payment_links", "reservations", "connector_credentials",
                    "audit_logs", "sessions", "billing_accounts", "subscriptions", "invoices",
                    "onboarding", "referrals", "referral_events", "consent_logs", "retention_policies"]
    for col in collections:
        await db[col].delete_many({})
    
    # Re-seed
    return await seed_data()


# ============ GUEST TOKEN RESOLVE ENDPOINTS ============
from fastapi.responses import Response

@api_router.get("/guest/resolve-room")
async def resolve_room(tenantSlug: str, roomCode: str, request: Request = None):
    """Resolve room by tenant slug + room code, issue guest token.
    Validates: room exists, is_active, QR version valid.
    Rate limited: max 10 resolves per IP per minute.
    """
    # Rate limit (Pilot Fix 4: guest spam protection)
    client_ip = request.client.host if request else "unknown"
    rate_key = f"guest_resolve:{client_ip}"
    if rate_limiter.is_rate_limited(rate_key, max_requests=10, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait.")
    
    tenant = await get_tenant_by_slug(tenantSlug)
    room = await db.rooms.find_one({"tenant_id": tenant["id"], "room_code": roomCode}, {"_id": 0})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found or QR code invalid")
    
    # Pilot Fix 3: QR version validation - inactive rooms reject
    room_doc = serialize_doc(room)
    if not room_doc.get("is_active", True):
        raise HTTPException(status_code=410, detail="This QR code has been deactivated")
    
    categories = await db.service_categories.find({"tenant_id": tenant["id"]}, {"_id": 0}).to_list(50)
    
    guest_token = create_guest_token(
        tenant_id=tenant["id"],
        room_id=room_doc["id"],
        room_code=roomCode
    )
    
    return {
        "guestToken": guest_token,
        "tenant": {"name": tenant["name"], "slug": tenant["slug"]},
        "room": room_doc,
        "serviceCategories": [serialize_doc(c) for c in categories],
        "loyaltyEnabled": tenant.get("loyalty_rules", {}).get("enabled", False)
    }

@api_router.get("/guest/resolve-table")
async def resolve_table(tenantSlug: str, tableCode: str, request: Request = None):
    """Resolve table with QR validation + rate limiting"""
    client_ip = request.client.host if request else "unknown"
    rate_key = f"guest_resolve:{client_ip}"
    if rate_limiter.is_rate_limited(rate_key, max_requests=10, window_seconds=60):
        raise HTTPException(status_code=429, detail="Too many requests. Please wait.")
    
    tenant = await get_tenant_by_slug(tenantSlug)
    table = await db.tables.find_one({"tenant_id": tenant["id"], "table_code": tableCode}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Table not found or QR code invalid")
    
    table_doc = serialize_doc(table)
    if not table_doc.get("is_active", True):
        raise HTTPException(status_code=410, detail="This QR code has been deactivated")
    categories = await db.menu_categories.find({"tenant_id": tenant["id"]}, {"_id": 0}).sort("sort_order", 1).to_list(50)
    items = await db.menu_items.find({"tenant_id": tenant["id"], "available": True}, {"_id": 0}).to_list(500)
    
    guest_token = create_guest_token(
        tenant_id=tenant["id"],
        table_id=table_doc["id"],
        table_code=tableCode
    )
    
    return {
        "guestToken": guest_token,
        "tenant": {"name": tenant["name"], "slug": tenant["slug"]},
        "table": table_doc,
        "menuCategories": [serialize_doc(c) for c in categories],
        "menuItems": [serialize_doc(i) for i in items],
        "loyaltyEnabled": tenant.get("loyalty_rules", {}).get("enabled", False)
    }

@api_router.post("/guest/join-loyalty")
async def guest_join_loyalty(data: dict):
    """Guest joins loyalty via guest token"""
    guest_token = data.get("guestToken", "")
    try:
        payload = decode_guest_token(guest_token)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=str(e))
    
    tenant_id = payload["tenant_id"]
    phone = data.get("phone", "")
    email = data.get("email", "")
    name = data.get("name", "")
    
    if not phone and not email:
        raise HTTPException(status_code=400, detail="Phone or email required")
    
    contact = await _upsert_contact(tenant_id, name, phone, email)
    
    # Check existing loyalty
    existing = await db.loyalty_accounts.find_one({"tenant_id": tenant_id, "contact_id": contact["id"]})
    if existing:
        # Reissue token with contact_id
        new_token = create_guest_token(
            tenant_id=tenant_id,
            room_id=payload.get("room_id"),
            table_id=payload.get("table_id"),
            room_code=payload.get("room_code"),
            table_code=payload.get("table_code"),
            contact_id=contact["id"]
        )
        return {"guestToken": new_token, "loyalty": serialize_doc(existing), "otpStub": "123456"}
    
    account = {
        "id": new_id(),
        "tenant_id": tenant_id,
        "contact_id": contact["id"],
        "points": 0,
        "tier": "bronze",
        "created_at": now_utc().isoformat()
    }
    await db.loyalty_accounts.insert_one(account)
    await db.contacts.update_one({"id": contact["id"]}, {"$set": {"loyalty_account_id": account["id"]}})
    
    new_token = create_guest_token(
        tenant_id=tenant_id,
        room_id=payload.get("room_id"),
        table_id=payload.get("table_id"),
        room_code=payload.get("room_code"),
        table_code=payload.get("table_code"),
        contact_id=contact["id"]
    )
    return {"guestToken": new_token, "loyalty": serialize_doc(account), "otpStub": "123456"}

# ============ QR CODE ENDPOINTS ============
@api_router.get("/admin/rooms/{room_id}/qr.png")
async def get_room_qr_png(room_id: str):
    """Generate QR PNG for a room"""
    room = await db.rooms.find_one({"id": room_id}, {"_id": 0})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    tenant = await db.tenants.find_one({"id": room["tenant_id"]}, {"_id": 0})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    
    public_url = os.environ.get("PUBLIC_BASE_URL", "https://omni-inbox-hub.preview.emergentagent.com")
    qr_url = f"{public_url}/g/{tenant['slug']}/room/{room['room_code']}"
    png_bytes = generate_qr_png(qr_url)
    
    return Response(content=png_bytes, media_type="image/png", 
                    headers={"Content-Disposition": f"inline; filename=room-{room['room_number']}-qr.png"})

@api_router.get("/admin/rooms/print.pdf")
async def get_rooms_print_pdf(ids: str = ""):
    """Generate printable PDF with QR codes for multiple rooms"""
    room_ids = [rid.strip() for rid in ids.split(",") if rid.strip()]
    if not room_ids:
        raise HTTPException(status_code=400, detail="No room IDs provided")
    
    rooms = await db.rooms.find({"id": {"$in": room_ids}}, {"_id": 0}).to_list(100)
    if not rooms:
        raise HTTPException(status_code=404, detail="No rooms found")
    
    tenant = await db.tenants.find_one({"id": rooms[0]["tenant_id"]}, {"_id": 0})
    public_url = os.environ.get("PUBLIC_BASE_URL", "https://omni-inbox-hub.preview.emergentagent.com")
    
    items = [{
        "label": f"Room {r['room_number']}",
        "url": f"{public_url}/g/{tenant['slug']}/room/{r['room_code']}"
    } for r in rooms]
    
    pdf_bytes = generate_qr_print_pdf(items, title=f"{tenant['name']} - Room QR Codes")
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=room-qr-codes.pdf"})

@api_router.get("/admin/tables/{table_id}/qr.png")
async def get_table_qr_png(table_id: str):
    """Generate QR PNG for a table"""
    table = await db.tables.find_one({"id": table_id}, {"_id": 0})
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")
    
    tenant = await db.tenants.find_one({"id": table["tenant_id"]}, {"_id": 0})
    public_url = os.environ.get("PUBLIC_BASE_URL", "https://omni-inbox-hub.preview.emergentagent.com")
    qr_url = f"{public_url}/g/{tenant['slug']}/table/{table['table_code']}"
    png_bytes = generate_qr_png(qr_url)
    
    return Response(content=png_bytes, media_type="image/png",
                    headers={"Content-Disposition": f"inline; filename=table-{table['table_number']}-qr.png"})

@api_router.get("/admin/tables/print.pdf")
async def get_tables_print_pdf(ids: str = ""):
    """Generate printable PDF with QR codes for multiple tables"""
    table_ids = [tid.strip() for tid in ids.split(",") if tid.strip()]
    if not table_ids:
        raise HTTPException(status_code=400, detail="No table IDs provided")
    
    tables = await db.tables.find({"id": {"$in": table_ids}}, {"_id": 0}).to_list(100)
    if not tables:
        raise HTTPException(status_code=404, detail="No tables found")
    
    tenant = await db.tenants.find_one({"id": tables[0]["tenant_id"]}, {"_id": 0})
    public_url = os.environ.get("PUBLIC_BASE_URL", "https://omni-inbox-hub.preview.emergentagent.com")
    
    items = [{
        "label": f"Table {t['table_number']}",
        "url": f"{public_url}/g/{tenant['slug']}/table/{t['table_code']}"
    } for t in tables]
    
    pdf_bytes = generate_qr_print_pdf(items, title=f"{tenant['name']} - Table QR Codes")
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": "attachment; filename=table-qr-codes.pdf"})

# ============ REQUEST COMMENTS ============
@api_router.post("/tenants/{tenant_slug}/requests/{request_id}/comments")
async def add_request_comment(tenant_slug: str, request_id: str, data: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    req = await db.guest_requests.find_one({"id": request_id, "tenant_id": tenant["id"]})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    
    comment = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "request_id": request_id,
        "body": data.get("body", ""),
        "created_by_user_id": data.get("user_id", ""),
        "created_by_name": data.get("user_name", ""),
        "created_at": now_utc().isoformat()
    }
    await db.request_comments.insert_one(comment)
    return serialize_doc(comment)

@api_router.get("/tenants/{tenant_slug}/requests/{request_id}/comments")
async def list_request_comments(tenant_slug: str, request_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    comments = await db.request_comments.find(
        {"tenant_id": tenant["id"], "request_id": request_id}, {"_id": 0}
    ).sort("created_at", 1).to_list(100)
    return [serialize_doc(c) for c in comments]

# ============ KB ARTICLES ============
@api_router.get("/tenants/{tenant_slug}/kb-articles")
async def list_kb_articles(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    articles = await db.kb_articles.find({"tenant_id": tenant["id"]}, {"_id": 0}).to_list(100)
    return [serialize_doc(a) for a in articles]

@api_router.post("/tenants/{tenant_slug}/kb-articles")
async def create_kb_article(tenant_slug: str, data: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    article = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "title": data.get("title", ""),
        "content": data.get("content", ""),
        "tags": data.get("tags", []),
        "created_at": now_utc().isoformat()
    }
    await db.kb_articles.insert_one(article)
    return serialize_doc(article)


# ============ PHASE 5: DB INDEXES ============
@app.on_event("startup")
async def create_indexes():
    """Create MongoDB indexes for performance"""
    try:
        await db.tenants.create_index("slug", unique=True)
        await db.tenants.create_index("id", unique=True)
        await db.users.create_index([("email", 1)], unique=True)
        await db.users.create_index([("tenant_id", 1)])
        await db.departments.create_index([("tenant_id", 1)])
        await db.rooms.create_index([("tenant_id", 1), ("room_code", 1)])
        await db.tables.create_index([("tenant_id", 1), ("table_code", 1)])
        await db.guest_requests.create_index([("tenant_id", 1), ("status", 1)])
        await db.guest_requests.create_index([("tenant_id", 1), ("department_code", 1)])
        await db.guest_requests.create_index([("tenant_id", 1), ("guest_phone", 1)])
        await db.orders.create_index([("tenant_id", 1), ("status", 1)])
        await db.orders.create_index([("tenant_id", 1), ("table_code", 1)])
        await db.contacts.create_index([("tenant_id", 1), ("phone", 1)])
        await db.contacts.create_index([("tenant_id", 1), ("email", 1)])
        await db.conversations.create_index([("tenant_id", 1)])
        await db.messages.create_index([("tenant_id", 1), ("conversation_id", 1)])
        await db.reviews.create_index([("tenant_id", 1), ("source", 1)])
        await db.loyalty_accounts.create_index([("tenant_id", 1), ("contact_id", 1)])
        await db.audit_logs.create_index([("tenant_id", 1), ("created_at", -1)])
        await db.sessions.create_index([("user_id", 1), ("is_active", 1)])
        await db.request_comments.create_index([("tenant_id", 1), ("request_id", 1)])
        await db.kb_articles.create_index([("tenant_id", 1)])
        await db.connector_credentials.create_index([("tenant_id", 1), ("connector_type", 1)])
        # Sprint 3 indexes
        await db.conversations.create_index([("tenant_id", 1), ("last_message_at", -1)])
        await db.conversations.create_index([("tenant_id", 1), ("contact_id", 1)])
        await db.messages.create_index([("tenant_id", 1), ("conversation_id", 1), ("created_at", 1)])
        await db.reviews.create_index([("tenant_id", 1), ("source_type", 1)])
        await db.reviews.create_index([("tenant_id", 1), ("sentiment", 1)])
        await db.review_replies.create_index([("tenant_id", 1), ("review_id", 1)])
        await db.usage_counters.create_index([("tenant_id", 1), ("month_key", 1)])
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.warning(f"Index creation: {e}")

# Start connector polling background task
@app.on_event("startup")
async def start_polling():
    polling_task = ConnectorPollingTask(db)
    asyncio.create_task(polling_task.start())

# ============ WEBSOCKET ENDPOINT ============
@app.websocket("/ws/{tenant_id}")
async def websocket_endpoint(websocket: WebSocket, tenant_id: str):
    channel = f"tenant:{tenant_id}"
    await ws_manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket, channel)

@api_router.get("/tenants/{tenant_slug}/reviews")
async def list_reviews(tenant_slug: str, source: Optional[str] = None, page: int = 1, limit: int = 20):
    tenant = await get_tenant_by_slug(tenant_slug)
    query = {"tenant_id": tenant["id"]}
    if source:
        query["source"] = source.upper()
    skip = (page - 1) * limit
    reviews = await db.reviews.find(query, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.reviews.count_documents(query)
    return {"data": [serialize_doc(r) for r in reviews], "total": total, "page": page}

@api_router.post("/tenants/{tenant_slug}/reviews/{review_id}/reply")
async def reply_to_review(tenant_slug: str, review_id: str, data: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    review = await db.reviews.find_one({"id": review_id, "tenant_id": tenant["id"]})
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    reply = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "review_id": review_id,
        "content": data.get("content", ""),
        "author": data.get("author", "Management"),
        "status": "draft",  # draft, published (stub)
        "created_at": now_utc().isoformat()
    }
    await db.review_replies.insert_one(reply)
    await db.reviews.update_one({"id": review_id}, {"$set": {"replied": True, "reply_id": reply["id"], "updated_at": now_utc().isoformat()}})
    return serialize_doc(reply)

@api_router.post("/tenants/{tenant_slug}/reviews/seed-stubs")
async def seed_stub_reviews(tenant_slug: str):
    """Seed fake reviews from connector stubs"""
    tenant = await get_tenant_by_slug(tenant_slug)
    existing = await db.reviews.count_documents({"tenant_id": tenant["id"]})
    if existing > 0:
        return {"message": "Reviews already exist", "count": existing}
    
    reviews = []
    for i, fr in enumerate(FAKE_REVIEWS):
        reviews.append({
            "id": new_id(),
            "tenant_id": tenant["id"],
            "source": fr["source"],
            "author": fr["author"],
            "rating": fr["rating"],
            "text": fr["text"],
            "language": fr["language"],
            "sentiment": analyze_sentiment(fr["text"]),
            "replied": False,
            "reply_id": None,
            "created_at": (now_utc() - timedelta(days=random.randint(1, 30))).isoformat(),
            "updated_at": now_utc().isoformat()
        })
    await db.reviews.insert_many(reviews)
    return {"message": f"Seeded {len(reviews)} reviews", "count": len(reviews)}

# ============ CONNECTOR FRAMEWORK ============
@api_router.get("/tenants/{tenant_slug}/connectors")
async def list_connectors(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    # Get configured connectors
    credentials = await db.connector_credentials.find({"tenant_id": tenant["id"]}, {"_id": 0}).to_list(20)
    cred_map = {c["connector_type"]: c for c in credentials}
    
    result = []
    for ct in CONNECTOR_TYPES:
        cred = cred_map.get(ct["type"])
        result.append({
            **ct,
            "configured": cred is not None,
            "enabled": cred.get("enabled", False) if cred else False,
            "credential_id": cred.get("id") if cred else None,
        })
    return result

@api_router.post("/tenants/{tenant_slug}/connectors")
async def configure_connector(tenant_slug: str, data: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    connector_type = data.get("connector_type", "").upper()
    
    existing = await db.connector_credentials.find_one({
        "tenant_id": tenant["id"], "connector_type": connector_type
    })
    
    if existing:
        await db.connector_credentials.update_one(
            {"id": existing["id"]},
            {"$set": {"credentials_json": data.get("credentials", {}), "enabled": data.get("enabled", True), "updated_at": now_utc().isoformat()}}
        )
        updated = await db.connector_credentials.find_one({"id": existing["id"]}, {"_id": 0})
        return serialize_doc(updated)
    
    cred = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "connector_type": connector_type,
        "credentials_json": data.get("credentials", {}),
        "enabled": data.get("enabled", True),
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat()
    }
    await db.connector_credentials.insert_one(cred)
    return serialize_doc(cred)

# ============ OFFERS + MOCK PAYMENTS ============
@api_router.post("/tenants/{tenant_slug}/offers")
async def create_offer(tenant_slug: str, data: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    
    offer = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "guest_name": data.get("guest_name", ""),
        "guest_email": data.get("guest_email", ""),
        "guest_phone": data.get("guest_phone", ""),
        "room_type": data.get("room_type", "standard"),
        "check_in": data.get("check_in", ""),
        "check_out": data.get("check_out", ""),
        "price": data.get("price", 0),
        "currency": data.get("currency", "TRY"),
        "inclusions": data.get("inclusions", []),
        "notes": data.get("notes", ""),
        "status": "draft",  # draft, sent, accepted, expired
        "payment_link_id": None,
        "reservation_id": None,
        "created_by": data.get("created_by", ""),
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat()
    }
    await db.offers.insert_one(offer)
    
    # Log audit
    await _log_audit(tenant["id"], "offer_created", "offer", offer["id"], data.get("created_by", ""))
    
    return serialize_doc(offer)

@api_router.get("/tenants/{tenant_slug}/offers")
async def list_offers(tenant_slug: str, status: Optional[str] = None):
    tenant = await get_tenant_by_slug(tenant_slug)
    query = {"tenant_id": tenant["id"]}
    if status:
        query["status"] = status
    offers = await db.offers.find(query, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [serialize_doc(o) for o in offers]

@api_router.post("/tenants/{tenant_slug}/offers/{offer_id}/generate-payment-link")
async def generate_payment_link(tenant_slug: str, offer_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    offer = await db.offers.find_one({"id": offer_id, "tenant_id": tenant["id"]})
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    
    payment_data = StripeStubProvider.create_payment_link(
        amount=offer["price"],
        currency=offer.get("currency", "TRY"),
        description=f"Reservation: {offer['room_type']} {offer.get('check_in','')} - {offer.get('check_out','')}"
    )
    
    payment_link = {
        **payment_data,
        "tenant_id": tenant["id"],
        "offer_id": offer_id,
    }
    await db.payment_links.insert_one(payment_link)
    await db.offers.update_one({"id": offer_id}, {"$set": {"payment_link_id": payment_data["id"], "status": "sent", "updated_at": now_utc().isoformat()}})
    
    return serialize_doc(payment_link)

@api_router.post("/payments/mock/succeed/{link_id}")
async def mock_payment_success(link_id: str):
    """Simulate payment success"""
    link = await db.payment_links.find_one({"id": link_id})
    if not link:
        raise HTTPException(status_code=404, detail="Payment link not found")
    
    # Update payment link
    await db.payment_links.update_one({"id": link_id}, {"$set": {"status": "succeeded", "paid_at": now_utc().isoformat()}})
    
    # Find offer
    offer = await db.offers.find_one({"id": link.get("offer_id")})
    if offer:
        # Create reservation
        reservation = {
            "id": new_id(),
            "tenant_id": link["tenant_id"],
            "offer_id": offer["id"],
            "payment_link_id": link_id,
            "guest_name": offer.get("guest_name", ""),
            "guest_email": offer.get("guest_email", ""),
            "guest_phone": offer.get("guest_phone", ""),
            "room_type": offer.get("room_type", ""),
            "check_in": offer.get("check_in", ""),
            "check_out": offer.get("check_out", ""),
            "price": offer.get("price", 0),
            "currency": offer.get("currency", "TRY"),
            "status": "confirmed",
            "created_at": now_utc().isoformat()
        }
        await db.reservations.insert_one(reservation)
        await db.offers.update_one({"id": offer["id"]}, {"$set": {"status": "accepted", "reservation_id": reservation["id"], "updated_at": now_utc().isoformat()}})
        
        # Broadcast
        await ws_manager.broadcast_tenant(link["tenant_id"], "reservation", "reservation", "created", serialize_doc(reservation))
        
        return {"payment": "succeeded", "reservation": serialize_doc(reservation)}
    
    return {"payment": "succeeded", "reservation": None}

@api_router.get("/tenants/{tenant_slug}/reservations")
async def list_reservations(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    reservations = await db.reservations.find({"tenant_id": tenant["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [serialize_doc(r) for r in reservations]

# ============ GUEST INTELLIGENCE (CRM) ============
@api_router.get("/tenants/{tenant_slug}/contacts/{contact_id}/intelligence")
async def get_contact_intelligence(tenant_slug: str, contact_id: str):
    """Compute and return guest intelligence data"""
    tenant = await get_tenant_by_slug(tenant_slug)
    contact = await db.contacts.find_one({"id": contact_id, "tenant_id": tenant["id"]}, {"_id": 0})
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    
    phone = contact.get("phone", "")
    email = contact.get("email", "")
    
    # Compute metrics
    req_query = {"tenant_id": tenant["id"]}
    if phone:
        req_query["guest_phone"] = phone
    
    requests_list = await db.guest_requests.find(req_query, {"_id": 0}).to_list(500)
    orders_list = await db.orders.find({"tenant_id": tenant["id"], "guest_phone": phone}, {"_id": 0}).to_list(500) if phone else []
    
    visit_count = len(set([r.get("room_code", "") for r in requests_list])) + len(set([o.get("table_code", "") for o in orders_list]))
    
    ratings = [r["rating"] for r in requests_list if r.get("rating")]
    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else 0
    
    total_spend = sum(o.get("total", 0) for o in orders_list)
    
    complaints = [r for r in requests_list if r.get("priority") in ["high", "urgent"] or analyze_sentiment(r.get("description", "")) == "negative"]
    complaint_ratio = round(len(complaints) / max(len(requests_list), 1), 2)
    
    # Last sentiment
    all_texts = [r.get("description", "") for r in requests_list] + [r.get("rating_comment", "") for r in requests_list if r.get("rating_comment")]
    last_sentiment = analyze_sentiment(all_texts[-1]) if all_texts else "neutral"
    
    # Preferred room type
    room_types = [r.get("room_code", "")[:1] for r in requests_list if r.get("room_code")]
    
    # Favorite menu items
    item_counts = {}
    for o in orders_list:
        for item in o.get("items", []):
            name = item.get("menu_item_name", "")
            item_counts[name] = item_counts.get(name, 0) + item.get("quantity", 1)
    favorite_items = sorted(item_counts.items(), key=lambda x: -x[1])[:5]
    
    # Alerts
    alerts = []
    if complaint_ratio > 0.3:
        alerts.append({"type": "warning", "message": f"High complaint ratio ({int(complaint_ratio*100)}%)"})
    for r in requests_list[-3:]:
        if r.get("priority") in ["high", "urgent"] and r.get("status") in ["OPEN", "IN_PROGRESS"]:
            alerts.append({"type": "urgent", "message": f"Active {r['priority']} request: {r['description'][:50]}"})
    if avg_rating > 0 and avg_rating < 3:
        alerts.append({"type": "warning", "message": f"Low average rating: {avg_rating}/5"})
    
    # Loyalty
    loyalty_info = None
    if contact.get("loyalty_account_id"):
        account = await db.loyalty_accounts.find_one({"id": contact["loyalty_account_id"]}, {"_id": 0})
        if account:
            tier = compute_tier(account.get("points", 0))
            loyalty_info = {
                "points": account.get("points", 0),
                "tier": tier,
                "tier_info": LOYALTY_TIERS.get(tier, {}),
                "next_tier": next_tier_info(tier, account.get("points", 0))
            }
    
    intelligence = {
        "visit_count": visit_count,
        "avg_rating": avg_rating,
        "total_spend": total_spend,
        "complaint_ratio": complaint_ratio,
        "last_sentiment": last_sentiment,
        "preferred_language": contact.get("preferred_language", "en"),
        "favorite_menu_items": [{"name": n, "count": c} for n, c in favorite_items],
        "total_requests": len(requests_list),
        "total_orders": len(orders_list),
        "alerts": alerts,
        "loyalty": loyalty_info
    }
    
    # Update contact with computed fields
    await db.contacts.update_one({"id": contact_id}, {"$set": {
        "intelligence": intelligence,
        "updated_at": now_utc().isoformat()
    }})
    
    return intelligence

# ============ AUDIT LOG ============
async def _log_audit(tenant_id: str, action: str, entity_type: str, entity_id: str, user_id: str = "", details: dict = None):
    entry = {
        "id": new_id(),
        "tenant_id": tenant_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "user_id": user_id,
        "details": details or {},
        "created_at": now_utc().isoformat()
    }
    await db.audit_logs.insert_one(entry)

@api_router.get("/tenants/{tenant_slug}/audit-logs")
async def list_audit_logs(tenant_slug: str, page: int = 1, limit: int = 50):
    tenant = await get_tenant_by_slug(tenant_slug)
    skip = (page - 1) * limit
    logs = await db.audit_logs.find({"tenant_id": tenant["id"]}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    total = await db.audit_logs.count_documents({"tenant_id": tenant["id"]})
    return {"data": [serialize_doc(l) for l in logs], "total": total, "page": page}

# ============ ENHANCED DASHBOARD STATS ============
@api_router.get("/tenants/{tenant_slug}/stats/enhanced")
async def get_enhanced_stats(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    tid = tenant["id"]
    
    # Basic stats
    total_requests = await db.guest_requests.count_documents({"tenant_id": tid})
    open_requests = await db.guest_requests.count_documents({"tenant_id": tid, "status": "OPEN"})
    in_progress = await db.guest_requests.count_documents({"tenant_id": tid, "status": "IN_PROGRESS"})
    done = await db.guest_requests.count_documents({"tenant_id": tid, "status": {"$in": ["DONE", "CLOSED"]}})
    
    total_orders = await db.orders.count_documents({"tenant_id": tid})
    active_orders = await db.orders.count_documents({"tenant_id": tid, "status": {"$in": ["RECEIVED", "PREPARING"]}})
    
    total_contacts = await db.contacts.count_documents({"tenant_id": tid})
    total_conversations = await db.conversations.count_documents({"tenant_id": tid})
    rooms_count = await db.rooms.count_documents({"tenant_id": tid})
    tables_count = await db.tables.count_documents({"tenant_id": tid})
    
    # Revenue (from orders)
    revenue_pipeline = [
        {"$match": {"tenant_id": tid, "order_type": "dine_in"}},
        {"$group": {"_id": None, "total_revenue": {"$sum": "$total"}, "order_count": {"$sum": 1}}}
    ]
    rev_result = await db.orders.aggregate(revenue_pipeline).to_list(1)
    total_revenue = rev_result[0]["total_revenue"] if rev_result else 0
    
    # Avg rating
    rating_pipeline = [
        {"$match": {"tenant_id": tid, "rating": {"$ne": None}}},
        {"$group": {"_id": None, "avg_rating": {"$avg": "$rating"}, "count": {"$sum": 1}}}
    ]
    rating_result = await db.guest_requests.aggregate(rating_pipeline).to_list(1)
    avg_rating = round(rating_result[0]["avg_rating"], 1) if rating_result else 0
    rating_count = rating_result[0]["count"] if rating_result else 0
    
    # Reviews stats
    total_reviews = await db.reviews.count_documents({"tenant_id": tid})
    review_sentiment = {
        "positive": await db.reviews.count_documents({"tenant_id": tid, "sentiment": "positive"}),
        "neutral": await db.reviews.count_documents({"tenant_id": tid, "sentiment": "neutral"}),
        "negative": await db.reviews.count_documents({"tenant_id": tid, "sentiment": "negative"}),
    }
    
    # Loyalty stats
    loyalty_members = await db.loyalty_accounts.count_documents({"tenant_id": tid})
    points_pipeline = [
        {"$match": {"tenant_id": tid, "type": "earn"}},
        {"$group": {"_id": None, "total_points": {"$sum": "$points"}}}
    ]
    points_result = await db.loyalty_ledger.aggregate(points_pipeline).to_list(1)
    total_points = points_result[0]["total_points"] if points_result else 0
    
    # Offers/Reservations
    total_offers = await db.offers.count_documents({"tenant_id": tid})
    total_reservations = await db.reservations.count_documents({"tenant_id": tid})
    
    return {
        "requests": {"total": total_requests, "open": open_requests, "in_progress": in_progress, "done": done},
        "orders": {"total": total_orders, "active": active_orders},
        "contacts": total_contacts,
        "conversations": total_conversations,
        "rooms": rooms_count,
        "tables": tables_count,
        "avg_rating": avg_rating,
        "rating_count": rating_count,
        "revenue": {"total": total_revenue, "currency": "TRY"},
        "reviews": {"total": total_reviews, "sentiment": review_sentiment},
        "loyalty": {"members": loyalty_members, "total_points_issued": total_points},
        "offers": total_offers,
        "reservations": total_reservations,
        "usage": tenant.get("usage_counters", {}),
        "limits": tenant.get("plan_limits", {})
    }

# ============ WEBSOCKET ENDPOINT ============
@app.websocket("/ws/{tenant_id}")
async def websocket_endpoint(websocket: WebSocket, tenant_id: str):
    channel = f"tenant:{tenant_id}"
    await ws_manager.connect(websocket, channel)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket, channel)

# Include routers (v1 legacy + v2 modular)
app.include_router(api_router)

# V2 modular routers (refactored architecture)
try:
    from routers.hotel import router as hotel_v2_router
    app.include_router(hotel_v2_router)
    logger.info("V2 hotel router loaded")
except Exception as e:
    logger.warning(f"V2 hotel router not loaded: {e}")

try:
    from routers.restaurant import router as restaurant_v2_router
    app.include_router(restaurant_v2_router)
    logger.info("V2 restaurant router loaded")
except Exception as e:
    logger.warning(f"V2 restaurant router not loaded: {e}")

try:
    from routers.inbox import router as inbox_v2_router
    app.include_router(inbox_v2_router)
    logger.info("V2 inbox router loaded")
except Exception as e:
    logger.warning(f"V2 inbox router not loaded: {e}")

try:
    from routers.reviews import router as reviews_v2_router
    app.include_router(reviews_v2_router)
    logger.info("V2 reviews router loaded")
except Exception as e:
    logger.warning(f"V2 reviews router not loaded: {e}")

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
