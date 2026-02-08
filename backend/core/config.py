"""Core configuration and database setup"""
import os
from pathlib import Path
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

ROOT_DIR = Path(__file__).parent.parent
load_dotenv(ROOT_DIR / '.env')

# Database
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'omni_inbox_hub')]

# JWT
JWT_SECRET = os.environ.get("JWT_SECRET", "omni-inbox-hub-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24
GUEST_JWT_SECRET = os.environ.get("GUEST_JWT_SECRET", "guest-token-secret-change-in-prod")
VAULT_MASTER_KEY = os.environ.get("VAULT_MASTER_KEY", "vault-master-key-change-in-prod")
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "https://property-payments-1.preview.emergentagent.com")
