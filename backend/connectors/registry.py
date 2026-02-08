"""Connector registry + base interface + stubs
All stubs return deterministic fake data seeded by tenant_id hash.
"""
import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod

def _now():
    return datetime.now(timezone.utc)

def _stable_id(tenant_id: str, source: str, idx: int) -> str:
    """Deterministic external_id per tenant+source+index"""
    raw = f"{tenant_id}:{source}:{idx}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


class ConnectorBase(ABC):
    """Base connector interface. All connectors must implement fetch_updates."""
    connector_type: str = "BASE"
    
    @abstractmethod
    async def fetch_updates(self, tenant_id: str, credentials: dict) -> List[Dict[str, Any]]:
        """Fetch new messages or reviews. Returns list of event dicts."""
        ...


class WebChatConnector(ConnectorBase):
    """WebChat is REAL - messages come from the API, not polling."""
    connector_type = "WEBCHAT"
    
    async def fetch_updates(self, tenant_id: str, credentials: dict) -> list:
        return []  # WebChat messages arrive via API, not polling


class WhatsAppStubConnector(ConnectorBase):
    """WhatsApp Business stub. TODO: Replace with real Meta WhatsApp Business API."""
    connector_type = "WHATSAPP"
    
    async def fetch_updates(self, tenant_id: str, credentials: dict) -> list:
        names = ["Ahmed K.", "Maria S.", "John D.", "Ayse T.", "Carlos R."]
        messages = [
            ("Hi, I'd like to book a room for next weekend", "en"),
            ("What time is checkout?", "en"),
            ("Merhaba, bu hafta sonu icin oda var mi?", "tr"),
            ("Is breakfast included?", "en"),
            ("Kahvalti dahil mi?", "tr"),
        ]
        results = []
        for i in range(min(2, len(names))):
            eid = _stable_id(tenant_id, "WHATSAPP", i)
            msg_text, lang = messages[i % len(messages)]
            results.append({
                "type": "message",
                "external_id": eid,
                "channel": "WHATSAPP",
                "from_name": names[i % len(names)],
                "from_phone": f"+9055{50000000 + i}",
                "body": msg_text,
                "language": lang,
                "timestamp": _now().isoformat(),
                "is_stub": True,
            })
        return results


class InstagramStubConnector(ConnectorBase):
    """Instagram DM stub. TODO: Replace with real Instagram Graph API."""
    connector_type = "INSTAGRAM"
    
    async def fetch_updates(self, tenant_id: str, credentials: dict) -> list:
        handles = ["@travel_adventures", "@food_lovers", "@hotel_guide"]
        messages = [
            "Love your hotel! Can I book directly?",
            "Your restaurant photos look amazing!",
            "Do you have any special offers this month?",
        ]
        results = []
        for i in range(min(2, len(handles))):
            eid = _stable_id(tenant_id, "INSTAGRAM", i)
            results.append({
                "type": "message",
                "external_id": eid,
                "channel": "INSTAGRAM",
                "from_name": handles[i],
                "from_handle": handles[i],
                "body": messages[i],
                "timestamp": _now().isoformat(),
                "is_stub": True,
            })
        return results


class GoogleReviewsStubConnector(ConnectorBase):
    """Google Reviews stub. TODO: Replace with Google My Business API."""
    connector_type = "GOOGLE_REVIEWS"
    
    async def fetch_updates(self, tenant_id: str, credentials: dict) -> list:
        reviews = [
            {"author": "Sarah M.", "rating": 5, "text": "Absolutely wonderful stay! The room service was incredibly fast and the staff was so friendly. Will definitely come back!", "lang": "en"},
            {"author": "Mehmet K.", "rating": 4, "text": "Guzel otel, temiz odalar. Kahvalti cesidi biraz artabilir ama genel olarak memnun kaldik.", "lang": "tr"},
            {"author": "Ayse D.", "rating": 5, "text": "Harika bir deneyimdi! Personel cok ilgili, oda cok temiz. Kesinlikle tekrar gelecegiz.", "lang": "tr"},
            {"author": "Ali R.", "rating": 4, "text": "Konum mukemmel, personel yardimsever. Havuz alani biraz kucuk ama deniz manzarasi muhtesem.", "lang": "tr"},
            {"author": "Tom W.", "rating": 5, "text": "Great location, excellent breakfast buffet. The spa was a nice bonus.", "lang": "en"},
            {"author": "Lisa B.", "rating": 5, "text": "Perfect honeymoon destination. The sunset view from our balcony was breathtaking.", "lang": "en"},
            {"author": "Kemal Y.", "rating": 4, "text": "Temiz ve konforlu. WiFi biraz yavas ama personel cok ilgili.", "lang": "tr"},
            {"author": "Anna P.", "rating": 3, "text": "Decent hotel but the AC in our room wasn't working properly. Staff tried to fix it but took too long.", "lang": "en"},
        ]
        results = []
        for i, r in enumerate(reviews):
            eid = _stable_id(tenant_id, "GOOGLE_REVIEWS", i)
            results.append({
                "type": "review",
                "external_id": eid,
                "source_type": "GOOGLE_REVIEWS",
                "author_name": r["author"],
                "rating": r["rating"],
                "text": r["text"],
                "language": r["lang"],
                "timestamp": (_now() - timedelta(days=i*3+1)).isoformat(),
                "is_stub": True,
            })
        return results


class TripAdvisorStubConnector(ConnectorBase):
    """TripAdvisor stub. TODO: Replace with TripAdvisor Content API."""
    connector_type = "TRIPADVISOR"
    
    async def fetch_updates(self, tenant_id: str, credentials: dict) -> list:
        reviews = [
            {"author": "James W.", "rating": 3, "text": "Decent hotel but the AC in our room wasn't working properly. Staff tried to fix it but took too long.", "lang": "en"},
            {"author": "Emma L.", "rating": 2, "text": "Disappointed with the noise levels. Room was nice but couldn't sleep well. The restaurant food was good though.", "lang": "en"},
            {"author": "Robert H.", "rating": 5, "text": "One of the best hotels we've stayed at in Istanbul. The rooftop restaurant is a must!", "lang": "en"},
            {"author": "Sophie C.", "rating": 4, "text": "Beautiful property with attentive staff. Only downside was slow elevator during peak hours.", "lang": "en"},
        ]
        results = []
        for i, r in enumerate(reviews):
            eid = _stable_id(tenant_id, "TRIPADVISOR", i)
            results.append({
                "type": "review",
                "external_id": eid,
                "source_type": "TRIPADVISOR",
                "author_name": r["author"],
                "rating": r["rating"],
                "text": r["text"],
                "language": r["lang"],
                "timestamp": (_now() - timedelta(days=i*4+2)).isoformat(),
                "is_stub": True,
            })
        return results


# ---- Registry ----
CONNECTOR_REGISTRY: Dict[str, ConnectorBase] = {
    "WEBCHAT": WebChatConnector(),
    "WHATSAPP": WhatsAppStubConnector(),
    "INSTAGRAM": InstagramStubConnector(),
    "GOOGLE_REVIEWS": GoogleReviewsStubConnector(),
    "TRIPADVISOR": TripAdvisorStubConnector(),
}

CONNECTOR_TYPES_META = [
    {"type": "WEBCHAT", "label": "Web Chat", "icon": "MessageSquare", "is_real": True, "credential_fields": []},
    {"type": "WHATSAPP", "label": "WhatsApp Business", "icon": "MessageCircle", "is_real": False, "credential_fields": ["phone_number_id", "access_token"]},
    {"type": "INSTAGRAM", "label": "Instagram DM", "icon": "Instagram", "is_real": False, "credential_fields": ["page_id", "access_token"]},
    {"type": "GOOGLE_REVIEWS", "label": "Google Reviews", "icon": "Star", "is_real": False, "credential_fields": ["place_id", "api_key"]},
    {"type": "TRIPADVISOR", "label": "TripAdvisor", "icon": "Award", "is_real": False, "credential_fields": ["location_id", "api_key"]},
]

def get_connector_instance(connector_type: str) -> Optional[ConnectorBase]:
    return CONNECTOR_REGISTRY.get(connector_type)
