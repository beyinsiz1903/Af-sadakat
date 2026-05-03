from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
import hashlib
import bcrypt

from core.config import db, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRY_HOURS
from core.tenant_guard import serialize_doc, new_id, now_utc, log_audit
from security import rate_limiter, brute_force, create_session_doc, token_family_manager, csrf_protection

from datetime import datetime, timezone, timedelta
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/api/auth", tags=["auth"])

class LoginRequest(BaseModel):
    email: str
    password: str

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

async def get_tenant_by_id(tenant_id: str):
    tenant = await db.tenants.find_one({"id": tenant_id})
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return serialize_doc(tenant)

@router.post("/register")
async def register(data: dict):
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

@router.post("/login")
async def login(data: LoginRequest, request: Request = None):
    if brute_force.is_locked(data.email):
        remaining = brute_force.get_lockout_remaining(data.email)
        raise HTTPException(status_code=429, detail=f"Account locked. Try again in {remaining}s")

    client_ip = request.client.host if request else "unknown"
    rate_check = rate_limiter.check_tiered(client_ip, route="auth/login")
    if rate_check["limited"]:
        raise HTTPException(status_code=429, detail=f"Too many login attempts. Retry after {rate_check['retry_after']}s")

    user = await db.users.find_one({"email": data.email})
    if not user or not verify_password(data.password, user["password_hash"]):
        brute_force.record_attempt(data.email, False)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.get("active", True):
        raise HTTPException(status_code=403, detail="Account disabled")

    brute_force.record_attempt(data.email, True)
    tenant = await db.tenants.find_one({"id": user["tenant_id"]})
    token = create_token(user["id"], user["tenant_id"], user["role"])

    token_family_manager.create_family(user["id"], token)

    user_agent = request.headers.get("user-agent", "") if request else ""
    session = create_session_doc(user["id"], user["tenant_id"], client_ip, user_agent, token)
    await db.sessions.insert_one(session)

    user_doc = serialize_doc(user)
    user_doc.pop("password_hash", None)
    user_doc.pop("_id", None)

    return {
        "token": token,
        "user": user_doc,
        "tenant": serialize_doc(tenant),
        "session_id": session["id"],
        "csrf_token": csrf_protection.generate_token(user["id"])
    }

@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    tenant = await get_tenant_by_id(user["tenant_id"])
    user_data = {k: v for k, v in user.items() if k != "password_hash"}
    return {"user": user_data, "tenant": tenant}

@router.post("/refresh")
async def refresh_token(data: dict):
    old_token = data.get("token", "")
    try:
        payload = decode_token(old_token)
        user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        new_token = create_token(user["id"], user["tenant_id"], user["role"])

        rotation_result = token_family_manager.rotate_token(old_token, new_token)
        if not rotation_result["valid"]:
            if rotation_result.get("reason") == "token_reuse_detected":
                await db.sessions.update_many(
                    {"user_id": user["id"]},
                    {"$set": {"is_active": False}}
                )
                await log_audit(user["tenant_id"], "token_reuse_detected", "user", user["id"], details={"family": rotation_result.get("invalidated_family")})
                raise HTTPException(status_code=401, detail="Token reuse detected. All sessions invalidated.")
            token_family_manager.create_family(user["id"], new_token)

        token_hash = hashlib.sha256(old_token.encode()).hexdigest()
        await db.sessions.update_one(
            {"token_hash": token_hash, "is_active": True},
            {"$set": {"last_seen_at": now_utc().isoformat(), "token_hash": hashlib.sha256(new_token.encode()).hexdigest()}}
        )

        return {
            "token": new_token,
            "user": {k: v for k, v in serialize_doc(user).items() if k != "password_hash"},
            "csrf_token": csrf_protection.generate_token(user["id"])
        }
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

@router.post("/logout")
async def logout(request: Request, user=Depends(get_current_user)):
    await log_audit(user["tenant_id"], "logout", "user", user["id"], user["id"])
    return {"status": "logged_out"}

@router.get("/sessions")
async def list_sessions(user=Depends(get_current_user)):
    sessions = await db.sessions.find(
        {"user_id": user["id"], "is_active": True}, {"_id": 0}
    ).sort("last_seen_at", -1).to_list(20)
    return [serialize_doc(s) for s in sessions]

@router.delete("/sessions/{session_id}")
async def revoke_session(session_id: str, user=Depends(get_current_user)):
    result = await db.sessions.update_one(
        {"id": session_id, "user_id": user["id"]},
        {"$set": {"is_active": False}}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"revoked": True}

@router.get("/csrf-token")
async def get_csrf_token(user=Depends(get_current_user)):
    return {"csrf_token": csrf_protection.generate_token(user["id"])}


# ---------------------------------------------------------------------------
# OTP (Twilio Verify) — phone verification for guest flows / 2FA
# ---------------------------------------------------------------------------
class OtpSendRequest(BaseModel):
    phone: str
    channel: str = "sms"


class OtpVerifyRequest(BaseModel):
    phone: str
    code: str


@router.post("/otp/send")
async def otp_send(data: OtpSendRequest, request: Request):
    client_ip = request.client.host if request else "unknown"
    rate_check = rate_limiter.check_tiered(client_ip, route="auth/otp_send")
    if rate_check["limited"]:
        raise HTTPException(status_code=429, detail=f"Too many OTP requests. Retry after {rate_check['retry_after']}s")

    from services.twilio_provider import send_otp, is_configured
    sent, dev_code = await send_otp(data.phone, channel=data.channel)
    if not sent:
        raise HTTPException(status_code=502, detail="OTP send failed")
    resp = {"sent": True, "configured": is_configured()}
    if dev_code is not None:
        resp["dev_code"] = dev_code
    return resp


@router.post("/otp/verify")
async def otp_verify(data: OtpVerifyRequest, request: Request):
    client_ip = request.client.host if request else "unknown"
    rate_check = rate_limiter.check_tiered(client_ip, route="auth/otp_verify")
    if rate_check["limited"]:
        raise HTTPException(status_code=429, detail=f"Too many OTP attempts. Retry after {rate_check['retry_after']}s")

    from services.twilio_provider import verify_otp
    ok = await verify_otp(data.phone, data.code)
    if not ok:
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    return {"verified": True}
