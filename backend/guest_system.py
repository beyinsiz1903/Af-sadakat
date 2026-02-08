"""Guest Token System + QR Generation + Connector Polling + Fernet Vault"""
import jwt
import io
import qrcode
from datetime import datetime, timezone, timedelta
from cryptography.fernet import Fernet
import base64
import hashlib
import os
import asyncio
import logging

logger = logging.getLogger(__name__)

# ---- Guest JWT Tokens ----
GUEST_JWT_SECRET = os.environ.get("GUEST_JWT_SECRET", "guest-token-secret-change-in-prod")
GUEST_TOKEN_EXPIRY_MINUTES = 30

def create_guest_token(tenant_id: str, room_id: str = None, table_id: str = None, 
                        contact_id: str = None, room_code: str = None, table_code: str = None) -> str:
    payload = {
        "type": "guest",
        "tenant_id": tenant_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=GUEST_TOKEN_EXPIRY_MINUTES),
        "iat": datetime.now(timezone.utc)
    }
    if room_id:
        payload["room_id"] = room_id
        payload["room_code"] = room_code or ""
    if table_id:
        payload["table_id"] = table_id
        payload["table_code"] = table_code or ""
    if contact_id:
        payload["contact_id"] = contact_id
    return jwt.encode(payload, GUEST_JWT_SECRET, algorithm="HS256")

def decode_guest_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, GUEST_JWT_SECRET, algorithms=["HS256"])
        if payload.get("type") != "guest":
            raise ValueError("Not a guest token")
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Guest token expired")
    except jwt.InvalidTokenError:
        raise ValueError("Invalid guest token")


# ---- QR Code Generation ----
def generate_qr_png(url: str, size: int = 300) -> bytes:
    """Generate QR code PNG bytes for a URL"""
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()

def generate_qr_print_pdf(items: list, title: str = "QR Codes") -> bytes:
    """Generate a printable PDF with QR codes in a grid layout
    items: list of {"label": str, "url": str}
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import ImageReader
    
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    
    margin = 20 * mm
    cols = 3
    rows = 4
    cell_w = (width - 2 * margin) / cols
    cell_h = (height - 2 * margin - 15 * mm) / rows
    qr_size = min(cell_w, cell_h) - 15 * mm
    
    c.setFont("Helvetica-Bold", 14)
    c.drawString(margin, height - 15 * mm, title)
    
    for idx, item in enumerate(items):
        page_idx = idx % (cols * rows)
        if idx > 0 and page_idx == 0:
            c.showPage()
            c.setFont("Helvetica-Bold", 14)
            c.drawString(margin, height - 15 * mm, title)
        
        row = page_idx // cols
        col = page_idx % cols
        
        x = margin + col * cell_w
        y = height - margin - 15 * mm - (row + 1) * cell_h
        
        # Generate QR
        qr_bytes = generate_qr_png(item["url"])
        qr_img = ImageReader(io.BytesIO(qr_bytes))
        
        # Draw QR
        c.drawImage(qr_img, x + (cell_w - qr_size) / 2, y + 10 * mm, width=qr_size, height=qr_size)
        
        # Draw label
        c.setFont("Helvetica-Bold", 10)
        c.drawCentredString(x + cell_w / 2, y + 5 * mm, item["label"])
    
    c.save()
    buf.seek(0)
    return buf.getvalue()


# ---- Fernet Credential Vault ----
def _get_fernet_key() -> bytes:
    """Derive Fernet key from VAULT_MASTER_KEY env var"""
    master = os.environ.get("VAULT_MASTER_KEY", "default-vault-key-change-in-prod")
    # Derive a valid Fernet key (32 bytes base64)
    key = hashlib.sha256(master.encode()).digest()
    return base64.urlsafe_b64encode(key)

def encrypt_credentials(data: str) -> str:
    """Encrypt credential JSON string using Fernet"""
    f = Fernet(_get_fernet_key())
    return f.encrypt(data.encode()).decode()

def decrypt_credentials(encrypted: str) -> str:
    """Decrypt credential JSON string"""
    f = Fernet(_get_fernet_key())
    return f.decrypt(encrypted.encode()).decode()


# ---- Connector Polling Background Task ----
class ConnectorPollingTask:
    """Background task that polls stub connectors periodically"""
    
    def __init__(self, db):
        self.db = db
        self.running = False
        self.interval = 60  # seconds
    
    async def start(self):
        self.running = True
        logger.info("Connector polling task started")
        while self.running:
            try:
                await self._poll_all()
            except Exception as e:
                logger.error(f"Polling error: {e}")
            await asyncio.sleep(self.interval)
    
    async def stop(self):
        self.running = False
    
    async def _poll_all(self):
        """Poll all enabled connectors for all tenants"""
        from connectors.registry import get_connector_instance as get_connector
        
        credentials = await self.db.connector_credentials.find(
            {"enabled": True, "connector_type": {"$ne": "WEBCHAT"}}
        ).to_list(100)
        
        for cred in credentials:
            try:
                connector = get_connector(cred["connector_type"])
                if connector:
                    updates = await connector.fetch_updates(cred["tenant_id"])
                    if updates:
                        # Store as stub messages/reviews depending on type
                        now = datetime.now(timezone.utc).isoformat()
                        await self.db.connector_credentials.update_one(
                            {"_id": cred["_id"]},
                            {"$set": {"last_sync_at": now, "status": "synced"}}
                        )
            except Exception as e:
                logger.warning(f"Poll {cred['connector_type']} for tenant {cred['tenant_id']}: {e}")
