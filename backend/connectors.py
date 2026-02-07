# Connector stubs for omnichannel integration
import uuid
from datetime import datetime, timezone, timedelta
import random

def now_utc():
    return datetime.now(timezone.utc)

def new_id():
    return str(uuid.uuid4())

class BaseConnector:
    """Base connector interface - all connectors must implement these methods"""
    connector_type = "BASE"
    
    def __init__(self, credentials: dict = None):
        self.credentials = credentials or {}
    
    async def fetch_updates(self, tenant_id: str, since: datetime = None):
        """Fetch new messages/reviews since last check"""
        raise NotImplementedError
    
    async def send_message(self, tenant_id: str, to: str, content: str):
        """Send a message through this channel"""
        raise NotImplementedError
    
    async def post_reply(self, tenant_id: str, review_id: str, content: str):
        """Post a reply to a review"""
        raise NotImplementedError


class WhatsAppConnectorStub(BaseConnector):
    """WhatsApp Business connector stub - TODO: implement real Meta API calls"""
    connector_type = "WHATSAPP"
    
    async def fetch_updates(self, tenant_id: str, since: datetime = None):
        # TODO: Implement real WhatsApp Business API polling
        # Requires: WHATSAPP_BUSINESS_TOKEN, PHONE_NUMBER_ID from Meta
        names = ["Ahmed", "Maria", "John", "Ayşe", "Carlos"]
        messages_en = [
            "Hi, I'd like to book a room for this weekend",
            "What time is checkout?",
            "Is breakfast included in the room rate?",
            "Can I get a late checkout tomorrow?",
            "Thank you for a wonderful stay!"
        ]
        messages_tr = [
            "Merhaba, bu hafta sonu için oda ayırtmak istiyorum",
            "Çıkış saati kaçtır?",
            "Kahvaltı oda ücretine dahil mi?",
            "Yarın geç çıkış yapabilir miyim?",
            "Harika bir konaklama için teşekkürler!"
        ]
        msg_list = messages_en + messages_tr
        return [{
            "id": new_id(),
            "channel": "WHATSAPP",
            "from_name": random.choice(names),
            "from_phone": f"+9055{random.randint(10000000, 99999999)}",
            "content": random.choice(msg_list),
            "timestamp": now_utc().isoformat(),
            "is_stub": True
        }]
    
    async def send_message(self, tenant_id: str, to: str, content: str):
        # TODO: Implement real WhatsApp message sending
        return {"status": "stub_sent", "message_id": new_id(), "to": to}


class InstagramDMConnectorStub(BaseConnector):
    """Instagram DM connector stub - TODO: implement real Instagram Graph API"""
    connector_type = "INSTAGRAM"
    
    async def fetch_updates(self, tenant_id: str, since: datetime = None):
        # TODO: Implement real Instagram Graph API polling
        # Requires: INSTAGRAM_ACCESS_TOKEN, PAGE_ID
        names = ["@travel_lover", "@food_adventures", "@hotel_reviews", "@wanderlust99"]
        messages = [
            "Love your hotel! Can I book directly?",
            "What's the price for a deluxe room next month?",
            "Your restaurant looks amazing! Is reservation needed?",
            "Hi! Do you have any special offers?"
        ]
        return [{
            "id": new_id(),
            "channel": "INSTAGRAM",
            "from_name": random.choice(names),
            "from_handle": random.choice(names),
            "content": random.choice(messages),
            "timestamp": now_utc().isoformat(),
            "is_stub": True
        }]


class GoogleReviewsConnectorStub(BaseConnector):
    """Google Reviews connector stub - TODO: implement real Google My Business API"""
    connector_type = "GOOGLE_REVIEWS"
    
    async def fetch_updates(self, tenant_id: str, since: datetime = None):
        # TODO: Implement real Google My Business API
        # Requires: GOOGLE_API_KEY, PLACE_ID
        from rbac import FAKE_REVIEWS
        return [r for r in FAKE_REVIEWS if r["source"] == "GOOGLE_REVIEWS"]


class TripAdvisorConnectorStub(BaseConnector):
    """TripAdvisor connector stub - TODO: implement real TripAdvisor Content API"""
    connector_type = "TRIPADVISOR"
    
    async def fetch_updates(self, tenant_id: str, since: datetime = None):
        # TODO: Implement real TripAdvisor Content API
        # Requires: TRIPADVISOR_API_KEY, LOCATION_ID
        from rbac import FAKE_REVIEWS
        return [r for r in FAKE_REVIEWS if r["source"] == "TRIPADVISOR"]


# Connector registry
CONNECTOR_REGISTRY = {
    "WHATSAPP": WhatsAppConnectorStub,
    "INSTAGRAM": InstagramDMConnectorStub,
    "GOOGLE_REVIEWS": GoogleReviewsConnectorStub,
    "TRIPADVISOR": TripAdvisorConnectorStub,
}

def get_connector(connector_type: str, credentials: dict = None):
    cls = CONNECTOR_REGISTRY.get(connector_type)
    if cls:
        return cls(credentials)
    return None


# Stripe stub provider
class StripeStubProvider:
    """Mock payment provider - TODO: implement real Stripe API"""
    
    @staticmethod
    def create_payment_link(amount: float, currency: str = "TRY", description: str = ""):
        """Create a mock payment link"""
        link_id = new_id()
        return {
            "id": link_id,
            "url": f"https://pay.stripe.stub/pay/{link_id}",
            "amount": amount,
            "currency": currency,
            "description": description,
            "status": "pending",
            "created_at": now_utc().isoformat(),
            "is_stub": True
        }
    
    @staticmethod
    def simulate_payment_success(link_id: str):
        """Simulate a successful payment"""
        return {
            "payment_id": new_id(),
            "link_id": link_id,
            "status": "succeeded",
            "paid_at": now_utc().isoformat(),
            "is_stub": True
        }
