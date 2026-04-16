from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import bcrypt

from core.config import db
from core.tenant_guard import (
    resolve_tenant, get_current_user, serialize_doc, new_id, now_utc, log_audit
)
from security import get_plan_limits

router = APIRouter(prefix="/api/tenants", tags=["tenants"])

class TenantCreate(BaseModel):
    name: str
    slug: str
    business_type: str = "hotel"
    plan: str = "basic"

class TenantUpdate(BaseModel):
    name: Optional[str] = None
    hotel_enabled: Optional[bool] = None
    restaurant_enabled: Optional[bool] = None
    agency_enabled: Optional[bool] = None
    clinic_enabled: Optional[bool] = None

class LoyaltyRulesUpdate(BaseModel):
    enabled: Optional[bool] = None
    points_per_request: Optional[int] = None
    points_per_order: Optional[int] = None
    points_per_currency_unit: Optional[int] = None

class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    role: str = "agent"

class DepartmentCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = ""

class ServiceCategoryCreate(BaseModel):
    name: str
    department_code: str
    icon: Optional[str] = ""

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

@router.post("")
async def create_tenant(data: TenantCreate):
    existing = await db.tenants.find_one({"slug": data.slug})
    if existing:
        raise HTTPException(status_code=400, detail="Tenant slug already exists")
    tenant = {
        "id": new_id(), "name": data.name, "slug": data.slug,
        "business_type": data.business_type, "plan": data.plan,
        "hotel_enabled": data.business_type in ["hotel"],
        "restaurant_enabled": data.business_type in ["restaurant", "hotel"],
        "agency_enabled": False, "clinic_enabled": False,
        "plan_limits": {
            "max_users": 5 if data.plan == "basic" else 25,
            "max_rooms": 20 if data.plan == "basic" else 100,
            "max_tables": 10 if data.plan == "basic" else 50,
            "monthly_ai_replies": 50 if data.plan == "basic" else 500,
        },
        "usage_counters": {"users": 1, "rooms": 0, "tables": 0, "ai_replies_this_month": 0},
        "loyalty_rules": {"enabled": False, "points_per_request": 10, "points_per_order": 5, "points_per_currency_unit": 1},
        "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat()
    }
    await db.tenants.insert_one(tenant)
    return serialize_doc(tenant)

@router.get("")
async def list_tenants():
    tenants = await db.tenants.find({}, {"_id": 0}).to_list(100)
    return [serialize_doc(t) for t in tenants]

@router.get("/{tenant_slug}")
async def get_tenant(tenant_slug: str):
    return await resolve_tenant(tenant_slug)

@router.patch("/{tenant_slug}")
async def update_tenant(tenant_slug: str, data: TenantUpdate):
    tenant = await resolve_tenant(tenant_slug)
    update_data = {k: v for k, v in data.model_dump().items() if v is not None}
    update_data["updated_at"] = now_utc().isoformat()
    await db.tenants.update_one({"id": tenant["id"]}, {"$set": update_data})
    updated = await db.tenants.find_one({"id": tenant["id"]}, {"_id": 0})
    return serialize_doc(updated)

@router.patch("/{tenant_slug}/loyalty-rules")
async def update_loyalty_rules(tenant_slug: str, data: LoyaltyRulesUpdate):
    tenant = await resolve_tenant(tenant_slug)
    update = {}
    if data.enabled is not None: update["loyalty_rules.enabled"] = data.enabled
    if data.points_per_request is not None: update["loyalty_rules.points_per_request"] = data.points_per_request
    if data.points_per_order is not None: update["loyalty_rules.points_per_order"] = data.points_per_order
    if data.points_per_currency_unit is not None: update["loyalty_rules.points_per_currency_unit"] = data.points_per_currency_unit
    update["updated_at"] = now_utc().isoformat()
    await db.tenants.update_one({"id": tenant["id"]}, {"$set": update})
    updated = await db.tenants.find_one({"id": tenant["id"]}, {"_id": 0})
    return serialize_doc(updated)

@router.post("/{tenant_slug}/users")
async def create_user(tenant_slug: str, data: UserCreate):
    tenant = await resolve_tenant(tenant_slug)
    existing = await db.users.find_one({"email": data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists")
    user = {
        "id": new_id(), "tenant_id": tenant["id"], "email": data.email,
        "password_hash": hash_password(data.password), "name": data.name,
        "role": data.role, "department_code": None, "active": True,
        "created_at": now_utc().isoformat()
    }
    await db.users.insert_one(user)
    await db.tenants.update_one({"id": tenant["id"]}, {"$inc": {"usage_counters.users": 1}})
    result = serialize_doc(user)
    result.pop("password_hash", None)
    return result

@router.get("/{tenant_slug}/users")
async def list_users(tenant_slug: str):
    tenant = await resolve_tenant(tenant_slug)
    users = await db.users.find({"tenant_id": tenant["id"]}, {"_id": 0, "password_hash": 0}).to_list(100)
    return [serialize_doc(u) for u in users]

@router.post("/{tenant_slug}/departments")
async def create_department(tenant_slug: str, data: DepartmentCreate):
    tenant = await resolve_tenant(tenant_slug)
    dept = {
        "id": new_id(), "tenant_id": tenant["id"], "name": data.name,
        "code": data.code.upper(), "description": data.description,
        "created_at": now_utc().isoformat()
    }
    await db.departments.insert_one(dept)
    return serialize_doc(dept)

@router.get("/{tenant_slug}/departments")
async def list_departments(tenant_slug: str):
    tenant = await resolve_tenant(tenant_slug)
    depts = await db.departments.find({"tenant_id": tenant["id"]}, {"_id": 0}).to_list(100)
    return [serialize_doc(d) for d in depts]

@router.delete("/{tenant_slug}/departments/{dept_id}")
async def delete_department(tenant_slug: str, dept_id: str):
    tenant = await resolve_tenant(tenant_slug)
    result = await db.departments.delete_one({"id": dept_id, "tenant_id": tenant["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Department not found")
    return {"deleted": True}

@router.post("/{tenant_slug}/service-categories")
async def create_service_category(tenant_slug: str, data: ServiceCategoryCreate):
    tenant = await resolve_tenant(tenant_slug)
    cat = {
        "id": new_id(), "tenant_id": tenant["id"], "name": data.name,
        "department_code": data.department_code.upper(), "icon": data.icon,
        "created_at": now_utc().isoformat()
    }
    await db.service_categories.insert_one(cat)
    return serialize_doc(cat)

@router.get("/{tenant_slug}/service-categories")
async def list_service_categories(tenant_slug: str):
    tenant = await resolve_tenant(tenant_slug)
    cats = await db.service_categories.find({"tenant_id": tenant["id"]}, {"_id": 0}).to_list(100)
    return [serialize_doc(c) for c in cats]

@router.get("/{tenant_slug}/usage")
async def get_usage(tenant_slug: str):
    tenant = await resolve_tenant(tenant_slug)
    plan = tenant.get("plan", "basic")
    limits = get_plan_limits(plan)
    usage = tenant.get("usage_counters", {})
    contacts = await db.contacts.count_documents({"tenant_id": tenant["id"]})
    active_offers = await db.offers.count_documents({"tenant_id": tenant["id"], "status": {"$in": ["draft", "sent"]}})
    reservations = await db.reservations.count_documents({"tenant_id": tenant["id"]})
    return {
        "plan": plan,
        "plan_label": limits.get("label", plan),
        "metrics": {
            "users": {"current": usage.get("users", 1), "limit": limits["max_users"]},
            "rooms": {"current": usage.get("rooms", 0), "limit": limits["max_rooms"]},
            "tables": {"current": usage.get("tables", 0), "limit": limits["max_tables"]},
            "contacts": {"current": contacts, "limit": limits["max_contacts"]},
            "ai_replies": {"current": usage.get("ai_replies_this_month", 0), "limit": limits["monthly_ai_replies"]},
            "reservations": {"current": reservations, "limit": limits["max_monthly_reservations"]},
            "active_offers": {"current": active_offers, "limit": limits["max_active_offers"]},
        }
    }

@router.post("/{tenant_slug}/upgrade")
async def upgrade_plan(tenant_slug: str, data: dict):
    from security import PLAN_LIMITS
    tenant = await resolve_tenant(tenant_slug)
    new_plan = data.get("plan", "pro")
    if new_plan not in PLAN_LIMITS:
        raise HTTPException(status_code=400, detail="Invalid plan")
    new_limits = get_plan_limits(new_plan)
    await db.tenants.update_one({"id": tenant["id"]}, {"$set": {
        "plan": new_plan,
        "plan_limits": {
            "max_users": new_limits["max_users"],
            "max_rooms": new_limits["max_rooms"],
            "max_tables": new_limits["max_tables"],
            "monthly_ai_replies": new_limits["monthly_ai_replies"],
        },
        "updated_at": now_utc().isoformat()
    }})
    await log_audit(tenant["id"], "plan_upgraded", "tenant", tenant["id"], details={"from": tenant.get("plan"), "to": new_plan})
    updated = await db.tenants.find_one({"id": tenant["id"]}, {"_id": 0})
    return serialize_doc(updated)

@router.get("/{tenant_slug}/onboarding")
async def get_onboarding_status(tenant_slug: str):
    tenant = await resolve_tenant(tenant_slug)
    onboarding = await db.onboarding.find_one({"tenant_id": tenant["id"]}, {"_id": 0})
    if not onboarding:
        onboarding = {
            "id": new_id(), "tenant_id": tenant["id"], "completed": False, "current_step": 1,
            "steps": {
                "1": {"label": "Business Info", "completed": True},
                "2": {"label": "Create Departments", "completed": False},
                "3": {"label": "Add Rooms / Tables", "completed": False},
                "4": {"label": "Configure Menu", "completed": False},
                "5": {"label": "Loyalty Rules", "completed": False},
                "6": {"label": "Generate QR Codes", "completed": False},
                "7": {"label": "Invite Team", "completed": False},
            },
            "created_at": now_utc().isoformat()
        }
        await db.onboarding.insert_one(onboarding)

    depts = await db.departments.count_documents({"tenant_id": tenant["id"]})
    rooms = await db.rooms.count_documents({"tenant_id": tenant["id"]})
    tables = await db.tables.count_documents({"tenant_id": tenant["id"]})
    menu_items = await db.menu_items.count_documents({"tenant_id": tenant["id"]})
    users = await db.users.count_documents({"tenant_id": tenant["id"]})

    steps = onboarding.get("steps", {})
    steps["2"]["completed"] = depts > 0
    steps["3"]["completed"] = rooms > 0 or tables > 0
    steps["4"]["completed"] = menu_items > 0 or not tenant.get("restaurant_enabled", False)
    steps["5"]["completed"] = tenant.get("loyalty_rules", {}).get("enabled", False) or True
    steps["6"]["completed"] = rooms > 0 or tables > 0
    steps["7"]["completed"] = users > 1

    completed_count = sum(1 for s in steps.values() if s.get("completed"))
    all_complete = completed_count >= 5

    await db.onboarding.update_one(
        {"tenant_id": tenant["id"]},
        {"$set": {"steps": steps, "completed": all_complete, "current_step": min(7, completed_count + 1)}}
    )

    return {**serialize_doc(onboarding), "steps": steps, "completed": all_complete, "progress": round(completed_count / 7 * 100)}

@router.post("/{tenant_slug}/onboarding/complete")
async def complete_onboarding(tenant_slug: str):
    tenant = await resolve_tenant(tenant_slug)
    await db.onboarding.update_one({"tenant_id": tenant["id"]}, {"$set": {"completed": True}})
    await db.tenants.update_one({"id": tenant["id"]}, {"$set": {"onboarding_completed": True}})
    return {"completed": True}
