"""GDPR/KVKK Compliance module: export, delete, anonymize, consent, retention"""
import uuid
from datetime import datetime, timezone

def now_utc():
    return datetime.now(timezone.utc)

def new_id():
    return str(uuid.uuid4())

async def export_guest_data(db, tenant_id: str, contact_id: str) -> dict:
    """Export all data related to a contact (Right of Access)"""
    contact = await db.contacts.find_one({"id": contact_id, "tenant_id": tenant_id}, {"_id": 0})
    if not contact:
        return None
    
    phone = contact.get("phone", "")
    email = contact.get("email", "")
    
    bundle = {"contact": contact, "requests": [], "orders": [], "messages": [], "loyalty": None, "consent_logs": []}
    
    if phone:
        reqs = await db.guest_requests.find({"tenant_id": tenant_id, "guest_phone": phone}, {"_id": 0}).to_list(500)
        bundle["requests"] = reqs
        ords = await db.orders.find({"tenant_id": tenant_id, "guest_phone": phone}, {"_id": 0}).to_list(500)
        bundle["orders"] = ords
    
    if contact.get("loyalty_account_id"):
        account = await db.loyalty_accounts.find_one({"id": contact["loyalty_account_id"]}, {"_id": 0})
        ledger = await db.loyalty_ledger.find({"account_id": contact["loyalty_account_id"]}, {"_id": 0}).to_list(500)
        bundle["loyalty"] = {"account": account, "ledger": ledger}
    
    consent_logs = await db.consent_logs.find({"contact_id": contact_id}, {"_id": 0}).to_list(100)
    bundle["consent_logs"] = consent_logs
    
    # Log the export
    await db.consent_logs.insert_one({
        "id": new_id(), "tenant_id": tenant_id, "contact_id": contact_id,
        "action": "data_export", "details": {"exported_at": now_utc().isoformat()},
        "created_at": now_utc().isoformat()
    })
    
    return bundle

async def forget_guest(db, tenant_id: str, contact_id: str) -> dict:
    """Right to be forgotten - anonymize all guest data"""
    contact = await db.contacts.find_one({"id": contact_id, "tenant_id": tenant_id})
    if not contact:
        return None
    
    phone = contact.get("phone", "")
    anon_name = f"ANON-{contact_id[:8]}"
    
    # Anonymize contact
    await db.contacts.update_one({"id": contact_id}, {"$set": {
        "name": anon_name, "phone": "", "email": "",
        "tags": [], "notes": "[ANONYMIZED]",
        "consent_marketing": False, "anonymized": True,
        "anonymized_at": now_utc().isoformat()
    }})
    
    # Anonymize requests
    if phone:
        await db.guest_requests.update_many(
            {"tenant_id": tenant_id, "guest_phone": phone},
            {"$set": {"guest_name": anon_name, "guest_phone": "", "guest_email": ""}}
        )
        await db.orders.update_many(
            {"tenant_id": tenant_id, "guest_phone": phone},
            {"$set": {"guest_name": anon_name, "guest_phone": "", "guest_email": ""}}
        )
    
    # Log
    await db.consent_logs.insert_one({
        "id": new_id(), "tenant_id": tenant_id, "contact_id": contact_id,
        "action": "right_to_forget", "details": {"anonymized_at": now_utc().isoformat()},
        "created_at": now_utc().isoformat()
    })
    
    return {"status": "anonymized", "contact_id": contact_id}

async def log_consent(db, tenant_id: str, contact_id: str, consent_type: str, granted: bool, source: str = "guest_panel"):
    """Log consent event"""
    return await db.consent_logs.insert_one({
        "id": new_id(), "tenant_id": tenant_id, "contact_id": contact_id,
        "action": f"consent_{consent_type}", "granted": granted, "source": source,
        "details": {"consent_type": consent_type, "granted": granted},
        "created_at": now_utc().isoformat()
    })
