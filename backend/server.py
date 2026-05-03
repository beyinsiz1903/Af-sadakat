from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Query, Request
from fastapi.responses import Response
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
import random
import hashlib

# Add backend dir to path for local imports
sys.path.insert(0, str(Path(__file__).parent))
from rbac import ROLES, has_permission, get_accessible_modules, LOYALTY_TIERS, compute_tier, next_tier_info, analyze_sentiment, CONNECTOR_TYPES, FAKE_REVIEWS
from connectors_legacy import get_connector, StripeStubProvider
from security import rate_limiter, brute_force, create_session_doc, encrypt_field, decrypt_field, mask_email, mask_phone, PLAN_LIMITS, get_plan_limits, check_limit, token_family_manager, csrf_protection
from billing import create_billing_account, create_subscription, create_invoice, generate_mock_invoices, usage_meter, handle_stripe_webhook, UsageMeter, create_payment_method
from analytics_engine import compute_analytics, compute_revenue_analytics, compute_staff_performance, compute_investor_metrics
from compliance import export_guest_data, forget_guest, log_consent, retention_auto_cleanup
from referral import get_or_create_referral, track_referral_click, track_referral_signup, generate_referral_code, get_referral_landing_data
from guest_system import create_guest_token, decode_guest_token, generate_qr_png, generate_qr_print_pdf, encrypt_credentials, decrypt_credentials, ConnectorPollingTask

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'omni_inbox_hub')]

# Create the main app
app = FastAPI(title="Omni Inbox Hub API", version="6.0.0")
api_router = APIRouter(prefix="/api")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# App startup time for uptime tracking

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

# ============ WEBSOCKET MANAGER (extracted to core/legacy_helpers) ============
from core.legacy_helpers import (
    ws_manager, ConnectionManager,
    get_tenant_by_slug, get_tenant_by_id,
    upsert_contact as _upsert_contact,
    award_loyalty_points as _award_loyalty_points,
)

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

# ============ TENANT ISOLATION (imported above from core/legacy_helpers) ============

# ============ ROOT ============
@api_router.get("/")
async def root():
    return {"message": "Omni Inbox Hub API", "version": "0.1.0"}


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



# ============ WEBCHAT/CONVERSATION + AI SUGGEST — extracted to routers/guest_chat.py ============


# ============ LOYALTY ROUTES — extracted to routers/guest_loyalty.py ============

# ============ DASHBOARD STATS — extracted to routers/dashboard_stats.py ============


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
        "loyalty_enabled": tenant.get("loyalty_rules", {}).get("enabled", False),
        "current_guest_name": room.get("current_guest_name", ""),
        "current_guest_check_in": room.get("current_guest_check_in", ""),
        "current_guest_check_out": room.get("current_guest_check_out", ""),
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
    
    public_url = os.environ.get("PUBLIC_BASE_URL", "https://kritik-billing.preview.emergentagent.com")
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
    public_url = os.environ.get("PUBLIC_BASE_URL", "https://kritik-billing.preview.emergentagent.com")
    
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
    public_url = os.environ.get("PUBLIC_BASE_URL", "https://kritik-billing.preview.emergentagent.com")
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
    public_url = os.environ.get("PUBLIC_BASE_URL", "https://kritik-billing.preview.emergentagent.com")
    
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
        # Sprint 4 indexes
        await db.contact_events.create_index([("tenant_id", 1), ("contact_id", 1), ("created_at", -1)])
        await db.loyalty_rules.create_index([("tenant_id", 1)], unique=True)
        await db.loyalty_ledger.create_index([("tenant_id", 1), ("contact_id", 1), ("created_at", -1)])
        # Sprint 5 indexes
        await db.properties.create_index([("tenant_id", 1), ("slug", 1)], unique=True)
        await db.properties.create_index([("tenant_id", 1), ("is_active", 1)])
        await db.offers.create_index([("tenant_id", 1), ("property_id", 1), ("created_at", -1)])
        await db.offers.create_index([("tenant_id", 1), ("status", 1)])
        await db.payment_links.create_index([("tenant_id", 1), ("idempotency_key", 1)], unique=True, sparse=True)
        await db.payments.create_index([("tenant_id", 1), ("offer_id", 1)])
        await db.reservations.create_index([("tenant_id", 1), ("confirmation_code", 1)], unique=True, sparse=True)
        await db.reservations.create_index([("tenant_id", 1), ("property_id", 1), ("created_at", -1)])

        # Sprint 7: AI Sales indexes
        await db.room_rates.create_index([("tenant_id", 1), ("property_id", 1), ("room_type_code", 1)], unique=True)
        await db.discount_rules.create_index([("tenant_id", 1), ("property_id", 1)], unique=True)
        await db.business_policies.create_index([("tenant_id", 1), ("property_id", 1)], unique=True)
        await db.ai_sales_settings.create_index([("tenant_id", 1), ("property_id", 1)], unique=True)
        await db.ai_sales_sessions.create_index([("tenant_id", 1), ("conversation_id", 1)], unique=True)

        # Meta integration indexes
        await db.meta_assets.create_index([("tenant_id", 1), ("asset_type", 1), ("meta_id", 1)], unique=True)
        await db.messages.create_index([("external_id", 1)], unique=True, sparse=True)
        await db.reviews.create_index([("external_id", 1)], unique=True, sparse=True)
        await db.conversations.create_index([("tenant_id", 1), ("external.provider", 1), ("external.contact_id", 1), ("external.asset_id", 1)])

        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.warning(f"Index creation: {e}")

# Start connector polling background task
@app.on_event("startup")
async def start_polling():
    polling_task = ConnectorPollingTask(db)
    asyncio.create_task(polling_task.start())

# Start offer expiration background task (Sprint 6: atomic + contact events + WS)
@app.on_event("startup")
async def start_offer_expiration_task():
    async def expire_offers_loop():
        while True:
            try:
                now_iso = now_utc().isoformat()
                # Find offers to expire (atomic: only SENT status)
                cursor = db.offers.find(
                    {"status": "SENT", "expires_at": {"$lt": now_iso, "$ne": None}},
                    {"_id": 0}
                )
                to_expire = await cursor.to_list(200)
                for offer_doc in to_expire:
                    oid = offer_doc.get("id", "")
                    tid = offer_doc.get("tenant_id", "")
                    # Atomic update: only if still SENT (prevents double expiration)
                    res = await db.offers.update_one(
                        {"id": oid, "status": "SENT"},
                        {"$set": {"status": "EXPIRED", "updated_at": now_iso}}
                    )
                    if res.modified_count > 0:
                        # Audit log
                        await db.audit_logs.insert_one({
                            "id": str(uuid.uuid4()), "tenant_id": tid,
                            "action": "OFFER_EXPIRED", "entity_type": "offer",
                            "entity_id": oid, "actor_user_id": "system",
                            "details": {"reason": "Auto-expired"}, "created_at": now_iso
                        })
                        # Contact event
                        contact_id = offer_doc.get("contact_id", "")
                        if contact_id:
                            await db.contact_events.insert_one({
                                "id": str(uuid.uuid4()), "tenant_id": tid,
                                "contact_id": contact_id, "type": "OFFER_EXPIRED",
                                "title": "Offer expired",
                                "body": f"Offer for {offer_doc.get('room_type','')} expired",
                                "ref_type": "offer", "ref_id": oid,
                                "created_at": now_iso
                            })
                        # WebSocket broadcast
                        try:
                            await ws_manager.broadcast_tenant(
                                tid, "offer", "offer", "expired",
                                {"id": oid, "status": "EXPIRED"}
                            )
                        except Exception:
                            pass
                if to_expire:
                    logger.info("Expired %d offers", len(to_expire))
            except Exception as e:
                logger.error("Offer expiration task error: %s", str(e))
            await asyncio.sleep(60)
    asyncio.create_task(expire_offers_loop())

# Meta token refresh background task (runs every 6 hours)
@app.on_event("startup")
async def start_meta_token_refresh_task():
    async def meta_token_refresh_loop():
        while True:
            try:
                await asyncio.sleep(21600)  # 6 hours
                # Find META credentials expiring within 7 days
                from datetime import timedelta as _td
                threshold = (now_utc() + _td(days=7)).isoformat()
                cursor = db.connector_credentials.find(
                    {"connector_type": "META", "status": "CONNECTED",
                     "token_expires_at": {"$lt": threshold, "$ne": None}},
                    {"_id": 0}
                )
                async for cred_doc in cursor:
                    try:
                        from security import decrypt_field as _dec, encrypt_field as _enc
                        from services.meta_provider import refresh_long_lived_token
                        app_id = cred_doc.get("meta_app_id", "")
                        app_secret = _dec(cred_doc.get("meta_app_secret", ""))
                        current_token = _dec(cred_doc.get("access_token", ""))
                        if not app_id or not app_secret or not current_token:
                            continue
                        result = await refresh_long_lived_token(app_id, app_secret, current_token)
                        if result and result.get("access_token"):
                            expires_in = result.get("expires_in", 5184000)
                            await db.connector_credentials.update_one(
                                {"id": cred_doc["id"]},
                                {"$set": {
                                    "access_token": _enc(result["access_token"]),
                                    "token_expires_at": (now_utc() + _td(seconds=expires_in)).isoformat(),
                                    "last_error": None,
                                    "updated_at": now_utc().isoformat(),
                                }}
                            )
                            await db.audit_log.insert_one({
                                "id": new_id(), "tenant_id": cred_doc["tenant_id"],
                                "action": "META_TOKEN_REFRESHED", "entity_type": "connector",
                                "entity_id": "META", "user_id": "system",
                                "created_at": now_utc().isoformat(),
                            })
                            logger.info(f"Refreshed Meta token for tenant {cred_doc['tenant_id']}")
                        else:
                            await db.connector_credentials.update_one(
                                {"id": cred_doc["id"]},
                                {"$set": {"status": "ERROR", "last_error": "Token refresh failed",
                                          "updated_at": now_utc().isoformat()}}
                            )
                    except Exception as te:
                        logger.error(f"Meta token refresh error: {te}")
            except Exception as e:
                logger.error(f"Meta token refresh loop error: {e}")
    asyncio.create_task(meta_token_refresh_loop())

# ============ USAGE METER MONTHLY RESET (Background Task) ============
@app.on_event("startup")
async def start_usage_meter_task():
    async def usage_meter_loop():
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                # Check if it's the 1st of the month (UTC)
                now = now_utc()
                if now.day == 1 and now.hour == 0:
                    await UsageMeter.monthly_reset(db)
                    logger.info("UsageMeter monthly reset executed")
                
                # Also cleanup expired token families
                token_family_manager.cleanup_expired(72)
            except Exception as e:
                logger.error(f"Usage meter loop error: {e}")
    asyncio.create_task(usage_meter_loop())

# ============ RETENTION AUTO-CLEANUP (Background Task) ============
@app.on_event("startup")
async def start_retention_cleanup_task():
    async def retention_cleanup_loop():
        while True:
            try:
                await asyncio.sleep(86400)  # Daily check
                results = await retention_auto_cleanup(db)
                if results:
                    logger.info(f"Retention auto-cleanup: {len(results)} tenants processed")
            except Exception as e:
                logger.error(f"Retention cleanup loop error: {e}")
    asyncio.create_task(retention_cleanup_loop())

# (WebSocket endpoint moved below to websocket_endpoint_final with auth revalidation)

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

# ============ ENHANCED DASHBOARD STATS — extracted to routers/dashboard_stats.py ============


# ============ WEBSOCKET ENDPOINT (with 15-min auth revalidation) ============
@app.websocket("/ws/{tenant_id}")
async def websocket_endpoint_final(websocket: WebSocket, tenant_id: str):
    channel = f"tenant:{tenant_id}"
    await ws_manager.connect(websocket, channel)
    import time as _time
    last_auth_check = _time.time()
    AUTH_REVALIDATION_INTERVAL = 900  # 15 min
    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                try:
                    await websocket.send_text("ping")
                except:
                    break
                continue
            if data == "ping":
                await websocket.send_text("pong")
            elif data.startswith("auth:"):
                token = data[5:]
                try:
                    payload = decode_token(token)
                    user = await db.users.find_one({"id": payload["user_id"]})
                    if user and user.get("active", True):
                        last_auth_check = _time.time()
                        await websocket.send_json({"type": "auth_valid", "ts": now_utc().isoformat()})
                    else:
                        await websocket.send_json({"type": "auth_invalid", "reason": "user_inactive"})
                        break
                except:
                    await websocket.send_json({"type": "auth_invalid", "reason": "token_expired"})
                    break
            if _time.time() - last_auth_check > AUTH_REVALIDATION_INTERVAL:
                await websocket.send_json({"type": "auth_required", "reason": "revalidation_needed"})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, channel)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        ws_manager.disconnect(websocket, channel)
# Mount legacy router groups (extracted from server.py for maintainability)
try:
    from routers import legacy_rooms, legacy_orders, legacy_contacts
    api_router.include_router(legacy_rooms.router)
    api_router.include_router(legacy_orders.router)
    api_router.include_router(legacy_contacts.router)
    logger.info("Legacy routers mounted: rooms, orders, contacts")
except Exception as e:
    logger.error(f"Failed to mount legacy routers: {e}")

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

try:
    from routers.crm import router as crm_v2_router
    app.include_router(crm_v2_router)
    logger.info("V2 CRM router loaded")
except Exception as e:
    logger.warning(f"V2 CRM router not loaded: {e}")

try:
    from routers.loyalty import router as loyalty_v2_router
    app.include_router(loyalty_v2_router)
    logger.info("V2 loyalty router loaded")
except Exception as e:
    logger.warning(f"V2 loyalty router not loaded: {e}")

try:
    from routers.properties import router as properties_v2_router
    app.include_router(properties_v2_router)
    logger.info("V2 properties router loaded")
except Exception as e:
    logger.warning(f"V2 properties router not loaded: {e}")

try:
    from routers.offers import router as offers_v2_router
    app.include_router(offers_v2_router)
    logger.info("V2 offers router loaded")
except Exception as e:
    logger.warning(f"V2 offers router not loaded: {e}")

try:
    from routers.payments import router as payments_v2_router
    app.include_router(payments_v2_router)
    logger.info("V2 payments router loaded")
except Exception as e:
    logger.warning(f"V2 payments router not loaded: {e}")

try:
    from routers.reservations import router as reservations_v2_router
    app.include_router(reservations_v2_router)
    logger.info("V2 reservations router loaded")
except Exception as e:
    logger.warning(f"V2 reservations router not loaded: {e}")

try:
    from routers.ai_sales import router as ai_sales_router
    app.include_router(ai_sales_router)
    logger.info("V2 AI sales router loaded")
except Exception as e:
    logger.warning(f"V2 AI sales router not loaded: {e}")

try:
    from routers.meta_integration import router as meta_integration_router
    app.include_router(meta_integration_router)
    logger.info("V2 Meta integration router loaded")
except Exception as e:
    logger.warning(f"V2 Meta integration router not loaded: {e}")

try:
    from routers.meta_webhooks import router as meta_webhooks_router
    app.include_router(meta_webhooks_router)
    logger.info("V2 Meta webhooks router loaded")
except Exception as e:
    logger.warning(f"V2 Meta webhooks router not loaded: {e}")

try:
    from routers.whatsapp_templates import router as wa_templates_router
    app.include_router(wa_templates_router)
    logger.info("V2 WhatsApp templates router loaded")
except Exception as e:
    logger.warning(f"V2 WhatsApp templates router not loaded: {e}")

try:
    from routers.syroce_integration import router as syroce_router
    app.include_router(syroce_router)
    logger.info("Syroce integration router loaded")
except Exception as e:
    logger.warning(f"Syroce integration router not loaded: {e}")

# Core extracted routers — must mount independently so an optional
# integration import failure cannot take down primary endpoints.
for _name, _import_path in [
    ("guest_loyalty", "routers.guest_loyalty"),
    ("guest_chat", "routers.guest_chat"),
    ("dashboard_stats", "routers.dashboard_stats"),
    ("analytics", "routers.analytics"),
    ("compliance_growth", "routers.compliance_growth"),
    ("syroce_webhooks", "routers.syroce_webhooks"),
]:
    try:
        _mod = __import__(_import_path, fromlist=["router"])
        app.include_router(_mod.router)
        logger.info(f"Router loaded: {_name}")
    except Exception as _e:
        logger.error(f"FAILED to load required router {_name}: {_e}")
        raise

# Sprint 9: New feature routers
for router_name, router_module, router_attr in [
    ("guest_services", "routers.guest_services", "router"),
    ("notifications", "routers.notifications", "router"),
    ("sla", "routers.sla", "router"),
    ("housekeeping", "routers.housekeeping", "router"),
    ("lost_found", "routers.lost_found", "router"),
    ("social_dashboard", "routers.social_dashboard", "router"),
    ("reports", "routers.reports", "router"),
    ("file_uploads", "routers.file_uploads", "router"),
    ("platform_integrations", "routers.platform_integrations", "router"),
    ("gamification", "routers.gamification", "router"),
    ("push_notifications", "routers.push_notifications", "router"),
    ("ab_testing", "routers.ab_testing", "router"),
    ("loyalty_engine", "routers.loyalty_engine", "router"),
    ("loyalty_analytics", "routers.loyalty_analytics", "router"),
    ("auth", "routers.auth", "router"),
    ("tenants", "routers.tenants", "router"),
    ("billing", "routers.billing", "router"),
    ("system", "routers.system", "router"),
    ("pms_integration", "routers.pms_integration", "router"),
    ("storage", "routers.storage", "router"),
    ("demo_seed", "routers.demo_seed", "router"),
    ("guest_resolve", "routers.guest_resolve", "router"),
]:
    try:
        mod = __import__(router_module, fromlist=[router_attr])
        app.include_router(getattr(mod, router_attr))
        logger.info(f"V2 {router_name} router loaded")
    except Exception as e:
        logger.warning(f"V2 {router_name} router not loaded: {e}")

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-Id", "X-Property-Id", "X-CSRF-Token", "X-Tenant-Id"],
    expose_headers=["X-Request-Id", "X-RateLimit-Remaining", "X-CSRF-Token"],
    max_age=600,
)

# Sprint 6: Request ID middleware + global exception handler
try:
    from core.middleware import RequestIDMiddleware, TenantIsolationMiddleware, global_exception_handler
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(TenantIsolationMiddleware)
    app.add_exception_handler(Exception, global_exception_handler)
    logger.info("Sprint 6 middleware loaded: RequestID + exception handler")
except Exception as e:
    logger.warning(f"Sprint 6 middleware not loaded: {e}")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
