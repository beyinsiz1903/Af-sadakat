"""Syroce -> OmniHub inbound webhook receiver.

Endpoint: POST /api/integrations/syroce/inbound
Auth:     HMAC-SHA256 over raw body using tenant pms_config.api_key
Headers:
  X-Syroce-Tenant     external_tenant_id
  X-Syroce-Signature  hex HMAC-SHA256 of raw body
  X-Syroce-Event-Id   unique id (used for idempotency)

Body:
  {
    "event": "reservation.created" | "reservation.updated" |
             "reservation.cancelled" | "guest.checkin" |
             "guest.checkout" | "folio.posted" |
             "room.status_changed",
    "occurred_at": "ISO8601",
    "data": {...}
  }
"""
import hashlib
import hmac
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, Request

from core.config import db, SYROCE_INTEGRATION_ENABLED
from core.tenant_guard import new_id, now_utc

logger = logging.getLogger("omnihub.syroce_webhooks")
router = APIRouter(prefix="/api/integrations/syroce", tags=["syroce-webhooks"])


def _verify_signature(api_key: str, raw_body: bytes, signature: str) -> bool:
    if not signature:
        return False
    mac = hmac.new(api_key.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, signature.lower().strip())


_INDEX_READY = False


async def _ensure_index():
    """Unique compound index enforces atomic, race-safe dedup."""
    global _INDEX_READY
    if _INDEX_READY:
        return
    try:
        await db.syroce_inbound_events.create_index(
            [("tenant_id", 1), ("event_id", 1)], unique=True,
            name="uq_syroce_event",
        )
        _INDEX_READY = True
    except Exception as e:
        logger.warning(f"Failed to create syroce dedup index: {e}")


async def _claim_event(event_id: str, tenant_id: str, event: str, body: dict) -> str:
    """Insert-first idempotency lock. Returns 'claimed' on first delivery,
    'duplicate' if event_id already processed. Raises on storage error.

    The unique index on (tenant_id, event_id) makes this atomic across
    concurrent retries.
    """
    await _ensure_index()
    doc = {
        "id": new_id(),
        "event_id": event_id,
        "tenant_id": tenant_id,
        "event": event,
        "body": body,
        "state": "PROCESSING",
        "received_at": now_utc().isoformat(),
    }
    try:
        await db.syroce_inbound_events.insert_one(doc)
        return "claimed"
    except Exception as e:
        if "duplicate key" in str(e).lower() or "E11000" in str(e):
            return "duplicate"
        raise


async def _mark_processed(event_id: str, tenant_id: str, result: dict):
    await db.syroce_inbound_events.update_one(
        {"tenant_id": tenant_id, "event_id": event_id},
        {"$set": {"state": "PROCESSED", "result": result,
                  "processed_at": now_utc().isoformat()}},
    )


async def _mark_failed(event_id: str, tenant_id: str, error: str):
    await db.syroce_inbound_events.update_one(
        {"tenant_id": tenant_id, "event_id": event_id},
        {"$set": {"state": "FAILED", "error": error[:500],
                  "failed_at": now_utc().isoformat()}},
    )


# ============ Event Handlers ============

async def _handle_reservation(tenant_id: str, event: str, data: dict):
    ext_id = data.get("id") or data.get("reservation_id")
    if not ext_id:
        return {"ok": False, "reason": "missing reservation id"}

    payload = {
        "external_id": str(ext_id),
        "tenant_id": tenant_id,
        "external_provider": "syroce",
        "confirmation_code": data.get("confirmation_code") or f"SYR-{ext_id}",
        "guest_name": data.get("guest_name", ""),
        "guest_phone": data.get("guest_phone", ""),
        "guest_email": data.get("guest_email", ""),
        "room_code": data.get("room_code", ""),
        "check_in": data.get("check_in", ""),
        "check_out": data.get("check_out", ""),
        "nights": data.get("nights", 0),
        "guests_count": data.get("guests_count", 1),
        "price_total": data.get("price_total", 0),
        "currency": data.get("currency", "TRY"),
        "status": "CANCELLED" if event == "reservation.cancelled" else data.get("status", "CONFIRMED"),
        "source": "SYROCE_PMS",
        "updated_at": now_utc().isoformat(),
    }

    existing = await db.reservations.find_one({"tenant_id": tenant_id, "external_id": str(ext_id)})
    if existing:
        await db.reservations.update_one({"id": existing["id"], "tenant_id": tenant_id}, {"$set": payload})
        return {"ok": True, "action": "updated", "id": existing["id"]}
    payload["id"] = new_id()
    payload["created_at"] = now_utc().isoformat()
    await db.reservations.insert_one(payload)
    return {"ok": True, "action": "created", "id": payload["id"]}


async def _handle_checkin(tenant_id: str, data: dict):
    room_code = data.get("room_code")
    if not room_code:
        return {"ok": False, "reason": "missing room_code"}

    update = {
        "current_guest_name": data.get("guest_name", ""),
        "current_guest_phone": data.get("guest_phone", ""),
        "current_guest_check_in": data.get("check_in", now_utc().isoformat()),
        "current_guest_check_out": data.get("check_out", ""),
        "status": "occupied",
        "updated_at": now_utc().isoformat(),
    }
    res = await db.rooms.update_one(
        {"tenant_id": tenant_id, "room_code": room_code}, {"$set": update}
    )
    if res.matched_count == 0:
        return {"ok": False, "reason": f"room {room_code} not found"}

    # Touch contact (no PII overwrite if exists)
    phone = data.get("guest_phone", "").strip()
    if phone:
        await db.contacts.update_one(
            {"tenant_id": tenant_id, "phone": phone},
            {
                "$set": {"last_checkin_at": now_utc().isoformat(), "updated_at": now_utc().isoformat()},
                "$setOnInsert": {
                    "id": new_id(), "tenant_id": tenant_id, "phone": phone,
                    "name": data.get("guest_name", ""),
                    "created_at": now_utc().isoformat(),
                },
            },
            upsert=True,
        )
    return {"ok": True, "action": "checkin", "room": room_code}


async def _handle_checkout(tenant_id: str, data: dict):
    room_code = data.get("room_code")
    if not room_code:
        return {"ok": False, "reason": "missing room_code"}
    res = await db.rooms.update_one(
        {"tenant_id": tenant_id, "room_code": room_code},
        {"$set": {
            "status": "needs_cleaning",
            "current_guest_name": "",
            "current_guest_phone": "",
            "current_guest_check_in": "",
            "current_guest_check_out": "",
            "updated_at": now_utc().isoformat(),
        }},
    )
    if res.matched_count == 0:
        return {"ok": False, "reason": f"room {room_code} not found"}
    # Close pending checkout requests for this room
    await db.checkout_requests.update_many(
        {"tenant_id": tenant_id, "room_code": room_code, "status": "PENDING"},
        {"$set": {"status": "COMPLETED", "completed_at": now_utc().isoformat()}},
    )
    return {"ok": True, "action": "checkout", "room": room_code}


async def _handle_folio(tenant_id: str, data: dict):
    entry = {
        "id": new_id(),
        "tenant_id": tenant_id,
        "external_provider": "syroce",
        "external_id": str(data.get("id", "")),
        "room_code": data.get("room_code", ""),
        "type": data.get("type", "charge"),
        "description": data.get("description", ""),
        "amount": data.get("amount", 0),
        "currency": data.get("currency", "TRY"),
        "posted_at": data.get("posted_at", now_utc().isoformat()),
        "created_at": now_utc().isoformat(),
    }
    await db.folio_entries.insert_one(entry)
    return {"ok": True, "action": "folio_posted", "id": entry["id"]}


async def _handle_room_status(tenant_id: str, data: dict):
    room_code = data.get("room_code")
    new_status = data.get("status")
    if not room_code or not new_status:
        return {"ok": False, "reason": "missing room_code or status"}
    res = await db.rooms.update_one(
        {"tenant_id": tenant_id, "room_code": room_code},
        {"$set": {"status": new_status, "updated_at": now_utc().isoformat()}},
    )
    if res.matched_count == 0:
        return {"ok": False, "reason": f"room {room_code} not found"}
    return {"ok": True, "action": "room_status_changed", "room": room_code, "status": new_status}


HANDLERS = {
    "reservation.created": lambda tid, d: _handle_reservation(tid, "reservation.created", d),
    "reservation.updated": lambda tid, d: _handle_reservation(tid, "reservation.updated", d),
    "reservation.cancelled": lambda tid, d: _handle_reservation(tid, "reservation.cancelled", d),
    "guest.checkin": lambda tid, d: _handle_checkin(tid, d),
    "guest.checkout": lambda tid, d: _handle_checkout(tid, d),
    "folio.posted": lambda tid, d: _handle_folio(tid, d),
    "room.status_changed": lambda tid, d: _handle_room_status(tid, d),
}


_AUTH_FAIL = HTTPException(status_code=401, detail="Unauthorized")


@router.post("/inbound")
async def syroce_inbound_webhook(
    request: Request,
    x_syroce_tenant: Optional[str] = Header(default=None),
    x_syroce_signature: Optional[str] = Header(default=None),
    x_syroce_event_id: Optional[str] = Header(default=None),
):
    if not SYROCE_INTEGRATION_ENABLED:
        raise HTTPException(status_code=503, detail="Syroce integration disabled")

    # Required headers — uniform 401 to prevent tenant enumeration.
    if not x_syroce_tenant or not x_syroce_signature or not x_syroce_event_id:
        raise _AUTH_FAIL

    raw_body = await request.body()

    # Tenant + key lookup — failures collapse to generic 401 (no enumeration).
    tenant = await db.tenants.find_one({"external_tenant_id": x_syroce_tenant})
    cfg = None
    if tenant:
        cfg = await db.pms_configs.find_one(
            {"tenant_id": tenant["id"], "provider": "syroce"}
        )
    if not tenant or not cfg or not cfg.get("api_key"):
        # Burn a constant-time compare against a dummy key to equalize timing.
        _verify_signature("dummy" * 8, raw_body, x_syroce_signature)
        raise _AUTH_FAIL

    if not _verify_signature(cfg["api_key"], raw_body, x_syroce_signature):
        logger.warning(f"Syroce inbound signature mismatch tenant={tenant['id']}")
        raise _AUTH_FAIL

    # Parse body AFTER auth so unauthenticated callers can't probe parsers.
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Body must be JSON")

    event = body.get("event") or ""
    data = body.get("data") or {}
    if event not in HANDLERS:
        raise HTTPException(status_code=400, detail=f"Unsupported event: {event}")

    # Insert-first idempotency: atomic claim via unique index. If a concurrent
    # retry won the race, this returns 'duplicate' without re-running the
    # handler.
    try:
        claim = await _claim_event(x_syroce_event_id, tenant["id"], event, body)
    except Exception as e:
        logger.exception(f"Syroce dedup storage error tenant={tenant['id']}")
        raise HTTPException(status_code=503, detail="Storage unavailable")

    if claim == "duplicate":
        return {"ok": True, "deduplicated": True, "event_id": x_syroce_event_id}

    try:
        result = await HANDLERS[event](tenant["id"], data)
    except Exception as e:
        # Mark FAILED so retries can re-enter via a different event_id or be
        # diagnosed; do not delete the lock (would re-process side effects).
        await _mark_failed(x_syroce_event_id, tenant["id"], str(e))
        logger.exception(f"Syroce inbound handler failed tenant={tenant['id']} event={event}")
        raise HTTPException(status_code=500, detail=f"Handler error: {e}")

    await _mark_processed(x_syroce_event_id, tenant["id"], result)
    logger.info(f"Syroce inbound processed tenant={tenant['id']} event={event} result={result}")
    return {"ok": True, "event": event, "result": result}
