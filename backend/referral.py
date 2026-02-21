"""Referral & Growth module with public landing page support and investor metrics"""
import uuid
import hashlib
from datetime import datetime, timezone

def now_utc():
    return datetime.now(timezone.utc)

def new_id():
    return str(uuid.uuid4())

def generate_referral_code(tenant_slug: str) -> str:
    """Generate a unique referral code from tenant slug"""
    hash_val = hashlib.md5(tenant_slug.encode()).hexdigest()[:6].upper()
    return f"REF-{hash_val}"

async def get_or_create_referral(db, tenant_id: str, tenant_slug: str) -> dict:
    existing = await db.referrals.find_one({"tenant_id": tenant_id})
    if existing:
        return existing
    
    referral = {
        "id": new_id(),
        "tenant_id": tenant_id,
        "code": generate_referral_code(tenant_slug),
        "clicks": 0,
        "signups": 0,
        "rewards_earned": 0,
        "reward_type": "ai_credits",
        "reward_amount": 50,
        "created_at": now_utc().isoformat()
    }
    await db.referrals.insert_one(referral)
    return referral

async def track_referral_click(db, code: str):
    await db.referrals.update_one({"code": code}, {"$inc": {"clicks": 1}})

async def track_referral_signup(db, code: str, new_tenant_id: str):
    referral = await db.referrals.find_one({"code": code})
    if referral:
        await db.referrals.update_one({"code": code}, {"$inc": {"signups": 1, "rewards_earned": 50}})
        # Award 50 extra AI credits to referrer
        await db.tenants.update_one(
            {"id": referral["tenant_id"]},
            {"$inc": {"plan_limits.monthly_ai_replies": 50}}
        )
        # Track referral event
        await db.referral_events.insert_one({
            "id": new_id(),
            "referrer_tenant_id": referral["tenant_id"],
            "referred_tenant_id": new_tenant_id,
            "code": code,
            "reward": 50,
            "reward_type": "ai_credits",
            "created_at": now_utc().isoformat()
        })
    return referral

async def get_referral_landing_data(db, referral_code: str) -> dict:
    """Get data for public referral landing page /r/{referralCode}"""
    referral = await db.referrals.find_one({"code": referral_code})
    if not referral:
        return None
    
    await track_referral_click(db, referral_code)
    
    tenant = await db.tenants.find_one({"id": referral["tenant_id"]}, {"_id": 0})
    tenant_name = tenant.get("name", "Kritik") if tenant else "Kritik"
    
    return {
        "referral_code": referral_code,
        "referrer_name": tenant_name,
        "reward_type": "ai_credits",
        "reward_amount": 50,
        "message": f"{tenant_name} sizi Kritik'e davet ediyor! Kaydolun ve 50 ucretsiz AI kredi kazanin.",
        "features": [
            "AI destekli misafir iletisimi",
            "Akilli rezervasyon yonetimi",
            "Cok kanalli mesajlasma (WhatsApp, Instagram, Web)",
            "Sadakat programi motoru",
            "Gercek zamanli analitik"
        ],
        "cta_text": "Ucretsiz Baslayın",
        "cta_url": f"/register?ref={referral_code}"
    }
