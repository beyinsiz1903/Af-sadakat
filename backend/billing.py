"""Billing module: models, subscription lifecycle, invoice stubs, usage meter, Stripe webhook"""
import uuid
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

def now_utc():
    return datetime.now(timezone.utc)

def new_id():
    return str(uuid.uuid4())

def create_billing_account(tenant_id: str, plan: str = "basic"):
    return {
        "id": new_id(),
        "tenant_id": tenant_id,
        "plan": plan,
        "status": "active",
        "payment_method": None,
        "stripe_customer_id": None,
        "billing_email": None,
        "billing_address": None,
        "tax_id": None,
        "currency": "USD",
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat()
    }

def create_payment_method(tenant_id: str, method_type: str = "card", last4: str = "4242", brand: str = "visa"):
    return {
        "id": new_id(),
        "tenant_id": tenant_id,
        "type": method_type,
        "last4": last4,
        "brand": brand,
        "exp_month": 12,
        "exp_year": 2027,
        "is_default": True,
        "stripe_payment_method_id": None,
        "created_at": now_utc().isoformat()
    }

def create_subscription(tenant_id: str, plan: str = "basic"):
    return {
        "id": new_id(),
        "tenant_id": tenant_id,
        "plan": plan,
        "status": "active",
        "current_period_start": now_utc().isoformat(),
        "current_period_end": (now_utc() + timedelta(days=30)).isoformat(),
        "trial_ends_at": (now_utc() + timedelta(days=14)).isoformat(),
        "cancel_at_period_end": False,
        "stripe_subscription_id": None,
        "created_at": now_utc().isoformat()
    }

def create_invoice(tenant_id: str, plan: str, amount: float, status: str = "paid"):
    return {
        "id": new_id(),
        "tenant_id": tenant_id,
        "invoice_number": f"INV-{new_id()[:8].upper()}",
        "plan": plan,
        "amount": amount,
        "currency": "USD",
        "status": status,
        "period_start": (now_utc() - timedelta(days=30)).isoformat(),
        "period_end": now_utc().isoformat(),
        "paid_at": now_utc().isoformat() if status == "paid" else None,
        "stripe_invoice_id": None,
        "created_at": now_utc().isoformat()
    }

def generate_mock_invoices(tenant_id: str, plan: str):
    """Generate mock invoice history"""
    from security import PLAN_LIMITS
    price = PLAN_LIMITS.get(plan, {}).get("price_monthly", 49)
    invoices = []
    for i in range(3):
        inv = create_invoice(tenant_id, plan, price, "paid")
        inv["period_start"] = (now_utc() - timedelta(days=30*(i+1))).isoformat()
        inv["period_end"] = (now_utc() - timedelta(days=30*i)).isoformat()
        inv["created_at"] = (now_utc() - timedelta(days=30*i)).isoformat()
        invoices.append(inv)
    return invoices

# ---- Usage Meter ----
class UsageMeter:
    """Tracks resource usage per tenant and enforces plan limits.
    Provides monthly reset functionality."""
    
    @staticmethod
    async def get_usage_snapshot(db, tenant_id: str, plan: str) -> dict:
        """Get current usage vs limits for all tracked metrics"""
        from security import get_plan_limits
        limits = get_plan_limits(plan)
        
        tenant = await db.tenants.find_one({"id": tenant_id})
        usage = tenant.get("usage_counters", {}) if tenant else {}
        
        contacts = await db.contacts.count_documents({"tenant_id": tenant_id})
        active_offers = await db.offers.count_documents({"tenant_id": tenant_id, "status": {"$in": ["draft", "sent"]}})
        reservations_this_month = await db.reservations.count_documents({
            "tenant_id": tenant_id,
            "created_at": {"$gte": now_utc().replace(day=1).isoformat()}
        })
        
        return {
            "users": {"current": usage.get("users", 1), "limit": limits["max_users"], "pct": round(usage.get("users", 1) / max(limits["max_users"], 1) * 100, 1)},
            "rooms": {"current": usage.get("rooms", 0), "limit": limits["max_rooms"], "pct": round(usage.get("rooms", 0) / max(limits["max_rooms"], 1) * 100, 1)},
            "tables": {"current": usage.get("tables", 0), "limit": limits["max_tables"], "pct": round(usage.get("tables", 0) / max(limits["max_tables"], 1) * 100, 1)},
            "contacts": {"current": contacts, "limit": limits["max_contacts"], "pct": round(contacts / max(limits["max_contacts"], 1) * 100, 1)},
            "ai_replies": {"current": usage.get("ai_replies_this_month", 0), "limit": limits["monthly_ai_replies"], "pct": round(usage.get("ai_replies_this_month", 0) / max(limits["monthly_ai_replies"], 1) * 100, 1)},
            "reservations": {"current": reservations_this_month, "limit": limits["max_monthly_reservations"], "pct": round(reservations_this_month / max(limits["max_monthly_reservations"], 1) * 100, 1)},
            "active_offers": {"current": active_offers, "limit": limits["max_active_offers"], "pct": round(active_offers / max(limits["max_active_offers"], 1) * 100, 1)},
        }
    
    @staticmethod
    async def check_and_enforce(db, tenant_id: str, plan: str, metric: str) -> dict:
        """Check if a metric is within limits. Returns {allowed, current, limit, pct}"""
        snapshot = await UsageMeter.get_usage_snapshot(db, tenant_id, plan)
        m = snapshot.get(metric, {"current": 0, "limit": 999, "pct": 0})
        return {
            "allowed": m["current"] < m["limit"],
            "current": m["current"],
            "limit": m["limit"],
            "pct": m["pct"],
            "metric": metric
        }
    
    @staticmethod
    async def monthly_reset(db):
        """Reset monthly counters for all tenants (ai_replies, reservations)"""
        result = await db.tenants.update_many(
            {},
            {"$set": {
                "usage_counters.ai_replies_this_month": 0,
                "usage_counters.monthly_reset_at": now_utc().isoformat()
            }}
        )
        logger.info(f"UsageMeter monthly reset: {result.modified_count} tenants reset")
        
        # Log the reset
        await db.audit_logs.insert_one({
            "id": new_id(),
            "tenant_id": "system",
            "action": "usage_monthly_reset",
            "entity_type": "system",
            "entity_id": "all",
            "details": {"tenants_reset": result.modified_count},
            "created_at": now_utc().isoformat()
        })
        return result.modified_count

usage_meter = UsageMeter()

# ---- Stripe Webhook Event Types ----
STRIPE_EVENT_TYPES = {
    "checkout.session.completed": "handle_checkout_complete",
    "invoice.paid": "handle_invoice_paid",
    "invoice.payment_failed": "handle_invoice_failed",
    "customer.subscription.updated": "handle_subscription_updated",
    "customer.subscription.deleted": "handle_subscription_deleted",
    "payment_intent.succeeded": "handle_payment_succeeded",
    "payment_intent.payment_failed": "handle_payment_failed",
}

async def handle_stripe_webhook(db, event_type: str, event_data: dict) -> dict:
    """Process Stripe webhook events (stub - ready for real Stripe integration)"""
    handler = STRIPE_EVENT_TYPES.get(event_type)
    if not handler:
        logger.warning(f"Unhandled Stripe event type: {event_type}")
        return {"status": "ignored", "event_type": event_type}
    
    # Log the event
    await db.stripe_events.insert_one({
        "id": new_id(),
        "event_type": event_type,
        "handler": handler,
        "data": event_data,
        "processed": True,
        "created_at": now_utc().isoformat()
    })
    
    # Stub handlers - in production, these would update billing state
    if event_type == "invoice.paid":
        customer_id = event_data.get("customer", "")
        amount = event_data.get("amount_paid", 0)
        await db.billing_accounts.update_one(
            {"stripe_customer_id": customer_id},
            {"$set": {"status": "active", "last_payment_at": now_utc().isoformat()}}
        )
    elif event_type == "customer.subscription.deleted":
        customer_id = event_data.get("customer", "")
        await db.subscriptions.update_one(
            {"stripe_customer_id": customer_id},
            {"$set": {"status": "cancelled", "cancelled_at": now_utc().isoformat()}}
        )
    
    return {"status": "processed", "event_type": event_type, "handler": handler}
