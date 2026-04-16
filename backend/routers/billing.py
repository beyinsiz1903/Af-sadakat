from fastapi import APIRouter, HTTPException, Request
import logging

from core.config import db
from core.tenant_guard import resolve_tenant, serialize_doc, new_id, now_utc, log_audit
from security import PLAN_LIMITS, get_plan_limits
from billing import create_billing_account, create_subscription, generate_mock_invoices, usage_meter, handle_stripe_webhook, create_payment_method

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["billing"])

@router.get("/plans")
async def get_plans_v2():
    return PLAN_LIMITS

@router.get("/tenants/{tenant_slug}/billing")
async def get_billing_v2(tenant_slug: str):
    tenant = await resolve_tenant(tenant_slug)
    billing = await db.billing_accounts.find_one({"tenant_id": tenant["id"]}, {"_id": 0})
    if not billing:
        billing = create_billing_account(tenant["id"], tenant.get("plan", "basic"))
        await db.billing_accounts.insert_one(billing)

    subscription = await db.subscriptions.find_one({"tenant_id": tenant["id"]}, {"_id": 0})
    if not subscription:
        subscription = create_subscription(tenant["id"], tenant.get("plan", "basic"))
        await db.subscriptions.insert_one(subscription)

    invoices = await db.invoices.find({"tenant_id": tenant["id"]}, {"_id": 0}).sort("created_at", -1).to_list(20)
    if not invoices:
        invoices = generate_mock_invoices(tenant["id"], tenant.get("plan", "basic"))
        if invoices:
            await db.invoices.insert_many(invoices)

    return {
        "billing_account": serialize_doc(billing),
        "subscription": serialize_doc(subscription),
        "invoices": [serialize_doc(i) for i in invoices],
        "plan": tenant.get("plan", "basic"),
        "plan_details": get_plan_limits(tenant.get("plan", "basic"))
    }

@router.post("/billing/webhook/stripe")
async def stripe_webhook_v2(data: dict, request: Request = None):
    event_type = data.get("type", "unknown")
    event_data = data.get("data", {}).get("object", {})
    logger.info(f"Stripe webhook received: {event_type}")
    result = await handle_stripe_webhook(db, event_type, event_data)
    await log_audit("system", f"stripe_webhook_{event_type}", "billing", "webhook", details=result)
    return result

@router.get("/tenants/{tenant_slug}/usage/detailed")
async def get_detailed_usage_v2(tenant_slug: str):
    tenant = await resolve_tenant(tenant_slug)
    plan = tenant.get("plan", "basic")
    return {
        "plan": plan,
        "plan_label": get_plan_limits(plan).get("label", plan),
        "metrics": await usage_meter.get_usage_snapshot(db, tenant["id"], plan),
        "features": get_plan_limits(plan).get("features", []),
        "plan_limits": get_plan_limits(plan)
    }

@router.post("/tenants/{tenant_slug}/billing/payment-method")
async def add_payment_method_v2(tenant_slug: str, data: dict):
    tenant = await resolve_tenant(tenant_slug)
    pm = create_payment_method(tenant["id"], data.get("type", "card"), data.get("last4", "4242"), data.get("brand", "visa"))
    await db.payment_methods.insert_one(pm)
    await db.billing_accounts.update_one(
        {"tenant_id": tenant["id"]},
        {"$set": {"payment_method": pm["id"], "updated_at": now_utc().isoformat()}}
    )
    return serialize_doc(pm)

@router.get("/tenants/{tenant_slug}/billing/payment-methods")
async def list_payment_methods_v2(tenant_slug: str):
    tenant = await resolve_tenant(tenant_slug)
    methods = await db.payment_methods.find({"tenant_id": tenant["id"]}, {"_id": 0}).to_list(10)
    return [serialize_doc(m) for m in methods]
