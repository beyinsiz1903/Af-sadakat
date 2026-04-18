"""PMS Integration Router: Abstract interface for Opera/Mews/Cloudbeds/Syroce.
Provides adapter pattern for multiple PMS systems.
"""
from fastapi import APIRouter, HTTPException
import logging
from typing import Optional

import httpx

from core.config import db
from core.tenant_guard import (
    serialize_doc, new_id, now_utc,
    resolve_tenant, log_audit, get_current_user
)
from fastapi import Depends

logger = logging.getLogger("omnihub.pms")

router = APIRouter(prefix="/api/v2/pms", tags=["pms-integration"])


class PMSAdapter:
    async def sync_rooms(self, tenant_id, config): raise NotImplementedError
    async def sync_guests(self, tenant_id, config): raise NotImplementedError
    async def sync_reservations(self, tenant_id, config): raise NotImplementedError
    async def push_charge(self, tenant_id, config, room_code, charge): raise NotImplementedError

    # Extended interface used by Syroce; default = NotImplementedError so legacy
    # adapters (Opera/Mews/Cloudbeds) keep working without changes.
    async def list_rooms(self): raise NotImplementedError
    async def list_reservations(self, status=None, from_date=None, to_date=None, limit=200):
        raise NotImplementedError
    async def get_reservation(self, reservation_id): raise NotImplementedError
    async def list_guests(self, limit=200): raise NotImplementedError
    async def get_guest(self, guest_id): raise NotImplementedError
    async def post_folio_charge(self, reservation_id, description, amount, external_ref):
        raise NotImplementedError


class OperaAdapter(PMSAdapter):
    async def sync_rooms(self, tenant_id, config):
        return {"status": "stub", "provider": "opera", "message": "Oracle Opera OHIP integration pending API credentials"}

    async def sync_guests(self, tenant_id, config):
        return {"status": "stub", "provider": "opera"}

    async def sync_reservations(self, tenant_id, config):
        return {"status": "stub", "provider": "opera"}

    async def push_charge(self, tenant_id, config, room_code, charge):
        return {"status": "stub", "provider": "opera", "charge": charge}


class MewsAdapter(PMSAdapter):
    async def sync_rooms(self, tenant_id, config):
        return {"status": "stub", "provider": "mews", "message": "Mews Connector API integration pending"}

    async def sync_guests(self, tenant_id, config):
        return {"status": "stub", "provider": "mews"}

    async def sync_reservations(self, tenant_id, config):
        return {"status": "stub", "provider": "mews"}

    async def push_charge(self, tenant_id, config, room_code, charge):
        return {"status": "stub", "provider": "mews", "charge": charge}


class CloudbedsAdapter(PMSAdapter):
    async def sync_rooms(self, tenant_id, config):
        return {"status": "stub", "provider": "cloudbeds", "message": "Cloudbeds API integration pending"}

    async def sync_guests(self, tenant_id, config):
        return {"status": "stub", "provider": "cloudbeds"}

    async def sync_reservations(self, tenant_id, config):
        return {"status": "stub", "provider": "cloudbeds"}

    async def push_charge(self, tenant_id, config, room_code, charge):
        return {"status": "stub", "provider": "cloudbeds", "charge": charge}


class SyroceAdapter(PMSAdapter):
    """Adapter for Syroce PMS (Hotel Management System).

    Authenticated outbound calls use Bearer token over HTTPS to the tenant's
    Syroce callback base URL (stored as `api_url` + `api_key` in pms_configs).
    """
    PROVIDER = "syroce"

    def __init__(self, base_url: str = "", api_key: str = ""):
        self.base = (base_url or "").rstrip("/")
        self.api_key = api_key or ""

    @classmethod
    def from_config(cls, config: dict) -> "SyroceAdapter":
        return cls(base_url=config.get("api_url", ""), api_key=config.get("api_key", ""))

    @property
    def headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"}

    async def _get(self, path: str, params: Optional[dict] = None) -> dict:
        if not self.base or not self.api_key:
            raise HTTPException(status_code=400, detail="Syroce integration not configured")
        url = f"{self.base}{path}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.get(url, headers=self.headers, params=params)
            self._raise_for_status(r)
            return r.json()

    async def _post(self, path: str, payload: dict) -> dict:
        if not self.base or not self.api_key:
            raise HTTPException(status_code=400, detail="Syroce integration not configured")
        url = f"{self.base}{path}"
        async with httpx.AsyncClient(timeout=20.0) as client:
            r = await client.post(url, headers=self.headers, json=payload)
            self._raise_for_status(r)
            return r.json()

    @staticmethod
    def _raise_for_status(r: httpx.Response):
        if r.status_code == 200:
            return
        if r.status_code == 401:
            raise HTTPException(status_code=502, detail="SYROCE_AUTH_INVALID")
        if r.status_code == 403:
            raise HTTPException(status_code=502, detail="SYROCE_SUBSCRIPTION_SUSPENDED")
        if r.status_code == 409:
            return  # idempotency / duplicate accepted by caller
        raise HTTPException(status_code=502, detail=f"SYROCE_HTTP_{r.status_code}")

    # ---- Discovery (outbound reads) ----
    async def list_rooms(self):
        return await self._get("/api/pms-outbound/rooms")

    async def list_reservations(self, status=None, from_date=None, to_date=None, limit=200):
        params = {"limit": int(limit)}
        if status:
            params["status"] = status
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        return await self._get("/api/pms-outbound/reservations", params=params)

    async def get_reservation(self, reservation_id):
        return await self._get(f"/api/pms-outbound/reservations/{reservation_id}")

    async def list_guests(self, limit=200):
        return await self._get("/api/pms-outbound/guests", params={"limit": int(limit)})

    async def get_guest(self, guest_id):
        return await self._get(f"/api/pms-outbound/guests/{guest_id}")

    async def post_folio_charge(self, reservation_id, description, amount, external_ref):
        return await self._post("/api/pms-outbound/folio/charge", {
            "reservation_id": reservation_id,
            "description": description,
            "amount": float(amount),
            "external_ref": external_ref,
        })

    # ---- Sync wrappers (used by /sync/{entity}) ----
    async def sync_rooms(self, tenant_id, config):
        a = self.from_config(config)
        data = await a.list_rooms()
        return {"status": "ok", "provider": "syroce", "count": data.get("count", 0)}

    async def sync_guests(self, tenant_id, config):
        a = self.from_config(config)
        data = await a.list_guests(limit=500)
        return {"status": "ok", "provider": "syroce", "count": data.get("count", 0)}

    async def sync_reservations(self, tenant_id, config):
        a = self.from_config(config)
        data = await a.list_reservations(limit=500)
        return {"status": "ok", "provider": "syroce", "count": data.get("count", 0)}

    async def push_charge(self, tenant_id, config, room_code, charge):
        a = self.from_config(config)
        return await a.post_folio_charge(
            reservation_id=charge.get("reservation_id") or room_code,
            description=charge.get("description", ""),
            amount=charge.get("amount", 0),
            external_ref=charge.get("external_ref") or new_id(),
        )


PMS_ADAPTERS = {
    "opera": OperaAdapter(),
    "mews": MewsAdapter(),
    "cloudbeds": CloudbedsAdapter(),
    "syroce": SyroceAdapter(),
}


def get_adapter(provider: str) -> PMSAdapter:
    adapter = PMS_ADAPTERS.get(provider)
    if not adapter:
        raise HTTPException(status_code=400, detail=f"Unsupported PMS provider: {provider}")
    return adapter


@router.get("/providers")
async def list_pms_providers():
    return {
        "providers": [
            {"id": "opera", "name": "Oracle Opera (OHIP)", "status": "available", "description": "Oracle Hospitality Integration Platform"},
            {"id": "mews", "name": "Mews", "status": "available", "description": "Mews Connector API"},
            {"id": "cloudbeds", "name": "Cloudbeds", "status": "available", "description": "Cloudbeds Open API"},
            {"id": "syroce", "name": "Syroce PMS", "status": "available", "description": "Syroce hotel management system (bi-directional)"},
        ]
    }


@router.get("/tenants/{tenant_slug}/config")
async def get_pms_config(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    config = await db.pms_configs.find_one({"tenant_id": tid})
    if not config:
        return {"configured": False, "provider": None}
    safe = serialize_doc(config)
    for secret_field in ["api_key", "client_secret"]:
        if safe.get(secret_field):
            safe[secret_field] = "***" + safe[secret_field][-4:] if len(safe.get(secret_field, "")) > 4 else "****"
    return {"configured": True, **safe}


@router.post("/tenants/{tenant_slug}/configure")
async def configure_pms(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    provider = data.get("provider")
    if provider not in PMS_ADAPTERS:
        raise HTTPException(status_code=400, detail="Invalid PMS provider")

    config = {
        "id": new_id(), "tenant_id": tid,
        "provider": provider,
        "api_url": data.get("api_url", ""),
        "api_key": data.get("api_key", ""),
        "client_id": data.get("client_id", ""),
        "client_secret": data.get("client_secret", ""),
        "hotel_id": data.get("hotel_id", ""),
        "sync_rooms": data.get("sync_rooms", True),
        "sync_guests": data.get("sync_guests", True),
        "sync_reservations": data.get("sync_reservations", True),
        "auto_post_charges": data.get("auto_post_charges", False),
        "status": "configured",
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat(),
    }

    await db.pms_configs.delete_many({"tenant_id": tid})
    await db.pms_configs.insert_one(config)

    await log_audit(tid, "PMS_CONFIGURED", "pms", config["id"], user["id"],
                    {"provider": provider})
    return {"status": "configured", "config": serialize_doc(config)}


@router.post("/tenants/{tenant_slug}/sync/{entity}")
async def trigger_pms_sync(tenant_slug: str, entity: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    config = await db.pms_configs.find_one({"tenant_id": tid})
    if not config:
        raise HTTPException(status_code=400, detail="PMS not configured")

    adapter = get_adapter(config["provider"])

    if entity == "rooms":
        result = await adapter.sync_rooms(tid, config)
    elif entity == "guests":
        result = await adapter.sync_guests(tid, config)
    elif entity == "reservations":
        result = await adapter.sync_reservations(tid, config)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown entity: {entity}")

    sync_log = {
        "id": new_id(), "tenant_id": tid,
        "provider": config["provider"],
        "entity": entity,
        "result": result,
        "triggered_by": user["id"],
        "created_at": now_utc().isoformat(),
    }
    await db.pms_sync_logs.insert_one(sync_log)

    return {"sync": result, "log_id": sync_log["id"]}


@router.post("/tenants/{tenant_slug}/post-charge")
async def post_charge_to_pms(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    config = await db.pms_configs.find_one({"tenant_id": tid})
    if not config:
        raise HTTPException(status_code=400, detail="PMS not configured")

    adapter = get_adapter(config["provider"])
    result = await adapter.push_charge(tid, config, data.get("room_code", ""), {
        "description": data.get("description", ""),
        "amount": data.get("amount", 0),
        "currency": data.get("currency", "TRY"),
    })
    return result


@router.get("/tenants/{tenant_slug}/sync-logs")
async def get_sync_logs(tenant_slug: str, limit: int = 20, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    logs = await db.pms_sync_logs.find({"tenant_id": tid}).sort("created_at", -1).limit(limit).to_list(limit)
    return [serialize_doc(l) for l in logs]
