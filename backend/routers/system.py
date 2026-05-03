from fastapi import APIRouter, Depends
import time as _time
import logging

from core.config import db
from core.tenant_guard import serialize_doc, now_utc, get_current_user
from core import cache as _cache
from rbac import ROLES, get_accessible_modules, LOYALTY_TIERS
from analytics_engine import compute_investor_metrics
from compliance import retention_auto_cleanup

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["system"])

_APP_START_TIME = _time.time()

@router.get("/health")
async def health_v2():
    health_data = {
        "status": "ok",
        "version": "6.0.0",
        "timestamp": now_utc().isoformat(),
        "uptime_seconds": round(_time.time() - _APP_START_TIME, 1),
        "services": {}
    }
    try:
        await db.command("ping")
        health_data["services"]["mongodb"] = True
    except Exception:
        health_data["services"]["mongodb"] = False
        health_data["status"] = "degraded"
    health_data["services"]["redis"] = True
    return health_data

@router.get("/system/status")
async def system_status_v2():
    try:
        await db.command("ping")
        db_status = "connected"
    except Exception as e:
        import logging
        logging.getLogger("omnihub.system").warning("DB ping failed: %s", e)
        db_status = "error"
    return {
        "status": "operational",
        "version": "11.0.0",
        "database": db_status,
        "timestamp": now_utc().isoformat(),
        "uptime": "running"
    }

@router.get("/system/metrics")
async def system_metrics_v2():
    return await compute_investor_metrics(db)


@router.get("/system/cache-stats")
async def cache_stats_v2(user=Depends(get_current_user)):
    if user.get("role") not in ("owner", "admin", "superadmin"):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="admin role required")
    return _cache.stats()


@router.post("/system/cache-clear")
async def cache_clear_v2(user=Depends(get_current_user)):
    if user.get("role") not in ("owner", "admin", "superadmin"):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="admin role required")
    await _cache.clear()
    return {"cleared": True}

@router.get("/system/investor-metrics")
async def investor_metrics_v2():
    return await compute_investor_metrics(db)

@router.get("/rbac/roles")
async def get_roles_v2():
    return ROLES

@router.get("/rbac/modules")
async def get_user_modules_v2(user=Depends(get_current_user)):
    return {"modules": get_accessible_modules(user.get("role", "agent")), "role": user.get("role")}

@router.get("/rbac/tiers")
async def get_loyalty_tiers_v2():
    return LOYALTY_TIERS

@router.post("/compliance/retention-cleanup")
async def trigger_retention_cleanup_v2():
    results = await retention_auto_cleanup(db)
    return {"status": "completed", "results": results}
