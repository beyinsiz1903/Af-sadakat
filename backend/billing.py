"""Billing module: models, subscription lifecycle, invoice stubs"""
import uuid
from datetime import datetime, timezone, timedelta

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
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat()
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
