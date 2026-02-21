"""Security module: sessions, rate limiting, brute-force, encryption, CSRF, token rotation, device tracking"""
import hashlib
import time
import uuid
import secrets
import hmac
from datetime import datetime, timezone, timedelta
from collections import defaultdict
import base64
import json

def now_utc():
    return datetime.now(timezone.utc)

def new_id():
    return str(uuid.uuid4())

# ---- Rate Limiter (Tiered: global + tenant + route) ----
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
    
    def check_tiered(self, ip: str, tenant_id: str = None, route: str = None) -> dict:
        """Tiered rate limiting: global IP -> tenant -> route"""
        # Global IP limit: 200/min
        if self.is_rate_limited(f"global:{ip}", max_requests=200, window_seconds=60):
            return {"limited": True, "level": "global", "retry_after": 60}
        
        # Tenant-level: 100/min per tenant per IP
        if tenant_id:
            if self.is_rate_limited(f"tenant:{tenant_id}:{ip}", max_requests=100, window_seconds=60):
                return {"limited": True, "level": "tenant", "retry_after": 60}
        
        # Route-level: specific limits for sensitive routes
        if route:
            route_limits = {
                "auth/login": (10, 300),       # 10 per 5 min
                "auth/register": (5, 300),      # 5 per 5 min
                "auth/refresh": (30, 60),       # 30 per min
                "billing/webhook": (50, 60),    # 50 per min
                "compliance/export": (5, 60),   # 5 per min
                "compliance/forget": (3, 60),   # 3 per min
            }
            for pattern, (max_req, window) in route_limits.items():
                if pattern in route:
                    if self.is_rate_limited(f"route:{pattern}:{ip}", max_requests=max_req, window_seconds=window):
                        return {"limited": True, "level": "route", "retry_after": window}
        
        return {"limited": False}

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

# ---- Token Family Manager (Refresh Token Rotation) ----
class TokenFamilyManager:
    """Manages refresh token families for token rotation.
    Each login creates a new family. When a refresh token is used,
    it's invalidated and a new one is issued. If an already-used
    token is presented, the entire family is invalidated (theft detection).
    """
    def __init__(self):
        self.families = {}  # family_id -> {tokens: set, active_token: str, user_id: str, created_at: float}
        self.token_to_family = {}  # token_hash -> family_id
    
    def create_family(self, user_id: str, token: str) -> str:
        family_id = new_id()
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        self.families[family_id] = {
            "tokens": {token_hash},
            "active_token": token_hash,
            "user_id": user_id,
            "created_at": time.time()
        }
        self.token_to_family[token_hash] = family_id
        return family_id
    
    def rotate_token(self, old_token: str, new_token: str) -> dict:
        """Rotate refresh token. Returns {valid, family_id, invalidated_family}"""
        old_hash = hashlib.sha256(old_token.encode()).hexdigest()
        family_id = self.token_to_family.get(old_hash)
        
        if not family_id or family_id not in self.families:
            return {"valid": False, "reason": "unknown_token"}
        
        family = self.families[family_id]
        
        # Check if this is a reused (already rotated) token - possible theft
        if old_hash != family["active_token"]:
            # Invalidate entire family
            self._invalidate_family(family_id)
            return {"valid": False, "reason": "token_reuse_detected", "invalidated_family": family_id}
        
        # Rotate: invalidate old, activate new
        new_hash = hashlib.sha256(new_token.encode()).hexdigest()
        family["tokens"].add(new_hash)
        family["active_token"] = new_hash
        self.token_to_family[new_hash] = family_id
        
        return {"valid": True, "family_id": family_id}
    
    def _invalidate_family(self, family_id: str):
        """Invalidate all tokens in a family"""
        family = self.families.pop(family_id, None)
        if family:
            for token_hash in family["tokens"]:
                self.token_to_family.pop(token_hash, None)
    
    def invalidate_user_families(self, user_id: str):
        """Invalidate all families for a user (e.g., on password change)"""
        to_remove = [fid for fid, f in self.families.items() if f["user_id"] == user_id]
        for fid in to_remove:
            self._invalidate_family(fid)
    
    def cleanup_expired(self, max_age_hours: int = 72):
        """Remove expired families"""
        cutoff = time.time() - (max_age_hours * 3600)
        expired = [fid for fid, f in self.families.items() if f["created_at"] < cutoff]
        for fid in expired:
            self._invalidate_family(fid)

token_family_manager = TokenFamilyManager()

# ---- Device Session Tracking ----
def create_session_doc(user_id: str, tenant_id: str, ip: str, user_agent: str, token: str):
    """Create a device session document with fingerprinting"""
    import re
    ua = user_agent or ""
    
    # Parse device info from user-agent
    device_type = "desktop"
    if "Mobile" in ua or "Android" in ua or "iPhone" in ua:
        device_type = "mobile"
    elif "Tablet" in ua or "iPad" in ua:
        device_type = "tablet"
    
    # Extract browser
    browser = "unknown"
    if "Chrome" in ua and "Edg" not in ua:
        browser = "Chrome"
    elif "Firefox" in ua:
        browser = "Firefox"
    elif "Safari" in ua and "Chrome" not in ua:
        browser = "Safari"
    elif "Edg" in ua:
        browser = "Edge"
    
    # Extract OS
    os_name = "unknown"
    if "Windows" in ua:
        os_name = "Windows"
    elif "Mac OS" in ua or "Macintosh" in ua:
        os_name = "macOS"
    elif "Linux" in ua:
        os_name = "Linux"
    elif "Android" in ua:
        os_name = "Android"
    elif "iPhone" in ua or "iPad" in ua:
        os_name = "iOS"
    
    device_id = hashlib.md5((ua + ip).encode()).hexdigest()[:12]
    
    return {
        "id": new_id(),
        "user_id": user_id,
        "tenant_id": tenant_id,
        "token_hash": hashlib.sha256(token.encode()).hexdigest(),
        "ip": ip,
        "user_agent": ua[:200],
        "device_id": device_id,
        "device_type": device_type,
        "browser": browser,
        "os": os_name,
        "is_active": True,
        "created_at": now_utc().isoformat(),
        "last_seen_at": now_utc().isoformat(),
        "expires_at": (now_utc() + timedelta(hours=72)).isoformat()
    }

# ---- CSRF Protection ----
class CSRFProtection:
    """CSRF token generation and validation for cookie-based auth flows"""
    
    def __init__(self, secret: str = None):
        self.secret = secret or secrets.token_hex(32)
    
    def generate_token(self, session_id: str) -> str:
        """Generate a CSRF token tied to a session"""
        timestamp = str(int(time.time()))
        payload = f"{session_id}:{timestamp}"
        signature = hmac.new(self.secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
        return base64.urlsafe_b64encode(f"{payload}:{signature}".encode()).decode()
    
    def validate_token(self, token: str, session_id: str, max_age_seconds: int = 3600) -> bool:
        """Validate a CSRF token"""
        try:
            decoded = base64.urlsafe_b64decode(token.encode()).decode()
            parts = decoded.split(":")
            if len(parts) != 3:
                return False
            stored_session, timestamp, signature = parts
            if stored_session != session_id:
                return False
            # Check age
            if time.time() - int(timestamp) > max_age_seconds:
                return False
            # Verify signature
            expected_payload = f"{stored_session}:{timestamp}"
            expected_sig = hmac.new(self.secret.encode(), expected_payload.encode(), hashlib.sha256).hexdigest()
            return hmac.compare_digest(signature, expected_sig)
        except Exception:
            return False

csrf_protection = CSRFProtection()

# ---- Encryption helpers (field-level, base64 for MVP) ----
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
        "price_yearly": 470,
        "max_users": 5,
        "max_rooms": 20,
        "max_tables": 10,
        "max_contacts": 200,
        "monthly_ai_replies": 50,
        "max_monthly_reservations": 10,
        "max_active_offers": 5,
        "features": ["hotel_qr", "restaurant_qr", "crm", "webchat"],
        "badge_color": "blue"
    },
    "pro": {
        "label": "Pro",
        "price_monthly": 149,
        "price_yearly": 1430,
        "max_users": 25,
        "max_rooms": 100,
        "max_tables": 50,
        "max_contacts": 2000,
        "monthly_ai_replies": 500,
        "max_monthly_reservations": 100,
        "max_active_offers": 50,
        "features": ["hotel_qr", "restaurant_qr", "crm", "webchat", "loyalty", "ai_suggestions", "departments", "realtime_boards", "reviews"],
        "badge_color": "amber"
    },
    "enterprise": {
        "label": "Enterprise",
        "price_monthly": 499,
        "price_yearly": 4790,
        "max_users": 999,
        "max_rooms": 999,
        "max_tables": 999,
        "max_contacts": 99999,
        "monthly_ai_replies": 9999,
        "max_monthly_reservations": 9999,
        "max_active_offers": 9999,
        "features": ["hotel_qr", "restaurant_qr", "crm", "webchat", "loyalty", "ai_suggestions", "departments", "realtime_boards", "reviews", "api_connectors", "white_label", "custom_sla", "advanced_analytics", "gdpr_tools"],
        "badge_color": "purple"
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
        "metric": metric,
        "usage_pct": round(current / max(limit_val, 1) * 100, 1)
    }
