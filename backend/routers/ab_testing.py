"""A/B Testing Router - Experiments, Variants, User Assignment, Event Tracking, Results
Full A/B testing infrastructure for hotel operations optimization.
"""
import random
import hashlib
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from core.config import db
from core.tenant_guard import (
    resolve_tenant, get_current_user, serialize_doc,
    new_id, now_utc, find_one_scoped, find_many_scoped, count_scoped,
    insert_scoped, update_scoped, delete_scoped, log_audit
)

router = APIRouter(prefix="/api/v2/ab-testing", tags=["ab-testing"])


def _assign_variant(experiment: dict, user_id: str) -> str:
    """Deterministically assign a user to a variant based on experiment traffic split"""
    variants = experiment.get("variants", [])
    if not variants:
        return "control"
    
    # Deterministic hash for consistent assignment
    hash_input = f"{experiment.get('id', '')}:{user_id}"
    hash_val = int(hashlib.md5(hash_input.encode()).hexdigest(), 16) % 100
    
    cumulative = 0
    for variant in variants:
        cumulative += variant.get("traffic_percent", 0)
        if hash_val < cumulative:
            return variant.get("name", "control")
    
    return variants[-1].get("name", "control") if variants else "control"


# ============ EXPERIMENTS ============
@router.get("/tenants/{tenant_slug}/experiments")
async def list_experiments(tenant_slug: str, status: Optional[str] = None,
                          user=Depends(get_current_user)):
    """List all A/B experiments"""
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if status:
        query["status"] = status
    experiments = await find_many_scoped("ab_experiments", tenant["id"], query,
                                          sort=[("created_at", -1)])
    return {"data": experiments, "total": len(experiments)}


@router.post("/tenants/{tenant_slug}/experiments")
async def create_experiment(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    """Create a new A/B experiment"""
    tenant = await resolve_tenant(tenant_slug)
    
    variants = data.get("variants", [
        {"name": "control", "traffic_percent": 50, "description": "Original version"},
        {"name": "variant_a", "traffic_percent": 50, "description": "Test version"}
    ])
    
    # Validate traffic percentages sum to 100
    total_traffic = sum(v.get("traffic_percent", 0) for v in variants)
    if total_traffic != 100:
        raise HTTPException(status_code=400, detail=f"Traffic percentages must sum to 100 (got {total_traffic})")
    
    experiment = await insert_scoped("ab_experiments", tenant["id"], {
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "hypothesis": data.get("hypothesis", ""),
        "feature_area": data.get("feature_area", "general"),
        "variants": variants,
        "status": "draft",
        "target_audience": data.get("target_audience", "all"),
        "target_sample_size": data.get("target_sample_size", 100),
        "primary_metric": data.get("primary_metric", "conversion_rate"),
        "secondary_metrics": data.get("secondary_metrics", []),
        "start_date": "",
        "end_date": "",
        "total_participants": 0,
        "created_by": user.get("id", ""),
    })
    
    await log_audit(tenant["id"], "AB_EXPERIMENT_CREATED", "ab_experiments", experiment["id"], user.get("id", ""))
    return experiment


@router.get("/tenants/{tenant_slug}/experiments/{experiment_id}")
async def get_experiment(tenant_slug: str, experiment_id: str, user=Depends(get_current_user)):
    """Get experiment details with results"""
    tenant = await resolve_tenant(tenant_slug)
    experiment = await find_one_scoped("ab_experiments", tenant["id"], {"id": experiment_id})
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return experiment


@router.patch("/tenants/{tenant_slug}/experiments/{experiment_id}")
async def update_experiment(tenant_slug: str, experiment_id: str, data: dict, user=Depends(get_current_user)):
    """Update an experiment (only while in draft status)"""
    tenant = await resolve_tenant(tenant_slug)
    experiment = await find_one_scoped("ab_experiments", tenant["id"], {"id": experiment_id})
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if experiment.get("status") not in ["draft", "paused"]:
        raise HTTPException(status_code=400, detail="Can only edit draft or paused experiments")
    
    allowed = ["name", "description", "hypothesis", "feature_area", "variants",
               "target_audience", "target_sample_size", "primary_metric", "secondary_metrics"]
    update_data = {k: v for k, v in data.items() if k in allowed}
    
    if "variants" in update_data:
        total_traffic = sum(v.get("traffic_percent", 0) for v in update_data["variants"])
        if total_traffic != 100:
            raise HTTPException(status_code=400, detail=f"Traffic percentages must sum to 100 (got {total_traffic})")
    
    return await update_scoped("ab_experiments", tenant["id"], experiment_id, update_data)


@router.delete("/tenants/{tenant_slug}/experiments/{experiment_id}")
async def delete_experiment(tenant_slug: str, experiment_id: str, user=Depends(get_current_user)):
    """Delete an experiment"""
    tenant = await resolve_tenant(tenant_slug)
    await delete_scoped("ab_experiments", tenant["id"], experiment_id)
    # Clean up related data
    await db.ab_assignments.delete_many({"tenant_id": tenant["id"], "experiment_id": experiment_id})
    await db.ab_events.delete_many({"tenant_id": tenant["id"], "experiment_id": experiment_id})
    return {"ok": True}


@router.post("/tenants/{tenant_slug}/experiments/{experiment_id}/start")
async def start_experiment(tenant_slug: str, experiment_id: str, user=Depends(get_current_user)):
    """Start an experiment"""
    tenant = await resolve_tenant(tenant_slug)
    experiment = await find_one_scoped("ab_experiments", tenant["id"], {"id": experiment_id})
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if experiment.get("status") not in ["draft", "paused"]:
        raise HTTPException(status_code=400, detail="Experiment must be in draft or paused status")
    
    update_data = {
        "status": "running",
        "start_date": now_utc().isoformat() if not experiment.get("start_date") else experiment["start_date"],
    }
    result = await update_scoped("ab_experiments", tenant["id"], experiment_id, update_data)
    await log_audit(tenant["id"], "AB_EXPERIMENT_STARTED", "ab_experiments", experiment_id, user.get("id", ""))
    return result


@router.post("/tenants/{tenant_slug}/experiments/{experiment_id}/stop")
async def stop_experiment(tenant_slug: str, experiment_id: str, user=Depends(get_current_user)):
    """Stop a running experiment"""
    tenant = await resolve_tenant(tenant_slug)
    experiment = await find_one_scoped("ab_experiments", tenant["id"], {"id": experiment_id})
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    update_data = {
        "status": "completed",
        "end_date": now_utc().isoformat(),
    }
    result = await update_scoped("ab_experiments", tenant["id"], experiment_id, update_data)
    await log_audit(tenant["id"], "AB_EXPERIMENT_STOPPED", "ab_experiments", experiment_id, user.get("id", ""))
    return result


@router.post("/tenants/{tenant_slug}/experiments/{experiment_id}/pause")
async def pause_experiment(tenant_slug: str, experiment_id: str, user=Depends(get_current_user)):
    """Pause a running experiment"""
    tenant = await resolve_tenant(tenant_slug)
    return await update_scoped("ab_experiments", tenant["id"], experiment_id, {"status": "paused"})


# ============ USER ASSIGNMENT ============
@router.post("/tenants/{tenant_slug}/assign")
async def assign_to_variant(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    """Assign a user to an experiment variant"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    experiment_id = data.get("experiment_id", "")
    user_identifier = data.get("user_id", user.get("id", ""))
    
    experiment = await find_one_scoped("ab_experiments", tid, {"id": experiment_id})
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    if experiment.get("status") != "running":
        raise HTTPException(status_code=400, detail="Experiment is not running")
    
    # Check existing assignment
    existing = await db.ab_assignments.find_one({
        "tenant_id": tid, "experiment_id": experiment_id, "user_id": user_identifier
    })
    if existing:
        return {"variant": existing.get("variant", ""), "experiment_id": experiment_id, "already_assigned": True}
    
    # Assign variant
    variant = _assign_variant(experiment, user_identifier)
    
    await insert_scoped("ab_assignments", tid, {
        "experiment_id": experiment_id,
        "user_id": user_identifier,
        "variant": variant,
        "assigned_at": now_utc().isoformat(),
    })
    
    # Increment participant count
    await db.ab_experiments.update_one(
        {"tenant_id": tid, "id": experiment_id},
        {"$inc": {"total_participants": 1}}
    )
    
    return {"variant": variant, "experiment_id": experiment_id, "already_assigned": False}


# ============ EVENT TRACKING ============
@router.post("/tenants/{tenant_slug}/track")
async def track_event(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    """Track an event for A/B testing"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    experiment_id = data.get("experiment_id", "")
    event_name = data.get("event_name", "")
    user_identifier = data.get("user_id", user.get("id", ""))
    event_value = data.get("value", 1)
    metadata = data.get("metadata", {})
    
    if not experiment_id or not event_name:
        raise HTTPException(status_code=400, detail="experiment_id and event_name required")
    
    # Get user's variant
    assignment = await db.ab_assignments.find_one({
        "tenant_id": tid, "experiment_id": experiment_id, "user_id": user_identifier
    })
    variant = assignment.get("variant", "unknown") if assignment else "unknown"
    
    event = await insert_scoped("ab_events", tid, {
        "experiment_id": experiment_id,
        "user_id": user_identifier,
        "variant": variant,
        "event_name": event_name,
        "event_value": event_value,
        "metadata": metadata,
        "tracked_at": now_utc().isoformat(),
    })
    
    return {"ok": True, "event_id": event.get("id", "")}


# ============ RESULTS ============
@router.get("/tenants/{tenant_slug}/experiments/{experiment_id}/results")
async def get_experiment_results(tenant_slug: str, experiment_id: str, user=Depends(get_current_user)):
    """Get detailed results for an experiment"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    experiment = await find_one_scoped("ab_experiments", tid, {"id": experiment_id})
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")
    
    variants = experiment.get("variants", [])
    primary_metric = experiment.get("primary_metric", "conversion_rate")
    
    results = []
    for variant in variants:
        vname = variant.get("name", "")
        
        # Count assignments
        assignment_count = await db.ab_assignments.count_documents({
            "tenant_id": tid, "experiment_id": experiment_id, "variant": vname
        })
        
        # Count events
        event_count = await db.ab_events.count_documents({
            "tenant_id": tid, "experiment_id": experiment_id, "variant": vname
        })
        
        # Count unique converters (users with conversion events)
        pipeline = [
            {"$match": {
                "tenant_id": tid,
                "experiment_id": experiment_id,
                "variant": vname,
                "event_name": {"$in": ["conversion", "purchase", "booking", "signup"]}
            }},
            {"$group": {"_id": "$user_id"}},
            {"$count": "unique_converters"}
        ]
        converters = 0
        async for doc in db.ab_events.aggregate(pipeline):
            converters = doc.get("unique_converters", 0)
        
        # Sum event values
        value_pipeline = [
            {"$match": {"tenant_id": tid, "experiment_id": experiment_id, "variant": vname}},
            {"$group": {"_id": None, "total_value": {"$sum": "$event_value"}, "avg_value": {"$avg": "$event_value"}}}
        ]
        total_value = 0
        avg_value = 0
        async for doc in db.ab_events.aggregate(value_pipeline):
            total_value = doc.get("total_value", 0)
            avg_value = round(doc.get("avg_value", 0), 2)
        
        conversion_rate = round((converters / max(assignment_count, 1)) * 100, 2)
        
        results.append({
            "variant_name": vname,
            "description": variant.get("description", ""),
            "traffic_percent": variant.get("traffic_percent", 0),
            "participants": assignment_count,
            "total_events": event_count,
            "unique_converters": converters,
            "conversion_rate": conversion_rate,
            "total_value": total_value,
            "avg_value": avg_value,
        })
    
    # Determine winner
    winner = None
    if len(results) >= 2:
        sorted_results = sorted(results, key=lambda r: r["conversion_rate"], reverse=True)
        if sorted_results[0]["conversion_rate"] > sorted_results[1]["conversion_rate"]:
            winner = sorted_results[0]["variant_name"]
    
    return {
        "experiment": experiment,
        "results": results,
        "winner": winner,
        "primary_metric": primary_metric,
        "total_participants": sum(r["participants"] for r in results),
        "total_events": sum(r["total_events"] for r in results),
    }


# ============ STATS ============
@router.get("/tenants/{tenant_slug}/stats")
async def get_ab_stats(tenant_slug: str, user=Depends(get_current_user)):
    """Get overall A/B testing statistics"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    total_experiments = await count_scoped("ab_experiments", tid)
    running = await count_scoped("ab_experiments", tid, {"status": "running"})
    completed = await count_scoped("ab_experiments", tid, {"status": "completed"})
    draft = await count_scoped("ab_experiments", tid, {"status": "draft"})
    total_assignments = await count_scoped("ab_assignments", tid)
    total_events = await count_scoped("ab_events", tid)
    
    return {
        "total_experiments": total_experiments,
        "running": running,
        "completed": completed,
        "draft": draft,
        "total_participants": total_assignments,
        "total_events_tracked": total_events,
    }
