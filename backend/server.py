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
import hashlib

# Add backend dir to path for local imports
sys.path.insert(0, str(Path(__file__).parent))
from rbac import ROLES, has_permission, get_accessible_modules, LOYALTY_TIERS, compute_tier, next_tier_info
from connectors_legacy import get_connector
from security import rate_limiter, brute_force, create_session_doc, encrypt_field, decrypt_field, mask_email, mask_phone, PLAN_LIMITS, get_plan_limits, check_limit, token_family_manager, csrf_protection
from billing import create_billing_account, create_subscription, create_invoice, generate_mock_invoices, usage_meter, handle_stripe_webhook, UsageMeter, create_payment_method
from analytics_engine import compute_analytics, compute_revenue_analytics, compute_staff_performance, compute_investor_metrics
from compliance import export_guest_data, forget_guest, log_consent, retention_auto_cleanup
from referral import get_or_create_referral, track_referral_click, track_referral_signup, generate_referral_code, get_referral_landing_data
from guest_system import create_guest_token, decode_guest_token, encrypt_credentials, decrypt_credentials, ConnectorPollingTask
from sentry_init import init_sentry

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Initialize Sentry (no-op if SENTRY_DSN not set)
init_sentry()

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
    except Exception:
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



# ============ MENU ROUTES ============









# ============ WEBCHAT/CONVERSATION + AI SUGGEST — extracted to routers/guest_chat.py ============


# ============ LOYALTY ROUTES — extracted to routers/guest_loyalty.py ============

# ============ DASHBOARD STATS — extracted to routers/dashboard_stats.py ============


# ============ GUEST INFO ROUTES ============


# ============ SEED DATA ============




# ============ QR CODE ENDPOINTS ============




# ============ REQUEST COMMENTS ============


# ============ KB ARTICLES ============



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

        # Performance: stats/enhanced + reports + cohort indexes
        await db.guest_requests.create_index([("tenant_id", 1), ("created_at", -1)])
        await db.guest_requests.create_index([("tenant_id", 1), ("department_code", 1), ("created_at", -1)])
        await db.guest_requests.create_index([("tenant_id", 1), ("rating", 1)], sparse=True)
        await db.loyalty_accounts.create_index([("tenant_id", 1), ("enrolled_at", -1)])
        await db.spa_bookings.create_index([("tenant_id", 1), ("status", 1)])
        await db.restaurant_reservations.create_index([("tenant_id", 1), ("status", 1)])
        await db.transport_requests.create_index([("tenant_id", 1), ("status", 1)])
        await db.laundry_requests.create_index([("tenant_id", 1), ("status", 1)])
        await db.notifications.create_index([("tenant_id", 1), ("read", 1)])
        await db.lost_found.create_index([("tenant_id", 1), ("status", 1)])
        await db.guest_surveys.create_index([("tenant_id", 1), ("created_at", -1)])

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




# ============ CONNECTOR FRAMEWORK ============


# ============ OFFERS + MOCK PAYMENTS ============





# ============ GUEST INTELLIGENCE (CRM) ============

# ============ AUDIT LOG — use core.tenant_guard.log_audit instead (dead _log_audit removed) ============
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
                except Exception:
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
                except Exception:
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
    ("legacy_restaurant", "routers.legacy_restaurant", "router"),
    ("legacy_qr", "routers.legacy_qr", "router"),
    ("legacy_engagement", "routers.legacy_engagement", "router"),
    ("legacy_misc", "routers.legacy_misc", "router"),
    ("exports", "routers.exports", "router"),
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
