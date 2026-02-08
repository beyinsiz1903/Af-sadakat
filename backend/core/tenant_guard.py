"""Centralized tenant isolation guard - THE critical security layer

Every DB query MUST go through tenant-scoped helpers.
This module provides:
1. tenant_guard() - FastAPI dependency that extracts + validates tenantId
2. Scoped query helpers that ALWAYS include tenantId
3. Guest token validation with cross-check
"""
import uuid
import secrets
import string
from datetime import datetime, timezone
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

from core.config import db, JWT_SECRET, JWT_ALGORITHM, GUEST_JWT_SECRET

security = HTTPBearer(auto_error=False)

def now_utc():
    return datetime.now(timezone.utc)

def new_id():
    return str(uuid.uuid4())

def generate_secure_code(prefix: str = "r", length: int = 12) -> str:
    """Generate a cryptographically secure, unguessable code
    Example: r_a8f3k2m9p4x7 (not sequential, not predictable)
    """
    chars = string.ascii_lowercase + string.digits
    random_part = ''.join(secrets.choice(chars) for _ in range(length))
    return f"{prefix}_{random_part}"

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

# ---- Token helpers ----
def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def decode_guest_token_safe(token: str) -> dict:
    try:
        payload = jwt.decode(token, GUEST_JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "guest":
            raise HTTPException(status_code=401, detail="Not a guest token")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Guest token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid guest token")

# ---- Tenant Guard (THE critical dependency) ----
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Extract and validate user from JWT. Returns user dict with tenant_id guaranteed."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_access_token(credentials.credentials)
    user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return serialize_doc(user)

async def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        return None
    try:
        payload = decode_access_token(credentials.credentials)
        user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
        return serialize_doc(user) if user else None
    except:
        return None

# ---- Tenant resolution (slug -> tenant) ----
async def resolve_tenant(slug: str):
    """Resolve tenant by slug - central isolation point"""
    tenant = await db.tenants.find_one({"slug": slug})
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant not found: {slug}")
    return serialize_doc(tenant)

# ---- Scoped query helpers (ALWAYS include tenantId) ----
async def find_one_scoped(collection_name: str, tenant_id: str, query: dict, projection=None):
    """Find one document, ALWAYS scoped by tenant_id"""
    query["tenant_id"] = tenant_id
    proj = projection or {"_id": 0}
    doc = await db[collection_name].find_one(query, proj)
    return serialize_doc(doc) if doc else None

async def find_many_scoped(collection_name: str, tenant_id: str, query: dict = None, 
                           sort=None, skip=0, limit=100, projection=None):
    """Find many documents, ALWAYS scoped by tenant_id"""
    q = query or {}
    q["tenant_id"] = tenant_id
    proj = projection or {"_id": 0}
    cursor = db[collection_name].find(q, proj)
    if sort:
        cursor = cursor.sort(sort)
    if skip:
        cursor = cursor.skip(skip)
    docs = await cursor.limit(limit).to_list(limit)
    return [serialize_doc(d) for d in docs]

async def count_scoped(collection_name: str, tenant_id: str, query: dict = None):
    """Count documents, ALWAYS scoped by tenant_id"""
    q = query or {}
    q["tenant_id"] = tenant_id
    return await db[collection_name].count_documents(q)

async def insert_scoped(collection_name: str, tenant_id: str, doc: dict):
    """Insert document, ALWAYS includes tenant_id"""
    doc["tenant_id"] = tenant_id
    if "id" not in doc:
        doc["id"] = new_id()
    if "created_at" not in doc:
        doc["created_at"] = now_utc().isoformat()
    await db[collection_name].insert_one(doc)
    return serialize_doc(doc)

async def update_scoped(collection_name: str, tenant_id: str, doc_id: str, update: dict):
    """Update document, ALWAYS scoped by tenant_id + id"""
    update["updated_at"] = now_utc().isoformat()
    await db[collection_name].update_one(
        {"id": doc_id, "tenant_id": tenant_id},
        {"$set": update}
    )
    return await find_one_scoped(collection_name, tenant_id, {"id": doc_id})

async def delete_scoped(collection_name: str, tenant_id: str, doc_id: str):
    """Delete document, ALWAYS scoped by tenant_id + id"""
    result = await db[collection_name].delete_one({"id": doc_id, "tenant_id": tenant_id})
    return result.deleted_count > 0

# ---- Audit logging ----
async def log_audit(tenant_id: str, action: str, entity_type: str, entity_id: str, 
                    actor_id: str = "", details: dict = None):
    await db.audit_logs.insert_one({
        "id": new_id(),
        "tenant_id": tenant_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "actor_user_id": actor_id,
        "details": details or {},
        "created_at": now_utc().isoformat()
    })

# ---- Guest token cross-validation ----
async def validate_guest_room_access(guest_token: str, room_code: str = None):
    """Validate guest token and cross-check room access"""
    payload = decode_guest_token_safe(guest_token)
    tenant_id = payload.get("tenant_id")
    token_room_id = payload.get("room_id")
    
    if room_code:
        room = await find_one_scoped("rooms", tenant_id, {"room_code": room_code})
        if not room or room["id"] != token_room_id:
            raise HTTPException(status_code=403, detail="Room access denied")
    
    return payload

async def validate_guest_table_access(guest_token: str, table_code: str = None):
    """Validate guest token and cross-check table access"""
    payload = decode_guest_token_safe(guest_token)
    tenant_id = payload.get("tenant_id")
    token_table_id = payload.get("table_id")
    
    if table_code:
        table = await find_one_scoped("tables", tenant_id, {"table_code": table_code})
        if not table or table["id"] != token_table_id:
            raise HTTPException(status_code=403, detail="Table access denied")
    
    return payload
