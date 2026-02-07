# RBAC Permission System

ROLES = {
    "owner": {
        "level": 100,
        "label": "Owner",
        "permissions": ["*"]  # Full access
    },
    "admin": {
        "level": 90,
        "label": "Admin",
        "permissions": [
            "dashboard", "inbox", "requests", "orders", "rooms", "tables",
            "menu", "contacts", "settings", "users", "departments", "loyalty",
            "reviews", "offers", "connectors", "reports"
        ]
    },
    "manager": {
        "level": 70,
        "label": "Manager",
        "permissions": [
            "dashboard", "inbox", "requests", "orders", "contacts",
            "reviews", "offers", "reports"
        ]
    },
    "agent": {
        "level": 50,
        "label": "Agent",
        "permissions": [
            "inbox", "requests", "contacts", "reviews"
        ]
    },
    "department_staff": {
        "level": 30,
        "label": "Department Staff",
        "permissions": ["requests"]  # Only sees own department
    },
    "kitchen_staff": {
        "level": 30,
        "label": "Kitchen Staff",
        "permissions": ["orders"]
    },
    "front_desk": {
        "level": 30,
        "label": "Front Desk",
        "permissions": ["requests", "inbox", "contacts"]
    }
}

def has_permission(role: str, permission: str) -> bool:
    role_data = ROLES.get(role, {})
    perms = role_data.get("permissions", [])
    return "*" in perms or permission in perms

def get_role_level(role: str) -> int:
    return ROLES.get(role, {}).get("level", 0)

def get_accessible_modules(role: str) -> list:
    role_data = ROLES.get(role, {})
    perms = role_data.get("permissions", [])
    if "*" in perms:
        return list(set(p for r in ROLES.values() for p in r["permissions"] if p != "*"))
    return perms

LOYALTY_TIERS = {
    "bronze": {"min_points": 0, "label": "Bronze", "color": "#CD7F32", "benefits": ["5% off room service"]},
    "silver": {"min_points": 500, "label": "Silver", "color": "#C0C0C0", "benefits": ["10% off room service", "Late checkout"]},
    "gold": {"min_points": 2000, "label": "Gold", "color": "#FFD700", "benefits": ["15% off all services", "Late checkout", "Room upgrade priority"]},
    "platinum": {"min_points": 5000, "label": "Platinum", "color": "#E5E4E2", "benefits": ["20% off all services", "Late checkout", "Room upgrade", "Welcome amenity"]}
}

def compute_tier(points: int) -> str:
    if points >= 5000:
        return "platinum"
    elif points >= 2000:
        return "gold"
    elif points >= 500:
        return "silver"
    return "bronze"

def next_tier_info(current_tier: str, points: int) -> dict:
    tiers_order = ["bronze", "silver", "gold", "platinum"]
    idx = tiers_order.index(current_tier) if current_tier in tiers_order else 0
    if idx >= len(tiers_order) - 1:
        return {"next_tier": None, "points_needed": 0, "progress": 100}
    next_t = tiers_order[idx + 1]
    needed = LOYALTY_TIERS[next_t]["min_points"]
    current_min = LOYALTY_TIERS[current_tier]["min_points"]
    range_pts = needed - current_min
    progress = min(100, int(((points - current_min) / range_pts) * 100)) if range_pts > 0 else 100
    return {
        "next_tier": next_t,
        "next_tier_label": LOYALTY_TIERS[next_t]["label"],
        "points_needed": max(0, needed - points),
        "progress": progress
    }

# Sentiment analysis (simple rule-based)
NEGATIVE_WORDS = {
    "en": ["terrible", "horrible", "awful", "worst", "disgusting", "broken", "dirty", "cold", "noisy", "rude", "slow", "bad", "complaint", "unacceptable", "disappointed"],
    "tr": ["berbat", "korkunç", "kötü", "pis", "kırık", "soğuk", "gürültülü", "kaba", "yavaş", "şikayet", "kabul edilemez", "hayal kırıklığı"]
}
POSITIVE_WORDS = {
    "en": ["excellent", "amazing", "wonderful", "great", "perfect", "clean", "beautiful", "friendly", "fast", "loved", "best", "thank", "impressed"],
    "tr": ["mükemmel", "harika", "muhteşem", "temiz", "güzel", "hızlı", "sevdik", "teşekkür", "etkilendik"]
}

def analyze_sentiment(text: str) -> str:
    lower = text.lower()
    neg_count = sum(1 for lang in NEGATIVE_WORDS.values() for w in lang if w in lower)
    pos_count = sum(1 for lang in POSITIVE_WORDS.values() for w in lang if w in lower)
    if neg_count > pos_count:
        return "negative"
    elif pos_count > neg_count:
        return "positive"
    return "neutral"

# Connector types
CONNECTOR_TYPES = [
    {"type": "WHATSAPP", "label": "WhatsApp Business", "icon": "MessageCircle", "status": "coming_soon"},
    {"type": "INSTAGRAM", "label": "Instagram DM", "icon": "Instagram", "status": "coming_soon"},
    {"type": "GOOGLE_REVIEWS", "label": "Google Reviews", "icon": "Star", "status": "coming_soon"},
    {"type": "TRIPADVISOR", "label": "TripAdvisor", "icon": "Award", "status": "coming_soon"},
    {"type": "WEBCHAT", "label": "Web Chat", "icon": "MessageSquare", "status": "active"},
]

# Fake review data for stubs
FAKE_REVIEWS = [
    {"source": "GOOGLE_REVIEWS", "author": "Sarah M.", "rating": 5, "text": "Absolutely wonderful stay! The room service was incredibly fast and the staff was so friendly. Will definitely come back!", "language": "en"},
    {"source": "GOOGLE_REVIEWS", "author": "Mehmet K.", "rating": 4, "text": "Güzel otel, temiz odalar. Kahvaltı çeşidi biraz artabilir ama genel olarak memnun kaldık.", "language": "tr"},
    {"source": "TRIPADVISOR", "author": "James W.", "rating": 3, "text": "Decent hotel but the AC in our room wasn't working properly. Staff tried to fix it but took too long.", "language": "en"},
    {"source": "GOOGLE_REVIEWS", "author": "Ayşe D.", "rating": 5, "text": "Harika bir deneyimdi! Personel çok ilgili, oda çok temiz. Kesinlikle tekrar geleceğiz.", "language": "tr"},
    {"source": "TRIPADVISOR", "author": "Emma L.", "rating": 2, "text": "Disappointed with the noise levels. Room was nice but couldn't sleep well. The restaurant food was good though.", "language": "en"},
    {"source": "GOOGLE_REVIEWS", "author": "Ali R.", "rating": 4, "text": "Konum mükemmel, personel yardımsever. Havuz alanı biraz küçük ama deniz manzarası muhteşem.", "language": "tr"},
]
