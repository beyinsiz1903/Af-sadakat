"""Guest Loyalty Router: OTP send/verify, device-based auto-recognition,
loyalty enrollment, and admin-side ledger/account listing.
Extracted from server.py for maintainability.
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import os
import random as _random
import secrets as _secrets
import logging

from core.config import db
from core.tenant_guard import serialize_doc, new_id, now_utc
from core.legacy_helpers import (
    get_tenant_by_slug,
    upsert_contact as _upsert_contact,
    normalize_phone as _phone_normalize,
)

logger = logging.getLogger("omnihub.guest_loyalty")
router = APIRouter(prefix="/api", tags=["guest-loyalty"])


@router.post("/g/{tenant_slug}/loyalty/send-otp")
async def send_loyalty_otp(tenant_slug: str, data: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    phone = _phone_normalize(data.get("phone", ""))
    if not phone or len(phone) < 7:
        raise HTTPException(status_code=400, detail="Valid phone required")

    last = await db.otp_codes.find_one(
        {"phone": phone, "tenant_id": tenant["id"]}, sort=[("created_at", -1)]
    )
    if last and (now_utc() - datetime.fromisoformat(
            last["created_at"].replace("Z", "+00:00"))).total_seconds() < 60:
        raise HTTPException(status_code=429, detail="Please wait before requesting another code")

    otp_code = str(_random.randint(100000, 999999))
    expires_at = (now_utc() + timedelta(minutes=5)).isoformat()

    await db.otp_codes.delete_many({"phone": phone, "tenant_id": tenant["id"]})
    await db.otp_codes.insert_one({
        "id": new_id(), "tenant_id": tenant["id"], "phone": phone,
        "code": otp_code, "verified": False, "attempts": 0,
        "created_at": now_utc().isoformat(), "expires_at": expires_at,
    })

    sms_sent = False
    try:
        from services.notification_engine import send_sms
        sms_sent = await send_sms(phone, f"OmniHub dogrulama kodunuz: {otp_code}")
    except Exception as e:
        logger.warning(f"SMS send failed: {e}")

    if sms_sent:
        return {"sent": True, "message": "OTP sent via SMS"}

    if (os.environ.get("ENV", "development").lower() == "production"
            and os.environ.get("ALLOW_OTP_STUB", "false").lower() != "true"):
        raise HTTPException(status_code=503, detail="SMS service unavailable")
    return {"sent": True, "otp_stub": otp_code, "message": "OTP sent (stub - SMS not configured)"}


@router.post("/g/{tenant_slug}/loyalty/verify-otp")
async def verify_loyalty_otp(tenant_slug: str, data: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    phone = _phone_normalize(data.get("phone", ""))
    code = (data.get("code") or "").strip()
    if not phone or not code:
        raise HTTPException(status_code=400, detail="Phone and code required")

    record = await db.otp_codes.find_one({
        "tenant_id": tenant["id"], "phone": phone, "verified": False
    })
    if not record:
        raise HTTPException(status_code=400, detail="No OTP found. Please request a new one.")

    if record.get("attempts", 0) >= 5:
        await db.otp_codes.delete_many({"id": record["id"]})
        raise HTTPException(status_code=429, detail="Too many attempts. Please request a new code.")

    if record.get("expires_at") and record["expires_at"] < now_utc().isoformat():
        raise HTTPException(status_code=400, detail="OTP expired. Please request a new one.")

    if record["code"] != code:
        await db.otp_codes.update_one({"id": record["id"]}, {"$inc": {"attempts": 1}})
        raise HTTPException(status_code=400, detail="Invalid OTP code")

    device_token = _secrets.token_urlsafe(32)
    await db.guest_devices.insert_one({
        "id": new_id(), "tenant_id": tenant["id"], "phone": phone,
        "device_token": device_token,
        "created_at": now_utc().isoformat(),
        "expires_at": (now_utc() + timedelta(days=90)).isoformat(),
        "user_agent": data.get("user_agent", ""),
    })
    await db.otp_codes.update_one({"id": record["id"]}, {"$set": {"verified": True}})
    return {"verified": True, "device_token": device_token, "message": "Phone verified successfully"}


@router.post("/g/{tenant_slug}/loyalty/resolve-device")
async def resolve_device(tenant_slug: str, data: dict):
    """Auto-recognize a returning guest by their stored device_token."""
    tenant = await get_tenant_by_slug(tenant_slug)
    token = (data.get("device_token") or "").strip()
    if not token:
        raise HTTPException(status_code=400, detail="device_token required")
    rec = await db.guest_devices.find_one({"tenant_id": tenant["id"], "device_token": token})
    if not rec:
        raise HTTPException(status_code=404, detail="Device not recognized")
    if rec.get("expires_at") and rec["expires_at"] < now_utc().isoformat():
        raise HTTPException(status_code=410, detail="Device token expired")
    contact = await db.contacts.find_one({"tenant_id": tenant["id"], "phone": rec["phone"]})
    if not contact:
        raise HTTPException(status_code=404, detail="No matching guest profile")
    return {
        "contact_id": contact["id"],
        "name": contact.get("name"),
        "phone": contact.get("phone"),
        "loyalty_account_id": contact.get("loyalty_account_id"),
    }


@router.post("/g/{tenant_slug}/loyalty/join")
async def join_loyalty(tenant_slug: str, data: dict):
    tenant = await get_tenant_by_slug(tenant_slug)
    phone = _phone_normalize(data.get("phone", ""))
    email = (data.get("email") or "").strip().lower()
    name = data.get("name", data.get("guest_name", ""))

    if not phone and not email:
        raise HTTPException(status_code=400, detail="Phone or email required")

    otp_verified = False
    if phone:
        otp_record = await db.otp_codes.find_one({
            "tenant_id": tenant["id"], "phone": phone, "verified": True
        })
        if not otp_record:
            raise HTTPException(status_code=403, detail="Phone not verified. Please verify OTP first.")
        otp_verified = True
        await db.otp_codes.delete_many({"tenant_id": tenant["id"], "phone": phone})

    contact = await _upsert_contact(tenant["id"], name, phone, email)

    existing = await db.loyalty_accounts.find_one(
        {"tenant_id": tenant["id"], "contact_id": contact["id"]}
    )
    if existing:
        return {**serialize_doc(existing), "contact_id": contact["id"], "otp_verified": otp_verified}

    account = {
        "id": new_id(),
        "tenant_id": tenant["id"],
        "contact_id": contact["id"],
        "contact_name": name,
        "contact_phone": phone,
        "contact_email": email,
        "points": 0,
        "tier": "bronze",
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat(),
    }
    await db.loyalty_accounts.insert_one(account)
    await db.contacts.update_one(
        {"id": contact["id"]}, {"$set": {"loyalty_account_id": account["id"]}}
    )

    return {**serialize_doc(account), "contact_id": contact["id"], "otp_verified": otp_verified}


@router.get("/tenants/{tenant_slug}/loyalty/accounts")
async def list_loyalty_accounts(tenant_slug: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    accounts = await db.loyalty_accounts.find(
        {"tenant_id": tenant["id"]}, {"_id": 0}
    ).to_list(200)
    return [serialize_doc(a) for a in accounts]


@router.get("/tenants/{tenant_slug}/loyalty/{account_id}/ledger")
async def get_loyalty_ledger(tenant_slug: str, account_id: str):
    tenant = await get_tenant_by_slug(tenant_slug)
    entries = await db.loyalty_ledger.find(
        {"tenant_id": tenant["id"], "account_id": account_id}, {"_id": 0}
    ).sort("created_at", -1).to_list(200)
    return [serialize_doc(e) for e in entries]
