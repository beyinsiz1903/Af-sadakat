"""SLA Router - Service Level Agreement management
Define SLA rules per category/department, track breaches, auto-escalation
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from core.config import db
from core.tenant_guard import (
    resolve_tenant, get_current_user, serialize_doc, new_id, now_utc,
    find_one_scoped, find_many_scoped, count_scoped,
    insert_scoped, update_scoped, delete_scoped, log_audit
)

router = APIRouter(prefix="/api/v2/sla", tags=["sla"])

@router.get("/tenants/{tenant_slug}/sla-rules")
async def list_sla_rules(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    return await find_many_scoped("sla_rules", tenant["id"], sort=[("category", 1)])

@router.post("/tenants/{tenant_slug}/sla-rules")
async def create_sla_rule(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    rule = await insert_scoped("sla_rules", tenant["id"], {
        "category": data.get("category", ""),
        "department_code": data.get("department_code", ""),
        "priority": data.get("priority", "normal"),
        "response_time_minutes": data.get("response_time_minutes", 30),
        "resolution_time_minutes": data.get("resolution_time_minutes", 120),
        "escalation_after_minutes": data.get("escalation_after_minutes", 45),
        "escalate_to_role": data.get("escalate_to_role", "manager"),
        "auto_escalation_enabled": data.get("auto_escalation_enabled", True),
        "notification_on_breach": data.get("notification_on_breach", True),
        "active": data.get("active", True),
    })
    await log_audit(tenant["id"], "sla_rule_created", "sla_rule", rule["id"], user.get("id", ""))
    return rule

@router.patch("/tenants/{tenant_slug}/sla-rules/{rule_id}")
async def update_sla_rule(tenant_slug: str, rule_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    update = {}
    for key in ["response_time_minutes", "resolution_time_minutes", "escalation_after_minutes",
                "escalate_to_role", "auto_escalation_enabled", "notification_on_breach", "active", "priority"]:
        if key in data:
            update[key] = data[key]
    return await update_scoped("sla_rules", tenant["id"], rule_id, update)

@router.delete("/tenants/{tenant_slug}/sla-rules/{rule_id}")
async def delete_sla_rule(tenant_slug: str, rule_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    await delete_scoped("sla_rules", tenant["id"], rule_id)
    return {"deleted": True}

# SLA Breach Tracking
@router.get("/tenants/{tenant_slug}/sla-breaches")
async def list_sla_breaches(tenant_slug: str, status: Optional[str] = None,
                           page: int = 1, limit: int = 50,
                           user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if status:
        query["status"] = status
    skip = (page - 1) * limit
    breaches = await find_many_scoped("sla_breaches", tenant["id"], query,
                                      sort=[("created_at", -1)], skip=skip, limit=limit)
    total = await count_scoped("sla_breaches", tenant["id"], query)
    return {"data": breaches, "total": total, "page": page}

@router.get("/tenants/{tenant_slug}/sla-stats")
async def get_sla_stats(tenant_slug: str, user=Depends(get_current_user)):
    """Get SLA compliance statistics"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    total_requests = await count_scoped("guest_requests", tid)
    total_breaches = await count_scoped("sla_breaches", tid)
    active_breaches = await count_scoped("sla_breaches", tid, {"status": "active"})
    
    # Get average response time from resolved requests
    resolved = await find_many_scoped("guest_requests", tid, {"status": {"$in": ["DONE", "CLOSED"]}}, limit=500)
    
    response_times = []
    resolution_times = []
    for r in resolved:
        if r.get("first_response_at") and r.get("created_at"):
            try:
                from datetime import datetime
                created = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
                responded = datetime.fromisoformat(r["first_response_at"].replace("Z", "+00:00"))
                diff = (responded - created).total_seconds() / 60
                response_times.append(diff)
            except:
                pass
        if r.get("resolved_at") and r.get("created_at"):
            try:
                from datetime import datetime
                created = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
                resolved_dt = datetime.fromisoformat(r["resolved_at"].replace("Z", "+00:00"))
                diff = (resolved_dt - created).total_seconds() / 60
                resolution_times.append(diff)
            except:
                pass
    
    avg_response = round(sum(response_times) / len(response_times), 1) if response_times else 0
    avg_resolution = round(sum(resolution_times) / len(resolution_times), 1) if resolution_times else 0
    compliance_rate = round((1 - total_breaches / max(total_requests, 1)) * 100, 1)
    
    return {
        "total_requests": total_requests,
        "total_breaches": total_breaches,
        "active_breaches": active_breaches,
        "avg_response_minutes": avg_response,
        "avg_resolution_minutes": avg_resolution,
        "compliance_rate": compliance_rate,
    }

# Auto-assignment Rules
@router.get("/tenants/{tenant_slug}/assignment-rules")
async def list_assignment_rules(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    return await find_many_scoped("assignment_rules", tenant["id"])

@router.post("/tenants/{tenant_slug}/assignment-rules")
async def create_assignment_rule(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    return await insert_scoped("assignment_rules", tenant["id"], {
        "name": data.get("name", ""),
        "category": data.get("category", ""),
        "department_code": data.get("department_code", ""),
        "floor": data.get("floor", ""),
        "assign_to_user_id": data.get("assign_to_user_id", ""),
        "assign_to_user_name": data.get("assign_to_user_name", ""),
        "priority_override": data.get("priority_override", ""),
        "active": data.get("active", True),
    })

@router.delete("/tenants/{tenant_slug}/assignment-rules/{rule_id}")
async def delete_assignment_rule(tenant_slug: str, rule_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    await delete_scoped("assignment_rules", tenant["id"], rule_id)
    return {"deleted": True}

# Response Templates
@router.get("/tenants/{tenant_slug}/response-templates")
async def list_response_templates(tenant_slug: str, category: Optional[str] = None,
                                  user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if category:
        query["category"] = category
    return await find_many_scoped("response_templates", tenant["id"], query, sort=[("name", 1)])

@router.post("/tenants/{tenant_slug}/response-templates")
async def create_response_template(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    return await insert_scoped("response_templates", tenant["id"], {
        "name": data.get("name", ""),
        "category": data.get("category", ""),
        "body_tr": data.get("body_tr", ""),
        "body_en": data.get("body_en", ""),
        "shortcut": data.get("shortcut", ""),
    })

@router.delete("/tenants/{tenant_slug}/response-templates/{template_id}")
async def delete_response_template(tenant_slug: str, template_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    await delete_scoped("response_templates", tenant["id"], template_id)
    return {"deleted": True}
