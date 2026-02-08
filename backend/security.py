"""Security module: sessions, rate limiting, brute-force, encryption helpers"""
import hashlib
import time
import uuid
from datetime import datetime, timezone, timedelta
from collections import defaultdict

def now_utc():
    return datetime.now(timezone.utc)

def new_id():
    return str(uuid.uuid4())

# ---- Rate Limiter (in-memory, Redis-ready) ----
class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)  # key -> [timestamp, ...]
    
    def is_rate_limited(self, key: str, max_requests: int = 60, window_seconds: int = 60) -> bool:
        now = time.time()
        self.requests[key] = [t for t in self.requests[key] if t > now - window_seconds]
        if len(self.requests[key]) >= max_requests:
            return True
        self.requests[key].append(now)
        return False
    
    def get_remaining(self, key: str, max_requests: int = 60, window_seconds: int = 60) -> int:
        now = time.time()
        self.requests[key] = [t for t in self.requests[key] if t > now - window_seconds]
        return max(0, max_requests - len(self.requests[key]))

rate_limiter = RateLimiter()

# ---- Brute Force Protection ----
class BruteForceProtection:
    def __init__(self):
        self.attempts = defaultdict(list)  # email -> [(timestamp, success), ...]
        self.lockouts = {}  # email -> lockout_until
    
    def record_attempt(self, email: str, success: bool):
        now = time.time()
        self.attempts[email].append((now, success))
        # Keep last 30 min
        self.attempts[email] = [(t, s) for t, s in self.attempts[email] if t > now - 1800]
        
        if not success:
            failures = sum(1 for t, s in self.attempts[email] if not s and t > now - 300)
            if failures >= 5:
                self.lockouts[email] = now + 900  # 15 min lockout
    
    def is_locked(self, email: str) -> bool:
        lockout = self.lockouts.get(email)
        if lockout and time.time() < lockout:
            return True
        if lockout:
            del self.lockouts[email]
        return False
    
    def get_lockout_remaining(self, email: str) -> int:
        lockout = self.lockouts.get(email, 0)
        return max(0, int(lockout - time.time()))

brute_force = BruteForceProtection()

# ---- Session Helpers ----
def create_session_doc(user_id: str, tenant_id: str, ip: str, user_agent: str, token: str):
    return {
        "id": new_id(),
        "user_id": user_id,
        "tenant_id": tenant_id,
        "token_hash": hashlib.sha256(token.encode()).hexdigest(),
        "ip": ip,
        "user_agent": user_agent[:200] if user_agent else "",
        "device_id": hashlib.md5((user_agent or "" + ip).encode()).hexdigest()[:12],
        "is_active": True,
        "created_at": now_utc().isoformat(),
        "last_seen_at": now_utc().isoformat()
    }

# ---- Encryption helpers (field-level, base64 for MVP) ----
import base64

def encrypt_field(value: str) -> str:
    """Simple base64 encoding - replace with AES/libsodium in production"""
    if not value:
        return value
    return "enc:" + base64.b64encode(value.encode()).decode()

def decrypt_field(value: str) -> str:
    """Decrypt field - replace with AES/libsodium in production"""
    if not value or not value.startswith("enc:"):
        return value
    return base64.b64decode(value[4:]).decode()

# ---- PII Masking ----
def mask_email(email: str) -> str:
    if not email or '@' not in email:
        return email
    local, domain = email.split('@', 1)
    return f"{local[:2]}***@{domain}"

def mask_phone(phone: str) -> str:
    if not phone or len(phone) < 6:
        return phone
    return f"{phone[:3]}***{phone[-3:]}"

# ---- Plan Definitions ----
PLAN_LIMITS = {
    "basic": {
        "label": "Basic",
        "price_monthly": 49,
        "max_users": 5,
        "max_rooms": 20,
        "max_tables": 10,
        "max_contacts": 200,
        "monthly_ai_replies": 50,
        "max_monthly_reservations": 10,
        "max_active_offers": 5,
        "features": ["hotel_qr", "restaurant_qr", "crm", "webchat"]
    },
    "pro": {
        "label": "Pro",
        "price_monthly": 149,
        "max_users": 25,
        "max_rooms": 100,
        "max_tables": 50,
        "max_contacts": 2000,
        "monthly_ai_replies": 500,
        "max_monthly_reservations": 100,
        "max_active_offers": 50,
        "features": ["hotel_qr", "restaurant_qr", "crm", "webchat", "loyalty", "ai_suggestions", "departments", "realtime_boards", "reviews"]
    },
    "enterprise": {
        "label": "Enterprise",
        "price_monthly": 499,
        "max_users": 999,
        "max_rooms": 999,
        "max_tables": 999,
        "max_contacts": 99999,
        "monthly_ai_replies": 9999,
        "max_monthly_reservations": 9999,
        "max_active_offers": 9999,
        "features": ["hotel_qr", "restaurant_qr", "crm", "webchat", "loyalty", "ai_suggestions", "departments", "realtime_boards", "reviews", "api_connectors", "white_label", "custom_sla"]
    }
}

def get_plan_limits(plan: str) -> dict:
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["basic"])

def check_limit(current: int, plan: str, metric: str) -> dict:
    limits = get_plan_limits(plan)
    limit_val = limits.get(metric, 999)
    allowed = current < limit_val
    return {
        "allowed": allowed,
        "current": current,
        "limit": limit_val,
        "plan": plan,
        "metric": metric
    }
