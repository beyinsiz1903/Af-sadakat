"""GDPR/KVKK Compliance module: export, delete, anonymize, consent, retention auto-cleanup"""
import uuid
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

def now_utc():
    return datetime.now(timezone.utc)

def new_id():
    return str(uuid.uuid4())

async def export_guest_data(db, tenant_id: str, contact_id: str) -> dict:
    """Export all data related to a contact (Right of Access / KVKK Bilgi Edinme)"""
    contact = await db.contacts.find_one({"id": contact_id, "tenant_id": tenant_id}, {"_id": 0})
    if not contact:
        return None
    
    phone = contact.get("phone", "")
    email = contact.get("email", "")
    
    bundle = {
        "export_metadata": {
            "exported_at": now_utc().isoformat(),
            "contact_id": contact_id,
            "tenant_id": tenant_id,
            "format_version": "2.0"
        },
        "contact": contact,
        "requests": [],
        "orders": [],
        "messages": [],
        "loyalty": None,
        "consent_logs": [],
        "reservations": [],
        "reviews": [],
        "gamification": None
    }
    
    if phone:
        reqs = await db.guest_requests.find({"tenant_id": tenant_id, "guest_phone": phone}, {"_id": 0}).to_list(500)
        bundle["requests"] = reqs
        ords = await db.orders.find({"tenant_id": tenant_id, "guest_phone": phone}, {"_id": 0}).to_list(500)
        bundle["orders"] = ords
        reservations = await db.reservations.find({"tenant_id": tenant_id, "guest_phone": phone}, {"_id": 0}).to_list(100)
        bundle["reservations"] = reservations
    
    # Messages from conversations
    if phone or email:
        convs = await db.conversations.find({"tenant_id": tenant_id, "$or": [{"guest_phone": phone}, {"guest_email": email}]}, {"_id": 0}).to_list(50)
        for conv in convs:
            msgs = await db.messages.find({"conversation_id": conv["id"]}, {"_id": 0}).to_list(500)
            bundle["messages"].extend(msgs)
    
    if contact.get("loyalty_account_id"):
        account = await db.loyalty_accounts.find_one({"id": contact["loyalty_account_id"]}, {"_id": 0})
        ledger = await db.loyalty_ledger.find({"account_id": contact["loyalty_account_id"]}, {"_id": 0}).to_list(500)
        bundle["loyalty"] = {"account": account, "ledger": ledger}
    
    # Gamification data
    badges = await db.member_badges.find({"contact_id": contact_id}, {"_id": 0}).to_list(100)
    if badges:
        bundle["gamification"] = {"earned_badges": badges}
    
    # Reviews
    if contact.get("name"):
        reviews = await db.reviews.find({"tenant_id": tenant_id, "guest_name": contact["name"]}, {"_id": 0}).to_list(100)
        bundle["reviews"] = reviews
    
    consent_logs = await db.consent_logs.find({"contact_id": contact_id}, {"_id": 0}).to_list(100)
    bundle["consent_logs"] = consent_logs
    
    # Log the export
    await db.consent_logs.insert_one({
        "id": new_id(), "tenant_id": tenant_id, "contact_id": contact_id,
        "action": "data_export", "granted": True, "source": "admin",
        "details": {"exported_at": now_utc().isoformat(), "record_count": sum(len(v) for v in bundle.values() if isinstance(v, list))},
        "created_at": now_utc().isoformat()
    })
    
    return bundle

async def forget_guest(db, tenant_id: str, contact_id: str) -> dict:
    """Right to be forgotten / KVKK Unutulma Hakki - anonymize all guest data"""
    contact = await db.contacts.find_one({"id": contact_id, "tenant_id": tenant_id})
    if not contact:
        return None
    
    phone = contact.get("phone", "")
    email = contact.get("email", "")
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
        await db.reservations.update_many(
            {"tenant_id": tenant_id, "guest_phone": phone},
            {"$set": {"guest_name": anon_name, "guest_phone": "", "guest_email": ""}}
        )
    
    # Anonymize conversations/messages
    if phone or email:
        await db.conversations.update_many(
            {"tenant_id": tenant_id, "$or": [{"guest_phone": phone}, {"guest_email": email}]},
            {"$set": {"guest_name": anon_name, "guest_phone": "", "guest_email": ""}}
        )
    
    # Remove loyalty data
    if contact.get("loyalty_account_id"):
        await db.loyalty_accounts.update_one(
            {"id": contact["loyalty_account_id"]},
            {"$set": {"name": anon_name, "phone": "", "email": "", "anonymized": True}}
        )
    
    # Log
    await db.consent_logs.insert_one({
        "id": new_id(), "tenant_id": tenant_id, "contact_id": contact_id,
        "action": "right_to_forget", "granted": True, "source": "admin",
        "details": {"anonymized_at": now_utc().isoformat()},
        "created_at": now_utc().isoformat()
    })
    
    return {"status": "anonymized", "contact_id": contact_id, "anonymized_name": anon_name}

async def log_consent(db, tenant_id: str, contact_id: str, consent_type: str, granted: bool, source: str = "guest_panel"):
    """Log consent event (KVKK Riza Kaydi)"""
    doc = {
        "id": new_id(), "tenant_id": tenant_id, "contact_id": contact_id,
        "action": f"consent_{consent_type}", "granted": granted, "source": source,
        "details": {"consent_type": consent_type, "granted": granted, "ip": "", "user_agent": ""},
        "created_at": now_utc().isoformat()
    }
    await db.consent_logs.insert_one(doc)
    return doc

async def retention_auto_cleanup(db, tenant_id: str = None):
    """Automatically purge data older than retention period for tenants with auto_purge enabled.
    KVKK Saklama Suresi Politikasi - Otomatik Temizlik"""
    query = {"auto_purge": True}
    if tenant_id:
        query["tenant_id"] = tenant_id
    
    policies = await db.retention_policies.find(query, {"_id": 0}).to_list(100)
    results = []
    
    for policy in policies:
        tid = policy["tenant_id"]
        months = policy.get("retention_months", 24)
        cutoff = (now_utc() - timedelta(days=months * 30)).isoformat()
        
        # Find contacts to anonymize
        old_contacts = await db.contacts.find({
            "tenant_id": tid,
            "anonymized": {"$ne": True},
            "created_at": {"$lt": cutoff},
            "$or": [
                {"last_activity_at": {"$lt": cutoff}},
                {"last_activity_at": {"$exists": False}}
            ]
        }, {"_id": 0, "id": 1}).to_list(500)
        
        anonymized_count = 0
        for contact in old_contacts:
            await forget_guest(db, tid, contact["id"])
            anonymized_count += 1
        
        # Clean old audit logs (keep last 12 months regardless)
        audit_cutoff = (now_utc() - timedelta(days=365)).isoformat()
        audit_result = await db.audit_logs.delete_many({
            "tenant_id": tid,
            "created_at": {"$lt": audit_cutoff}
        })
        
        result = {
            "tenant_id": tid,
            "retention_months": months,
            "contacts_anonymized": anonymized_count,
            "audit_logs_deleted": audit_result.deleted_count,
            "processed_at": now_utc().isoformat()
        }
        results.append(result)
        
        # Log cleanup
        await db.consent_logs.insert_one({
            "id": new_id(), "tenant_id": tid, "contact_id": "system",
            "action": "retention_auto_cleanup", "granted": True, "source": "scheduler",
            "details": result,
            "created_at": now_utc().isoformat()
        })
    
    logger.info(f"Retention auto-cleanup: processed {len(results)} tenants")
    return results
