"""Guest Services Router - Enhanced guest experience
Hotel info, room service ordering, spa/activity booking, transport,
laundry, wake-up calls, minibar, surveys, announcements, multi-language,
guest push notifications
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
import logging

from core.config import db
from core.tenant_guard import (
    resolve_tenant, serialize_doc, new_id, now_utc,
    find_one_scoped, find_many_scoped,
    insert_scoped, update_scoped, delete_scoped, log_audit, get_current_user
)
from fastapi import Depends

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/guest-services", tags=["guest-services"])


GUEST_STATUS_MESSAGES = {
    "IN_PROGRESS": {
        "housekeeping": {"en": "Housekeeping team is on the way to your room", "tr": "Kat hizmeti ekibi odanıza geliyor"},
        "maintenance": {"en": "Technical team is heading to your room", "tr": "Teknik ekip odanıza geliyor"},
        "room_service": {"en": "Your order is being prepared", "tr": "Siparişiniz hazırlanıyor"},
        "laundry": {"en": "Your laundry is being processed", "tr": "Çamaşırlarınız işleme alındı"},
        "spa": {"en": "Your spa booking is confirmed", "tr": "Spa rezervasyonunuz onaylandı"},
        "transport": {"en": "Your transport is being arranged", "tr": "Transferiniz ayarlanıyor"},
        "wakeup": {"en": "Your wake-up call is scheduled", "tr": "Uyandırma servisiniz ayarlandı"},
        "reception": {"en": "Reception is handling your request", "tr": "Resepsiyon talebinizle ilgileniyor"},
        "default": {"en": "Your request is being processed", "tr": "Talebiniz işleme alındı"},
    },
    "DONE": {
        "housekeeping": {"en": "Housekeeping is complete!", "tr": "Kat hizmeti tamamlandı!"},
        "maintenance": {"en": "Technical service is complete!", "tr": "Teknik servis tamamlandı!"},
        "room_service": {"en": "Your order has been delivered!", "tr": "Siparişiniz teslim edildi!"},
        "laundry": {"en": "Your laundry is ready!", "tr": "Çamaşırlarınız hazır!"},
        "spa": {"en": "Your spa session is complete!", "tr": "Spa seansınız tamamlandı!"},
        "transport": {"en": "Your transport is ready!", "tr": "Transferiniz hazır!"},
        "wakeup": {"en": "Wake-up call completed", "tr": "Uyandırma servisi tamamlandı"},
        "reception": {"en": "Your request has been fulfilled!", "tr": "Talebiniz karşılandı!"},
        "default": {"en": "Your request is complete!", "tr": "Talebiniz tamamlandı!"},
    },
    "PREPARING": {
        "room_service": {"en": "Your order is being prepared in the kitchen", "tr": "Siparişiniz mutfakta hazırlanıyor"},
        "default": {"en": "Your request is being prepared", "tr": "Talebiniz hazırlanıyor"},
    },
    "READY": {
        "room_service": {"en": "Your order is on its way!", "tr": "Siparişiniz yola çıktı!"},
        "default": {"en": "Your request is ready!", "tr": "Talebiniz hazır!"},
    },
    "CONFIRMED": {
        "spa": {"en": "Your spa booking is confirmed!", "tr": "Spa rezervasyonunuz onaylandı!"},
        "transport": {"en": "Your transport is confirmed!", "tr": "Transferiniz onaylandı!"},
        "default": {"en": "Your booking is confirmed!", "tr": "Rezervasyonunuz onaylandı!"},
    },
    "CANCELLED": {
        "default": {"en": "Your request has been cancelled", "tr": "Talebiniz iptal edildi"},
    },
    "SERVED": {
        "room_service": {"en": "Your order has been served. Enjoy!", "tr": "Siparişiniz servis edildi. Afiyet olsun!"},
        "default": {"en": "Service completed!", "tr": "Servis tamamlandı!"},
    },
}

STATUS_TITLES = {
    "IN_PROGRESS": {"en": "In Progress", "tr": "İşleme Alındı"},
    "DONE": {"en": "Completed", "tr": "Tamamlandı"},
    "PREPARING": {"en": "Preparing", "tr": "Hazırlanıyor"},
    "READY": {"en": "Ready", "tr": "Hazır"},
    "CONFIRMED": {"en": "Confirmed", "tr": "Onaylandı"},
    "CANCELLED": {"en": "Cancelled", "tr": "İptal"},
    "SERVED": {"en": "Served", "tr": "Servis Edildi"},
    "CLOSED": {"en": "Closed", "tr": "Kapatıldı"},
}


async def notify_guest_status_change(tenant_id: str, room_code: str, service_type: str, new_status: str, request_description: str = ""):
    """Send push notification to all guest subscriptions for a room when status changes"""
    try:
        subs = await db.guest_push_subscriptions.find({
            "tenant_id": tenant_id,
            "room_code": room_code,
            "active": True
        }).to_list(50)

        if not subs:
            return

        status_msgs = GUEST_STATUS_MESSAGES.get(new_status, {})
        svc_msgs = status_msgs.get(service_type, status_msgs.get("default", {}))
        if not svc_msgs:
            svc_msgs = {"en": f"Request status: {new_status}", "tr": f"Talep durumu: {new_status}"}

        title_msgs = STATUS_TITLES.get(new_status, {"en": new_status, "tr": new_status})

        from routers.push_notifications import send_web_push

        for sub in subs:
            prefs = sub.get("preferences", {})
            if not prefs.get(service_type, True):
                continue

            sub_lang = sub.get("lang", "tr")
            title = f"🏨 {title_msgs.get(sub_lang, title_msgs.get('en', new_status))}"
            body = svc_msgs.get(sub_lang, svc_msgs.get("en", ""))
            if request_description:
                body = f"{body}\n📋 {request_description[:80]}"

            subscription_info = sub.get("subscription", {})
            if subscription_info:
                tenant_doc = await db.tenants.find_one({"id": tenant_id})
                t_slug = tenant_doc.get("slug", "") if tenant_doc else ""
                guest_url = f"/g/{t_slug}/room/{room_code}" if t_slug else "/"
                await send_web_push(
                    subscription_info=subscription_info,
                    title=title,
                    body=body,
                    data={
                        "type": "status_change",
                        "service_type": service_type,
                        "status": new_status,
                        "room_code": room_code,
                        "url": guest_url,
                    }
                )

        await db.guest_notifications.insert_one({
            "id": new_id(),
            "tenant_id": tenant_id,
            "room_code": room_code,
            "service_type": service_type,
            "status": new_status,
            "title_en": title_msgs.get("en", new_status),
            "title_tr": title_msgs.get("tr", new_status),
            "body_en": svc_msgs.get("en", ""),
            "body_tr": svc_msgs.get("tr", ""),
            "read": False,
            "created_at": now_utc().isoformat(),
        })

    except Exception as e:
        logger.error(f"Guest notification failed: {e}")

# Helper: create a guest_request record so all services appear on admin Requests Board
async def _create_linked_request(tid, room, category, dept_code, description, guest_name="", guest_phone="", linked_entity_type="", linked_entity_id=""):
    """Creates a guest_request entry for specialized services so they show on Requests Board"""
    from core.config import db as _db
    req = {
        "id": new_id(),
        "tenant_id": tid,
        "room_id": room["id"],
        "room_code": room.get("room_code", ""),
        "room_number": room.get("room_number", ""),
        "category": category,
        "department_code": dept_code,
        "description": description,
        "priority": "normal",
        "status": "OPEN",
        "guest_name": guest_name,
        "guest_phone": guest_phone,
        "guest_email": "",
        "assigned_to": None,
        "notes": "",
        "first_response_at": None,
        "resolved_at": None,
        "rating": None,
        "rating_comment": None,
        "linked_entity_type": linked_entity_type,
        "linked_entity_id": linked_entity_id,
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat(),
    }
    await _db.guest_requests.insert_one(req)
    return req

# ============ HOTEL INFO (Public - Guest facing) ============
@router.get("/g/{tenant_slug}/hotel-info")
async def get_hotel_info(tenant_slug: str):
    """Get all hotel information for guest display"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    info = await db.hotel_info.find_one({"tenant_id": tid}, {"_id": 0})
    if not info:
        info = {"tenant_id": tid, "facilities": [], "announcements": [], "emergency_contacts": [], "wifi": {}, "policies": {}}
    
    return serialize_doc(info)

@router.get("/g/{tenant_slug}/room-service-menu")
async def get_room_service_menu(tenant_slug: str):
    """Get room service menu for in-room ordering"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    categories = await find_many_scoped("menu_categories", tid, sort=[("sort_order", 1)])
    items = await find_many_scoped("menu_items", tid, {"available": True})
    
    return {"categories": categories, "items": items}

@router.post("/g/{tenant_slug}/room/{room_code}/room-service-order")
async def create_room_service_order(tenant_slug: str, room_code: str, data: dict):
    """Place room service order from room QR"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    room = await find_one_scoped("rooms", tid, {"room_code": room_code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    items = data.get("items", [])
    if not items:
        raise HTTPException(status_code=400, detail="No items in order")
    
    total = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)
    
    order = await insert_scoped("orders", tid, {
        "room_id": room["id"],
        "room_code": room_code,
        "room_number": room.get("room_number", ""),
        "table_id": None,
        "table_code": None,
        "items": items,
        "total": total,
        "status": "RECEIVED",
        "order_type": "room_service",
        "guest_name": data.get("guest_name", ""),
        "guest_phone": data.get("guest_phone", ""),
        "notes": data.get("notes", ""),
    })
    
    # Create notification for kitchen
    await insert_scoped("notifications", tid, {
        "type": "NEW_ROOM_SERVICE_ORDER",
        "title": f"Room Service Order - Room {room.get('room_number', '')}",
        "body": f"{len(items)} items, Total: {total}",
        "department_code": "FB",
        "entity_type": "order",
        "entity_id": order["id"],
        "read": False,
        "priority": "normal",
    })
    
    item_names = ", ".join([i.get("menu_item_name", "") for i in items[:3]])
    await _create_linked_request(tid, room, "room_service", "FB",
        f"Room Service: {item_names} ({len(items)} items, {total} TRY)",
        data.get("guest_name", ""), data.get("guest_phone", ""), "order", order["id"])
    
    # Auto gamification
    try:
        from routers.gamification import auto_check_badges, auto_check_challenges
        contact_id = room.get("current_guest_contact_id", "")
        if contact_id:
            await auto_check_badges(tid, contact_id, "service_used", order["id"])
            await auto_check_challenges(tid, contact_id, "restaurant_order")
            await auto_check_challenges(tid, contact_id, "service_used")
    except Exception:
        pass
    
    return order

@router.post("/g/{tenant_slug}/room/{room_code}/spa-booking")
async def create_spa_booking(tenant_slug: str, room_code: str, data: dict):
    """Book spa/wellness service from room"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    room = await find_one_scoped("rooms", tid, {"room_code": room_code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    booking = await insert_scoped("spa_bookings", tid, {
        "room_id": room["id"],
        "room_code": room_code,
        "room_number": room.get("room_number", ""),
        "service_type": data.get("service_type", ""),
        "preferred_date": data.get("preferred_date", ""),
        "preferred_time": data.get("preferred_time", ""),
        "guest_name": data.get("guest_name", ""),
        "guest_phone": data.get("guest_phone", ""),
        "notes": data.get("notes", ""),
        "status": "PENDING",
        "persons": data.get("persons", 1),
    })
    
    await insert_scoped("notifications", tid, {
        "type": "NEW_SPA_BOOKING",
        "title": f"Spa Booking - Room {room.get('room_number', '')}",
        "body": f"{data.get('service_type', 'Spa')} for {data.get('preferred_date', '')}",
        "department_code": "SPA",
        "entity_type": "spa_booking",
        "entity_id": booking["id"],
        "read": False,
        "priority": "normal",
    })
    
    await _create_linked_request(tid, room, "spa", "SPA",
        f"Spa: {data.get('service_type', '')} - {data.get('preferred_date', '')} {data.get('preferred_time', '')}",
        data.get("guest_name", ""), data.get("guest_phone", ""), "spa_booking", booking["id"])
    
    # Auto gamification: badge + challenge check
    try:
        from routers.gamification import auto_check_badges, auto_check_challenges
        contact_id = room.get("current_guest_contact_id", "")
        if contact_id:
            await auto_check_badges(tid, contact_id, "spa_booking", booking["id"])
            await auto_check_badges(tid, contact_id, "service_used", booking["id"])
            await auto_check_challenges(tid, contact_id, "spa_booking")
            await auto_check_challenges(tid, contact_id, "service_used")
    except Exception:
        pass
    
    return booking

@router.post("/g/{tenant_slug}/room/{room_code}/transport-request")
async def create_transport_request(tenant_slug: str, room_code: str, data: dict):
    """Request transport/shuttle from room"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    room = await find_one_scoped("rooms", tid, {"room_code": room_code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    transport = await insert_scoped("transport_requests", tid, {
        "room_id": room["id"],
        "room_code": room_code,
        "room_number": room.get("room_number", ""),
        "transport_type": data.get("transport_type", "taxi"),
        "pickup_date": data.get("pickup_date", ""),
        "pickup_time": data.get("pickup_time", ""),
        "destination": data.get("destination", ""),
        "passengers": data.get("passengers", 1),
        "guest_name": data.get("guest_name", ""),
        "guest_phone": data.get("guest_phone", ""),
        "notes": data.get("notes", ""),
        "status": "PENDING",
    })
    
    await insert_scoped("notifications", tid, {
        "type": "NEW_TRANSPORT_REQUEST",
        "title": f"Transport Request - Room {room.get('room_number', '')}",
        "body": f"{data.get('transport_type', 'Taxi')} to {data.get('destination', 'N/A')}",
        "department_code": "CONCIERGE",
        "entity_type": "transport_request",
        "entity_id": transport["id"],
        "read": False,
        "priority": "normal",
    })
    
    await _create_linked_request(tid, room, "transport", "CONCIERGE",
        f"Transfer: {data.get('transport_type', 'taxi')} → {data.get('destination', '')} - {data.get('pickup_date', '')} {data.get('pickup_time', '')}",
        data.get("guest_name", ""), data.get("guest_phone", ""), "transport_request", transport["id"])
    
    # Auto gamification
    try:
        from routers.gamification import auto_check_badges, auto_check_challenges
        contact_id = room.get("current_guest_contact_id", "")
        if contact_id:
            await auto_check_badges(tid, contact_id, "service_used", transport["id"])
            await auto_check_challenges(tid, contact_id, "service_used")
    except Exception:
        pass
    
    return transport

@router.post("/g/{tenant_slug}/room/{room_code}/wakeup-call")
async def create_wakeup_call(tenant_slug: str, room_code: str, data: dict):
    """Set wake-up call from room"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    room = await find_one_scoped("rooms", tid, {"room_code": room_code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    wakeup = await insert_scoped("wakeup_calls", tid, {
        "room_id": room["id"],
        "room_code": room_code,
        "room_number": room.get("room_number", ""),
        "wakeup_time": data.get("wakeup_time", ""),
        "wakeup_date": data.get("wakeup_date", ""),
        "guest_name": data.get("guest_name", ""),
        "status": "SCHEDULED",
        "notes": data.get("notes", ""),
    })
    
    await _create_linked_request(tid, room, "wakeup", "FRONTDESK",
        f"Wake-up Call: {data.get('wakeup_date', '')} {data.get('wakeup_time', '')}",
        data.get("guest_name", ""), "", "wakeup_call", wakeup["id"])
    
    await insert_scoped("notifications", tid, {
        "type": "NEW_WAKEUP_CALL",
        "title": f"Wake-up Call - Room {room.get('room_number', '')}",
        "body": f"{data.get('wakeup_date', '')} at {data.get('wakeup_time', '')}",
        "department_code": "FRONTDESK",
        "entity_type": "wakeup_call",
        "entity_id": wakeup["id"],
        "read": False,
        "priority": "normal",
    })
    
    return wakeup

@router.post("/g/{tenant_slug}/room/{room_code}/laundry-request")
async def create_laundry_request(tenant_slug: str, room_code: str, data: dict):
    """Request laundry service"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    room = await find_one_scoped("rooms", tid, {"room_code": room_code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    laundry = await insert_scoped("laundry_requests", tid, {
        "room_id": room["id"],
        "room_code": room_code,
        "room_number": room.get("room_number", ""),
        "service_type": data.get("service_type", "regular"),  # regular, express, dry_clean
        "items_description": data.get("items_description", ""),
        "pickup_time": data.get("pickup_time", ""),
        "guest_name": data.get("guest_name", ""),
        "guest_phone": data.get("guest_phone", ""),
        "status": "PENDING",
        "notes": data.get("notes", ""),
    })
    
    await insert_scoped("notifications", tid, {
        "type": "NEW_LAUNDRY_REQUEST",
        "title": f"Laundry Request - Room {room.get('room_number', '')}",
        "body": f"{data.get('service_type', 'Regular')} laundry service",
        "department_code": "HK",
        "entity_type": "laundry_request",
        "entity_id": laundry["id"],
        "read": False,
        "priority": "normal",
    })
    
    await _create_linked_request(tid, room, "laundry", "HK",
        f"Laundry: {data.get('service_type', 'regular')} - {data.get('items_description', '')}",
        data.get("guest_name", ""), data.get("guest_phone", ""), "laundry_request", laundry["id"])
    
    return laundry

@router.post("/g/{tenant_slug}/room/{room_code}/minibar-order")
async def create_minibar_order(tenant_slug: str, room_code: str, data: dict):
    """Order minibar items"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    room = await find_one_scoped("rooms", tid, {"room_code": room_code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    items = data.get("items", [])
    total = sum(i.get("price", 0) * i.get("quantity", 1) for i in items)
    
    order = await insert_scoped("minibar_orders", tid, {
        "room_id": room["id"],
        "room_code": room_code,
        "room_number": room.get("room_number", ""),
        "items": items,
        "total": total,
        "guest_name": data.get("guest_name", ""),
        "status": "PENDING",
        "notes": data.get("notes", ""),
    })
    
    return order

@router.post("/g/{tenant_slug}/room/{room_code}/survey")
async def submit_survey(tenant_slug: str, room_code: str, data: dict):
    """Submit guest satisfaction survey"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    room = await find_one_scoped("rooms", tid, {"room_code": room_code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    
    survey = await insert_scoped("guest_surveys", tid, {
        "room_id": room["id"],
        "room_code": room_code,
        "room_number": room.get("room_number", ""),
        "overall_rating": data.get("overall_rating", 0),
        "cleanliness_rating": data.get("cleanliness_rating", 0),
        "service_rating": data.get("service_rating", 0),
        "food_rating": data.get("food_rating", 0),
        "comfort_rating": data.get("comfort_rating", 0),
        "location_rating": data.get("location_rating", 0),
        "value_rating": data.get("value_rating", 0),
        "comments": data.get("comments", ""),
        "guest_name": data.get("guest_name", ""),
        "guest_email": data.get("guest_email", ""),
        "would_recommend": data.get("would_recommend", None),
    })
    
    return survey

@router.get("/g/{tenant_slug}/room/{room_code}/my-orders")
async def get_room_orders(tenant_slug: str, room_code: str):
    """Get all orders for a room (room service, minibar)"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    orders = await find_many_scoped("orders", tid, {"room_code": room_code}, sort=[("created_at", -1)], limit=50)
    minibar = await find_many_scoped("minibar_orders", tid, {"room_code": room_code}, sort=[("created_at", -1)], limit=50)
    
    return {"room_service_orders": orders, "minibar_orders": minibar}

@router.get("/g/{tenant_slug}/room/{room_code}/my-bookings")
async def get_room_bookings(tenant_slug: str, room_code: str):
    """Get all bookings for a room (spa, transport, wakeup, laundry)"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    spa = await find_many_scoped("spa_bookings", tid, {"room_code": room_code}, sort=[("created_at", -1)])
    transport = await find_many_scoped("transport_requests", tid, {"room_code": room_code}, sort=[("created_at", -1)])
    wakeup = await find_many_scoped("wakeup_calls", tid, {"room_code": room_code}, sort=[("created_at", -1)])
    laundry = await find_many_scoped("laundry_requests", tid, {"room_code": room_code}, sort=[("created_at", -1)])
    restaurant_rez = await find_many_scoped("restaurant_reservations", tid, {"room_code": room_code}, sort=[("date", -1), ("time", -1)])
    
    return {"spa_bookings": spa, "transport_requests": transport, "wakeup_calls": wakeup, "laundry_requests": laundry, "restaurant_reservations": restaurant_rez}

@router.get("/g/{tenant_slug}/room/{room_code}/folio")
async def get_room_folio(tenant_slug: str, room_code: str):
    """Get room folio - all charges/spending for the current stay"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    room = await find_one_scoped("rooms", tid, {"room_code": room_code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    check_in = room.get("current_guest_check_in", "")
    check_out = room.get("current_guest_check_out", "")

    date_filter = {}
    if check_in:
        date_filter["created_at"] = {"$gte": check_in}

    items = []

    order_query = {"room_code": room_code}
    if check_in:
        order_query["created_at"] = {"$gte": check_in}
    orders = await find_many_scoped("orders", tid, order_query, sort=[("created_at", -1)], limit=100)
    for o in orders:
        desc_parts = [f'{i.get("menu_item_name","")} x{i.get("quantity",1)}' for i in o.get("items", [])[:3]]
        items.append({
            "id": o["id"],
            "type": "room_service",
            "type_label": "Oda Servisi",
            "type_label_en": "Room Service",
            "description": ", ".join(desc_parts),
            "amount": o.get("total", 0),
            "currency": "TRY",
            "status": o.get("status", ""),
            "date": o.get("created_at", ""),
        })

    minibar_query = {"room_code": room_code}
    if check_in:
        minibar_query["created_at"] = {"$gte": check_in}
    minibar = await find_many_scoped("minibar_orders", tid, minibar_query, sort=[("created_at", -1)], limit=100)
    for m in minibar:
        desc_parts = [f'{i.get("name", i.get("menu_item_name",""))} x{i.get("quantity",1)}' for i in m.get("items", [])[:3]]
        items.append({
            "id": m["id"],
            "type": "minibar",
            "type_label": "Minibar",
            "type_label_en": "Minibar",
            "description": ", ".join(desc_parts),
            "amount": m.get("total", 0),
            "currency": "TRY",
            "status": m.get("status", ""),
            "date": m.get("created_at", ""),
        })

    spa_query = {"room_code": room_code}
    if check_in:
        spa_query["created_at"] = {"$gte": check_in}
    spa = await find_many_scoped("spa_bookings", tid, spa_query, sort=[("created_at", -1)])
    for s in spa:
        svc_type = s.get("service_type", "")
        spa_svc = None
        if svc_type:
            spa_svc = await find_one_scoped("spa_services", tid, {"id": svc_type})
            if not spa_svc:
                spa_svc = await find_one_scoped("spa_services", tid, {"name": svc_type})
        spa_price = spa_svc.get("price", 0) if spa_svc else 0
        spa_name = spa_svc.get("name", svc_type) if spa_svc else (svc_type or "Spa")
        items.append({
            "id": s["id"],
            "type": "spa",
            "type_label": "Spa",
            "type_label_en": "Spa",
            "description": spa_name,
            "amount": spa_price,
            "currency": "TRY",
            "status": s.get("status", ""),
            "date": s.get("created_at", ""),
        })

    laundry_query = {"room_code": room_code}
    if check_in:
        laundry_query["created_at"] = {"$gte": check_in}
    laundry = await find_many_scoped("laundry_requests", tid, laundry_query, sort=[("created_at", -1)])
    laundry_prices = {"regular": 150, "express": 250, "dry_clean": 300}
    for l in laundry:
        stype = l.get("service_type", "regular")
        items.append({
            "id": l["id"],
            "type": "laundry",
            "type_label": "Camasir",
            "type_label_en": "Laundry",
            "description": f'{stype.replace("_"," ").title()} - {l.get("items_description","")}',
            "amount": laundry_prices.get(stype, 150),
            "currency": "TRY",
            "status": l.get("status", ""),
            "date": l.get("created_at", ""),
        })

    transport_query = {"room_code": room_code}
    if check_in:
        transport_query["created_at"] = {"$gte": check_in}
    transport = await find_many_scoped("transport_requests", tid, transport_query, sort=[("created_at", -1)])
    transport_prices = {"taxi": 0, "airport_transfer": 500, "vip_transfer": 1000, "shuttle": 200}
    for tr in transport:
        ttype = tr.get("transport_type", "taxi")
        price = transport_prices.get(ttype, 0)
        items.append({
            "id": tr["id"],
            "type": "transport",
            "type_label": "Transfer",
            "type_label_en": "Transport",
            "description": f'{ttype.replace("_"," ").title()} → {tr.get("destination","")}',
            "amount": price,
            "currency": "TRY",
            "status": tr.get("status", ""),
            "date": tr.get("created_at", ""),
        })

    items.sort(key=lambda x: x.get("date", ""), reverse=True)

    total = sum(i["amount"] for i in items)

    guest_name = room.get("current_guest_name", "")

    return {
        "room_number": room.get("room_number", ""),
        "room_type": room.get("room_type", ""),
        "guest_name": guest_name,
        "check_in": check_in,
        "check_out": check_out,
        "items": items,
        "total": total,
        "currency": "TRY",
    }

@router.get("/g/{tenant_slug}/announcements")
async def get_announcements(tenant_slug: str):
    """Get active announcements for guests"""
    tenant = await resolve_tenant(tenant_slug)
    return await find_many_scoped("announcements", tenant["id"], {"active": True}, sort=[("created_at", -1)])

@router.get("/g/{tenant_slug}/spa-services")
async def get_spa_services(tenant_slug: str):
    """Get available spa/wellness services"""
    tenant = await resolve_tenant(tenant_slug)
    return await find_many_scoped("spa_services", tenant["id"], {"available": True}, sort=[("sort_order", 1)])

@router.get("/g/{tenant_slug}/activities")
async def get_activities(tenant_slug: str):
    """Get available activities and excursions"""
    tenant = await resolve_tenant(tenant_slug)
    return await find_many_scoped("activities", tenant["id"], {"available": True}, sort=[("sort_order", 1)])

# ============ RESTAURANT RESERVATION (Guest facing) ============

@router.get("/g/{tenant_slug}/restaurants")
async def get_restaurants(tenant_slug: str):
    """Get available restaurants for reservation"""
    tenant = await resolve_tenant(tenant_slug)
    return await find_many_scoped("restaurants", tenant["id"], {"active": True}, sort=[("sort_order", 1)])

@router.get("/g/{tenant_slug}/restaurants/{restaurant_id}/availability")
async def check_availability(tenant_slug: str, restaurant_id: str, date: str = "", party_size: int = 2):
    """Check available time slots for a given date & party size"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    restaurant = await find_one_scoped("restaurants", tid, {"id": restaurant_id})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    # Get existing reservations for the date
    existing = await find_many_scoped("restaurant_reservations", tid, {
        "restaurant_id": restaurant_id,
        "date": date,
        "status": {"$in": ["pending", "confirmed"]},
    })

    # Build available slots based on restaurant config
    open_time = restaurant.get("open_time", "12:00")
    close_time = restaurant.get("close_time", "22:00")
    slot_duration = restaurant.get("slot_duration_minutes", 90)
    total_capacity = restaurant.get("total_seats", 40)

    from datetime import datetime as dt, timedelta
    slots = []
    try:
        current = dt.strptime(open_time, "%H:%M")
        end = dt.strptime(close_time, "%H:%M")
        while current < end:
            time_str = current.strftime("%H:%M")
            # Count reserved seats for this slot
            reserved = sum(
                r.get("party_size", 0) for r in existing
                if r.get("time") == time_str
            )
            available_seats = total_capacity - reserved
            slots.append({
                "time": time_str,
                "available_seats": max(available_seats, 0),
                "is_available": available_seats >= party_size,
            })
            current += timedelta(minutes=slot_duration)
    except Exception:
        pass

    return {"restaurant": restaurant, "date": date, "party_size": party_size, "slots": slots}

@router.post("/g/{tenant_slug}/room/{room_code}/restaurant-reservation")
async def create_restaurant_reservation(tenant_slug: str, room_code: str, data: dict):
    """Guest creates a restaurant reservation from room QR"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    room = await find_one_scoped("rooms", tid, {"room_code": room_code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    restaurant_id = data.get("restaurant_id", "")
    date = data.get("date", "")
    time = data.get("time", "")
    party_size = data.get("party_size", 2)

    if not date or not time:
        raise HTTPException(status_code=400, detail="Date and time are required")

    # Check if restaurant exists
    restaurant = None
    if restaurant_id:
        restaurant = await find_one_scoped("restaurants", tid, {"id": restaurant_id})

    reservation = await insert_scoped("restaurant_reservations", tid, {
        "restaurant_id": restaurant_id,
        "restaurant_name": data.get("restaurant_name", restaurant.get("name", "Main Restaurant") if restaurant else "Main Restaurant"),
        "room_id": room["id"],
        "room_code": room_code,
        "room_number": room.get("room_number", ""),
        "date": date,
        "time": time,
        "party_size": party_size,
        "guest_name": data.get("guest_name", ""),
        "guest_phone": data.get("guest_phone", ""),
        "guest_email": data.get("guest_email", ""),
        "special_requests": data.get("special_requests", ""),
        "occasion": data.get("occasion", ""),
        "seating_preference": data.get("seating_preference", "no_preference"),
        "status": "pending",
    })

    # Create notification
    await insert_scoped("notifications", tid, {
        "type": "NEW_RESTAURANT_RESERVATION",
        "title": f"Restaurant Reservation - Room {room.get('room_number', '')}",
        "body": f"{party_size} guests, {date} at {time}",
        "department_code": "FB",
        "entity_type": "restaurant_reservation",
        "entity_id": reservation["id"],
        "read": False,
        "priority": "normal",
    })

    restaurant_name = data.get("restaurant_name", "Restaurant")
    await _create_linked_request(tid, room, "restaurant_reservation", "FB",
        f"Restaurant: {restaurant_name} - {date} {time}, {party_size} guests",
        data.get("guest_name", ""), data.get("guest_phone", ""), "restaurant_reservation", reservation["id"])

    return reservation

@router.get("/g/{tenant_slug}/room/{room_code}/my-reservations")
async def get_my_restaurant_reservations(tenant_slug: str, room_code: str):
    """Guest views their restaurant reservations"""
    tenant = await resolve_tenant(tenant_slug)
    return await find_many_scoped("restaurant_reservations", tenant["id"],
        {"room_code": room_code}, sort=[("date", 1), ("time", 1)])

# ============ RESTAURANT RESERVATION (Admin) ============

@router.get("/tenants/{tenant_slug}/restaurants")
async def list_restaurants_admin(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    return await find_many_scoped("restaurants", tenant["id"], sort=[("sort_order", 1)])

@router.post("/tenants/{tenant_slug}/restaurants")
async def create_restaurant(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    return await insert_scoped("restaurants", tenant["id"], {
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "cuisine_type": data.get("cuisine_type", ""),
        "open_time": data.get("open_time", "12:00"),
        "close_time": data.get("close_time", "22:00"),
        "slot_duration_minutes": data.get("slot_duration_minutes", 90),
        "total_seats": data.get("total_seats", 40),
        "dress_code": data.get("dress_code", ""),
        "phone": data.get("phone", ""),
        "location": data.get("location", ""),
        "active": data.get("active", True),
        "sort_order": data.get("sort_order", 0),
    })

@router.patch("/tenants/{tenant_slug}/restaurants/{restaurant_id}")
async def update_restaurant(tenant_slug: str, restaurant_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    update = {}
    for k in ["name","description","cuisine_type","open_time","close_time","slot_duration_minutes","total_seats","dress_code","phone","location","active","sort_order"]:
        if k in data:
            update[k] = data[k]
    return await update_scoped("restaurants", tenant["id"], restaurant_id, update)

@router.delete("/tenants/{tenant_slug}/restaurants/{restaurant_id}")
async def delete_restaurant(tenant_slug: str, restaurant_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    await delete_scoped("restaurants", tenant["id"], restaurant_id)
    return {"deleted": True}

@router.get("/tenants/{tenant_slug}/restaurant-reservations")
async def list_restaurant_reservations(tenant_slug: str, date: Optional[str] = None,
                                        status: Optional[str] = None,
                                        restaurant_id: Optional[str] = None,
                                        user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if date:
        query["date"] = date
    if status:
        query["status"] = status
    if restaurant_id:
        query["restaurant_id"] = restaurant_id
    return await find_many_scoped("restaurant_reservations", tenant["id"], query,
                                   sort=[("date", 1), ("time", 1)])

@router.patch("/tenants/{tenant_slug}/restaurant-reservations/{reservation_id}")
async def update_restaurant_reservation(tenant_slug: str, reservation_id: str, data: dict,
                                          user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    update = {}
    if "status" in data:
        update["status"] = data["status"]
    if "notes" in data:
        update["notes"] = data["notes"]
    if "table_number" in data:
        update["table_number"] = data["table_number"]
    return await update_scoped("restaurant_reservations", tenant["id"], reservation_id, update)

# ============ ADMIN ENDPOINTS ============

@router.put("/tenants/{tenant_slug}/hotel-info")
async def update_hotel_info(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    """Update hotel information"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    
    existing = await db.hotel_info.find_one({"tenant_id": tid})
    update_data = {
        "tenant_id": tid,
        "hotel_name": data.get("hotel_name", tenant["name"]),
        "description": data.get("description", ""),
        "address": data.get("address", ""),
        "phone": data.get("phone", ""),
        "email": data.get("email", ""),
        "website": data.get("website", ""),
        "wifi_name": data.get("wifi_name", ""),
        "wifi_password": data.get("wifi_password", ""),
        "check_in_time": data.get("check_in_time", "14:00"),
        "check_out_time": data.get("check_out_time", "12:00"),
        "facilities": data.get("facilities", []),
        "emergency_contacts": data.get("emergency_contacts", []),
        "announcements": data.get("announcements", []),
        "pool_hours": data.get("pool_hours", ""),
        "spa_hours": data.get("spa_hours", ""),
        "restaurant_hours": data.get("restaurant_hours", ""),
        "gym_hours": data.get("gym_hours", ""),
        "parking_info": data.get("parking_info", ""),
        "pet_policy": data.get("pet_policy", ""),
        "smoking_policy": data.get("smoking_policy", ""),
        "languages": data.get("languages", ["tr", "en"]),
        "currency": data.get("currency", "TRY"),
        "updated_at": now_utc().isoformat(),
    }
    
    if existing:
        await db.hotel_info.update_one({"tenant_id": tid}, {"$set": update_data})
    else:
        update_data["id"] = new_id()
        update_data["created_at"] = now_utc().isoformat()
        await db.hotel_info.insert_one(update_data)
    
    result = await db.hotel_info.find_one({"tenant_id": tid}, {"_id": 0})
    return serialize_doc(result)

@router.get("/tenants/{tenant_slug}/hotel-info")
async def get_hotel_info_admin(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    info = await db.hotel_info.find_one({"tenant_id": tenant["id"]}, {"_id": 0})
    return serialize_doc(info) if info else {}

# Spa Services Admin
@router.get("/tenants/{tenant_slug}/spa-services")
async def list_spa_services_admin(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    return await find_many_scoped("spa_services", tenant["id"], sort=[("sort_order", 1)])

@router.post("/tenants/{tenant_slug}/spa-services")
async def create_spa_service(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    return await insert_scoped("spa_services", tenant["id"], {
        "name": data.get("name", ""),
        "description": data.get("description", ""),
        "duration_minutes": data.get("duration_minutes", 60),
        "price": data.get("price", 0),
        "category": data.get("category", "massage"),
        "available": data.get("available", True),
        "sort_order": data.get("sort_order", 0),
    })

@router.delete("/tenants/{tenant_slug}/spa-services/{service_id}")
async def delete_spa_service(tenant_slug: str, service_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    await delete_scoped("spa_services", tenant["id"], service_id)
    return {"deleted": True}

# Announcements Admin
@router.get("/tenants/{tenant_slug}/announcements")
async def list_announcements_admin(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    return await find_many_scoped("announcements", tenant["id"], sort=[("created_at", -1)])

@router.post("/tenants/{tenant_slug}/announcements")
async def create_announcement(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    return await insert_scoped("announcements", tenant["id"], {
        "title": data.get("title", ""),
        "title_tr": data.get("title_tr", ""),
        "body": data.get("body", ""),
        "body_tr": data.get("body_tr", ""),
        "type": data.get("type", "info"),  # info, warning, event, promo
        "active": data.get("active", True),
        "priority": data.get("priority", "normal"),
        "expires_at": data.get("expires_at", None),
    })

@router.delete("/tenants/{tenant_slug}/announcements/{ann_id}")
async def delete_announcement(tenant_slug: str, ann_id: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    await delete_scoped("announcements", tenant["id"], ann_id)
    return {"deleted": True}

# Spa Bookings Admin
@router.get("/tenants/{tenant_slug}/spa-bookings")
async def list_spa_bookings(tenant_slug: str, status: Optional[str] = None, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if status:
        query["status"] = status.upper()
    return await find_many_scoped("spa_bookings", tenant["id"], query, sort=[("created_at", -1)])

@router.patch("/tenants/{tenant_slug}/spa-bookings/{booking_id}")
async def update_spa_booking(tenant_slug: str, booking_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    booking = await find_one_scoped("spa_bookings", tenant["id"], {"id": booking_id})
    update = {}
    if "status" in data:
        update["status"] = data["status"].upper()
    if "notes" in data:
        update["notes"] = data["notes"]
    result = await update_scoped("spa_bookings", tenant["id"], booking_id, update)
    if "status" in data and booking:
        try:
            await notify_guest_status_change(tenant["id"], booking.get("room_code", ""), "spa", data["status"].upper(), booking.get("service_type", ""))
        except Exception as e:
            logger.error(f"Guest notify error: {e}")
    return result

# Transport Requests Admin
@router.get("/tenants/{tenant_slug}/transport-requests")
async def list_transport_requests(tenant_slug: str, status: Optional[str] = None, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if status:
        query["status"] = status.upper()
    return await find_many_scoped("transport_requests", tenant["id"], query, sort=[("created_at", -1)])

@router.patch("/tenants/{tenant_slug}/transport-requests/{req_id}")
async def update_transport_request(tenant_slug: str, req_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    req = await find_one_scoped("transport_requests", tenant["id"], {"id": req_id})
    update = {}
    if "status" in data:
        update["status"] = data["status"].upper()
    if "notes" in data:
        update["notes"] = data["notes"]
    if "driver_name" in data:
        update["driver_name"] = data["driver_name"]
    if "vehicle_info" in data:
        update["vehicle_info"] = data["vehicle_info"]
    result = await update_scoped("transport_requests", tenant["id"], req_id, update)
    if "status" in data and req:
        try:
            desc = f'{req.get("transport_type", "")} → {req.get("destination", "")}'
            await notify_guest_status_change(tenant["id"], req.get("room_code", ""), "transport", data["status"].upper(), desc)
        except Exception as e:
            logger.error(f"Guest notify error: {e}")
    return result

# Laundry Requests Admin  
@router.get("/tenants/{tenant_slug}/laundry-requests")
async def list_laundry_requests(tenant_slug: str, status: Optional[str] = None, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    query = {}
    if status:
        query["status"] = status.upper()
    return await find_many_scoped("laundry_requests", tenant["id"], query, sort=[("created_at", -1)])

@router.patch("/tenants/{tenant_slug}/laundry-requests/{req_id}")
async def update_laundry_request(tenant_slug: str, req_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    req = await find_one_scoped("laundry_requests", tenant["id"], {"id": req_id})
    update = {}
    if "status" in data:
        update["status"] = data["status"].upper()
    if "notes" in data:
        update["notes"] = data["notes"]
    result = await update_scoped("laundry_requests", tenant["id"], req_id, update)
    if "status" in data and req:
        try:
            desc = f'{req.get("service_type", "regular")} - {req.get("items_description", "")}'
            await notify_guest_status_change(tenant["id"], req.get("room_code", ""), "laundry", data["status"].upper(), desc)
        except Exception as e:
            logger.error(f"Guest notify error: {e}")
    return result

# Wake-up Calls Admin
@router.get("/tenants/{tenant_slug}/wakeup-calls")
async def list_wakeup_calls(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    return await find_many_scoped("wakeup_calls", tenant["id"], sort=[("wakeup_date", 1), ("wakeup_time", 1)])

@router.patch("/tenants/{tenant_slug}/wakeup-calls/{call_id}")
async def update_wakeup_call(tenant_slug: str, call_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    call = await find_one_scoped("wakeup_calls", tenant["id"], {"id": call_id})
    update = {}
    if "status" in data:
        update["status"] = data["status"].upper()
    result = await update_scoped("wakeup_calls", tenant["id"], call_id, update)
    if "status" in data and call:
        try:
            desc = f'{call.get("wakeup_date", "")} {call.get("wakeup_time", "")}'
            await notify_guest_status_change(tenant["id"], call.get("room_code", ""), "wakeup", data["status"].upper(), desc)
        except Exception as e:
            logger.error(f"Guest notify error: {e}")
    return result

# Guest Surveys Admin
@router.get("/tenants/{tenant_slug}/surveys")
async def list_surveys(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    surveys = await find_many_scoped("guest_surveys", tenant["id"], sort=[("created_at", -1)])
    return surveys

@router.get("/tenants/{tenant_slug}/surveys/stats")
async def get_survey_stats(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]
    surveys = await find_many_scoped("guest_surveys", tid)
    
    if not surveys:
        return {"total": 0, "avg_overall": 0, "avg_cleanliness": 0, "avg_service": 0, "avg_food": 0, "avg_comfort": 0, "recommend_pct": 0}
    
    total = len(surveys)
    avg = lambda key: round(sum(s.get(key, 0) for s in surveys) / total, 1) if total else 0
    recommend = sum(1 for s in surveys if s.get("would_recommend")) / total * 100 if total else 0
    
    return {
        "total": total,
        "avg_overall": avg("overall_rating"),
        "avg_cleanliness": avg("cleanliness_rating"),
        "avg_service": avg("service_rating"),
        "avg_food": avg("food_rating"),
        "avg_comfort": avg("comfort_rating"),
        "recommend_pct": round(recommend, 1),
    }


# ============ GUEST SERVICES CONFIG (Toggle services per hotel) ============

# Default service definitions - all available services
ALL_GUEST_SERVICES = [
    {"key": "housekeeping", "label": "Housekeeping", "label_tr": "Kat Hizmeti", "department_code": "HK", "icon": "sparkles", "default_enabled": True},
    {"key": "maintenance", "label": "Technical Service", "label_tr": "Teknik Servis", "department_code": "TECH", "icon": "wrench", "default_enabled": True},
    {"key": "room_service", "label": "Room Service", "label_tr": "Oda Servisi", "department_code": "FB", "icon": "utensils", "default_enabled": True},
    {"key": "reception", "label": "Reception", "label_tr": "Resepsiyon", "department_code": "FRONTDESK", "icon": "bell", "default_enabled": True},
    {"key": "laundry", "label": "Laundry & Ironing", "label_tr": "Çamaşır / Ütü", "department_code": "HK", "icon": "shirt", "default_enabled": False},
    {"key": "spa", "label": "Spa & Wellness", "label_tr": "Spa & Masaj", "department_code": "SPA", "icon": "heart", "default_enabled": False},
    {"key": "transport", "label": "Transport / Transfer", "label_tr": "Transfer / Ulaşım", "department_code": "CONCIERGE", "icon": "car", "default_enabled": False},
    {"key": "wakeup", "label": "Wake-up Call", "label_tr": "Uyandırma Servisi", "department_code": "FRONTDESK", "icon": "alarm", "default_enabled": True},
    {"key": "bellboy", "label": "Bellboy / Luggage", "label_tr": "Bellboy / Bavul", "department_code": "BELL", "icon": "luggage", "default_enabled": False},
    {"key": "key_access", "label": "Key / Card Issue", "label_tr": "Anahtar / Kart", "department_code": "FRONTDESK", "icon": "key", "default_enabled": True},
    {"key": "minibar", "label": "Minibar", "label_tr": "Minibar", "department_code": "FB", "icon": "coffee", "default_enabled": False},
    {"key": "checkout", "label": "Express Check-out", "label_tr": "Hızlı Çıkış", "department_code": "FRONTDESK", "icon": "logout", "default_enabled": True},
    {"key": "complaint", "label": "Complaint", "label_tr": "Şikayet / Öneri", "department_code": "FRONTDESK", "icon": "alert", "default_enabled": True},
    {"key": "restaurant_reservation", "label": "Restaurant Reservation", "label_tr": "Restoran Rezervasyonu", "department_code": "FB", "icon": "calendar", "default_enabled": False},
    {"key": "other", "label": "Other Request", "label_tr": "Diğer Talep", "department_code": "FRONTDESK", "icon": "help", "default_enabled": True},
]

def _get_default_config():
    """Build default config dict from ALL_GUEST_SERVICES"""
    return {s["key"]: s["default_enabled"] for s in ALL_GUEST_SERVICES}

@router.get("/g/{tenant_slug}/active-services")
async def get_active_services(tenant_slug: str):
    """Public: Return only the services that this hotel has enabled"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    cfg_doc = await db.guest_services_config.find_one({"tenant_id": tid}, {"_id": 0})
    enabled_map = (serialize_doc(cfg_doc) if cfg_doc else {}).get("services", _get_default_config())

    result = []
    for svc in ALL_GUEST_SERVICES:
        if enabled_map.get(svc["key"], svc["default_enabled"]):
            result.append(svc)
    return result

@router.get("/tenants/{tenant_slug}/services-config")
async def get_services_config(tenant_slug: str, user=Depends(get_current_user)):
    """Admin: Get full service configuration (all services + enabled flags)"""
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    cfg_doc = await db.guest_services_config.find_one({"tenant_id": tid}, {"_id": 0})
    enabled_map = (serialize_doc(cfg_doc) if cfg_doc else {}).get("services", _get_default_config())

    services = []
    for svc in ALL_GUEST_SERVICES:
        services.append({**svc, "enabled": enabled_map.get(svc["key"], svc["default_enabled"])})
    return services

@router.put("/tenants/{tenant_slug}/services-config")
async def update_services_config(tenant_slug: str, data: dict, user=Depends(get_current_user)):
    """Admin: Update which services are enabled/disabled for guests.
    Body: { "services": { "spa": true, "laundry": false, ... } }
    """
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    new_map = data.get("services", {})
    # Merge with defaults so unknown keys keep their default
    merged = _get_default_config()
    for k, v in new_map.items():
        if k in merged:
            merged[k] = bool(v)

    existing = await db.guest_services_config.find_one({"tenant_id": tid})
    if existing:
        await db.guest_services_config.update_one(
            {"tenant_id": tid},
            {"$set": {"services": merged, "updated_at": now_utc().isoformat()}}
        )
    else:
        await db.guest_services_config.insert_one({
            "id": new_id(),
            "tenant_id": tid,
            "services": merged,
            "created_at": now_utc().isoformat(),
            "updated_at": now_utc().isoformat(),
        })

    await log_audit(tid, "services_config_updated", "guest_services_config", tid, user.get("id", ""), {"services": merged})

    # Return the full list with updated flags
    services = []
    for svc in ALL_GUEST_SERVICES:
        services.append({**svc, "enabled": merged.get(svc["key"], svc["default_enabled"])})
    return services


# ============ GUEST PUSH NOTIFICATIONS ============

@router.get("/g/{tenant_slug}/push/vapid-key")
async def guest_vapid_key(tenant_slug: str):
    from routers.push_notifications import _get_vapid_keys
    _, public_key = _get_vapid_keys()
    return {"public_key": public_key}


@router.post("/g/{tenant_slug}/room/{room_code}/push/subscribe")
async def guest_push_subscribe(tenant_slug: str, room_code: str, data: dict):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    room = await find_one_scoped("rooms", tid, {"room_code": room_code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    subscription = data.get("subscription", {})
    if not subscription or not subscription.get("endpoint"):
        raise HTTPException(status_code=400, detail="Invalid subscription")

    endpoint = subscription.get("endpoint", "")
    existing = await db.guest_push_subscriptions.find_one({
        "tenant_id": tid,
        "room_code": room_code,
        "subscription.endpoint": endpoint
    })

    prefs = data.get("preferences", {
        "housekeeping": True,
        "maintenance": True,
        "room_service": True,
        "laundry": True,
        "spa": True,
        "transport": True,
        "wakeup": True,
        "reception": True,
    })
    lang = data.get("lang", "tr")

    if existing:
        await db.guest_push_subscriptions.update_one(
            {"_id": existing["_id"]},
            {"$set": {
                "subscription": subscription,
                "preferences": prefs,
                "lang": lang,
                "active": True,
                "updated_at": now_utc().isoformat()
            }}
        )
        return {"status": "updated", "message": "Subscription updated"}
    else:
        await db.guest_push_subscriptions.insert_one({
            "id": new_id(),
            "tenant_id": tid,
            "room_code": room_code,
            "subscription": subscription,
            "preferences": prefs,
            "lang": lang,
            "active": True,
            "created_at": now_utc().isoformat(),
            "updated_at": now_utc().isoformat(),
        })
        return {"status": "subscribed", "message": "Push notifications enabled"}


@router.delete("/g/{tenant_slug}/room/{room_code}/push/unsubscribe")
async def guest_push_unsubscribe(tenant_slug: str, room_code: str, data: dict):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    endpoint = data.get("endpoint", "")
    if endpoint:
        await db.guest_push_subscriptions.update_many(
            {"tenant_id": tid, "room_code": room_code, "subscription.endpoint": endpoint},
            {"$set": {"active": False, "updated_at": now_utc().isoformat()}}
        )
    else:
        await db.guest_push_subscriptions.update_many(
            {"tenant_id": tid, "room_code": room_code},
            {"$set": {"active": False, "updated_at": now_utc().isoformat()}}
        )
    return {"status": "unsubscribed"}


@router.get("/g/{tenant_slug}/room/{room_code}/push/preferences")
async def guest_push_preferences(tenant_slug: str, room_code: str, endpoint: str = ""):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    query = {"tenant_id": tid, "room_code": room_code, "active": True}
    if endpoint:
        query["subscription.endpoint"] = endpoint

    sub = await db.guest_push_subscriptions.find_one(query)
    if not sub:
        return {
            "subscribed": False,
            "preferences": {
                "housekeeping": True, "maintenance": True, "room_service": True,
                "laundry": True, "spa": True, "transport": True,
                "wakeup": True, "reception": True,
            }
        }

    return {
        "subscribed": True,
        "preferences": sub.get("preferences", {}),
        "lang": sub.get("lang", "tr"),
    }


@router.put("/g/{tenant_slug}/room/{room_code}/push/preferences")
async def update_guest_push_preferences(tenant_slug: str, room_code: str, data: dict):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    endpoint = data.get("endpoint", "")
    prefs = data.get("preferences", {})
    lang = data.get("lang")

    update_data = {"preferences": prefs, "updated_at": now_utc().isoformat()}
    if lang:
        update_data["lang"] = lang

    query = {"tenant_id": tid, "room_code": room_code, "active": True}
    if endpoint:
        query["subscription.endpoint"] = endpoint

    result = await db.guest_push_subscriptions.update_many(query, {"$set": update_data})
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="No active subscription found")

    return {"status": "updated", "preferences": prefs}


@router.get("/g/{tenant_slug}/room/{room_code}/notifications")
async def guest_notifications_list(tenant_slug: str, room_code: str, limit: int = 20):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    notifs = await db.guest_notifications.find(
        {"tenant_id": tid, "room_code": room_code}
    ).sort("created_at", -1).limit(limit).to_list(limit)

    for n in notifs:
        n.pop("_id", None)
    return notifs


@router.post("/g/{tenant_slug}/room/{room_code}/notifications/mark-read")
async def guest_notifications_mark_read(tenant_slug: str, room_code: str):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    await db.guest_notifications.update_many(
        {"tenant_id": tid, "room_code": room_code, "read": False},
        {"$set": {"read": True}}
    )
    return {"status": "ok"}


@router.get("/g/{tenant_slug}/room/{room_code}/notifications/unread-count")
async def guest_notifications_unread(tenant_slug: str, room_code: str):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    count = await db.guest_notifications.count_documents(
        {"tenant_id": tid, "room_code": room_code, "read": False}
    )
    return {"count": count}


@router.get("/g/{tenant_slug}/rooms/availability")
async def check_room_availability(tenant_slug: str, check_in: str = "", check_out: str = "", guests: int = 1):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    room_rates = await db.room_rates.find({"tenant_id": tid}).to_list(50)
    available = []
    for rt in room_rates:
        rt = serialize_doc(rt)
        existing = await db.reservations.count_documents({
            "tenant_id": tid, "room_type": rt.get("room_type", ""),
            "status": {"$in": ["CONFIRMED", "CHECKED_IN"]},
            "$or": [
                {"check_in": {"$lt": check_out}, "check_out": {"$gt": check_in}}
            ]
        }) if check_in and check_out else 0
        capacity = rt.get("total_rooms", 10)
        rooms_left = max(0, capacity - existing)
        if rooms_left > 0 or not check_in:
            nights = 1
            if check_in and check_out:
                from datetime import datetime
                try:
                    d1 = datetime.fromisoformat(check_in)
                    d2 = datetime.fromisoformat(check_out)
                    nights = max(1, (d2 - d1).days)
                except: pass
            base_price = rt.get("base_price", rt.get("price_per_night", 0))
            available.append({
                "room_type": rt.get("room_type", ""),
                "display_name": rt.get("display_name", rt.get("room_type", "").replace("_", " ").title()),
                "base_price": base_price,
                "total_price": base_price * nights,
                "nights": nights,
                "currency": rt.get("currency", "TRY"),
                "max_guests": rt.get("max_guests", 2),
                "amenities": rt.get("amenities", []),
                "rooms_available": rooms_left,
            })
    return {"available_rooms": available, "check_in": check_in, "check_out": check_out}


@router.post("/g/{tenant_slug}/rooms/reserve")
async def guest_create_reservation(tenant_slug: str, data: dict):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    required = ["room_type", "check_in", "check_out", "guest_name"]
    for f in required:
        if not data.get(f):
            raise HTTPException(status_code=400, detail=f"{f} required")

    room_rate = await db.room_rates.find_one({"tenant_id": tid, "room_type": data["room_type"]})
    if not room_rate:
        raise HTTPException(status_code=400, detail="Invalid room type")

    from datetime import datetime
    try:
        d1 = datetime.fromisoformat(data["check_in"])
        d2 = datetime.fromisoformat(data["check_out"])
        nights = max(1, (d2 - d1).days)
    except:
        raise HTTPException(status_code=400, detail="Invalid dates")

    base_price = room_rate.get("base_price", room_rate.get("price_per_night", 0))
    total = base_price * nights

    from core.middleware import generate_unique_confirmation_code
    confirmation_code = await generate_unique_confirmation_code(tid, "GHI")

    reservation = {
        "id": new_id(), "tenant_id": tid,
        "property_id": data.get("property_id", ""),
        "status": "PENDING",
        "confirmation_code": confirmation_code,
        "guest_name": data["guest_name"],
        "guest_email": data.get("guest_email", ""),
        "guest_phone": data.get("guest_phone", ""),
        "room_type": data["room_type"],
        "check_in": data["check_in"],
        "check_out": data["check_out"],
        "nights": nights,
        "guests_count": data.get("guests_count", 1),
        "price_per_night": base_price,
        "price_total": total,
        "currency": room_rate.get("currency", "TRY"),
        "special_requests": data.get("special_requests", ""),
        "source": "GUEST_PORTAL",
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat(),
    }
    await db.reservations.insert_one(reservation)

    await log_audit(tid, "RESERVATION_CREATED", "reservation", reservation["id"], "guest",
                    {"confirmation_code": confirmation_code, "source": "GUEST_PORTAL"})

    return {
        "reservation": serialize_doc(reservation),
        "confirmation_code": confirmation_code,
        "message": "Reservation created successfully"
    }


@router.post("/g/{tenant_slug}/room/{room_code}/express-checkout")
async def express_checkout(tenant_slug: str, room_code: str, data: dict):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    room = await db.rooms.find_one({"tenant_id": tid, "room_code": room_code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    folio = await _build_folio(tid, room_code, room)
    checkout_request = {
        "id": new_id(), "tenant_id": tid,
        "room_code": room_code,
        "guest_name": data.get("guest_name", room.get("current_guest_name", "")),
        "folio_total": folio.get("total", 0),
        "folio_items_count": len(folio.get("items", [])),
        "payment_method": data.get("payment_method", "room_charge"),
        "folio_confirmed": data.get("folio_confirmed", False),
        "feedback": data.get("feedback", ""),
        "rating": data.get("rating", 0),
        "status": "PENDING",
        "created_at": now_utc().isoformat(),
    }
    await db.checkout_requests.insert_one(checkout_request)

    await db.guest_requests.insert_one({
        "id": new_id(), "tenant_id": tid,
        "room_id": str(room.get("_id", room.get("id", ""))),
        "room_code": room_code,
        "category": "checkout",
        "description": f"Express checkout - Folio: {folio.get('total', 0)} {folio.get('currency', 'TRY')}",
        "priority": "high",
        "status": "OPEN",
        "guest_name": checkout_request["guest_name"],
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat(),
    })

    return {
        "checkout_id": checkout_request["id"],
        "folio": folio,
        "status": "PENDING",
        "message": "Express checkout request submitted. Front desk will process shortly."
    }


async def _build_folio(tid, room_code, room):
    check_in_str = room.get("current_guest_check_in", "")
    items = []
    currency = "TRY"
    total = 0

    orders = await db.orders.find({"tenant_id": tid, "room_code": room_code}).to_list(100)
    for o in orders:
        if o.get("created_at", "") >= check_in_str:
            amt = sum(i.get("price", 0) * i.get("quantity", 1) for i in o.get("items", []))
            items.append({"type": "room_service", "description": "Room Service Order", "amount": amt, "date": o.get("created_at", "")})
            total += amt

    minibar = await db.minibar_orders.find({"tenant_id": tid, "room_code": room_code}).to_list(100)
    for m in minibar:
        if m.get("created_at", "") >= check_in_str:
            amt = m.get("total", 0)
            items.append({"type": "minibar", "description": "Minibar", "amount": amt, "date": m.get("created_at", "")})
            total += amt

    spa = await db.spa_bookings.find({"tenant_id": tid, "room_code": room_code}).to_list(50)
    for s in spa:
        if s.get("created_at", "") >= check_in_str:
            amt = s.get("price", 0)
            items.append({"type": "spa", "description": f"Spa - {s.get('service_type', '')}", "amount": amt, "date": s.get("created_at", "")})
            total += amt

    laundry = await db.laundry_requests.find({"tenant_id": tid, "room_code": room_code}).to_list(50)
    for l in laundry:
        if l.get("created_at", "") >= check_in_str:
            amt = l.get("price", 0)
            items.append({"type": "laundry", "description": "Laundry", "amount": amt, "date": l.get("created_at", "")})
            total += amt

    return {"items": items, "total": round(total, 2), "currency": currency}


@router.post("/g/{tenant_slug}/room/{room_code}/digital-checkin")
async def digital_checkin(tenant_slug: str, room_code: str, data: dict):
    tenant = await resolve_tenant(tenant_slug)
    tid = tenant["id"]

    room = await db.rooms.find_one({"tenant_id": tid, "room_code": room_code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Required field validation
    required_missing = []
    for field in ("guest_name", "guest_phone", "id_number"):
        if not (data.get(field) or "").strip():
            required_missing.append(field)
    if required_missing:
        raise HTTPException(status_code=400,
                            detail=f"Missing required fields: {', '.join(required_missing)}")
    if not data.get("terms_accepted"):
        raise HTTPException(status_code=400, detail="Terms must be accepted to complete check-in")
    id_type = data.get("id_type", "passport")
    if id_type not in ("passport", "national_id", "driver_license"):
        raise HTTPException(status_code=400, detail="Invalid id_type")

    checkin_record = {
        "id": new_id(), "tenant_id": tid,
        "room_code": room_code,
        "guest_name": data.get("guest_name", ""),
        "guest_email": data.get("guest_email", ""),
        "guest_phone": data.get("guest_phone", ""),
        "nationality": data.get("nationality", ""),
        "id_type": data.get("id_type", "passport"),
        "id_number": data.get("id_number", ""),
        "arrival_time": data.get("arrival_time", ""),
        "special_requests": data.get("special_requests", ""),
        "id_photo_uploaded": bool(data.get("id_photo_id")),
        "id_photo_id": data.get("id_photo_id", ""),
        "terms_accepted": data.get("terms_accepted", False),
        "status": "SUBMITTED",
        "created_at": now_utc().isoformat(),
    }
    await db.digital_checkins.insert_one(checkin_record)

    await db.guest_notifications.insert_one({
        "id": new_id(), "tenant_id": tid,
        "room_code": room_code,
        "type": "checkin",
        "title_en": "Digital check-in received",
        "title_tr": "Dijital check-in alindi",
        "body_en": "Your pre-arrival check-in has been submitted. We'll have everything ready for you!",
        "body_tr": "Varis oncesi check-in'iniz alindi. Her seyi sizin icin hazirlayacagiz!",
        "read": False,
        "created_at": now_utc().isoformat(),
    })

    await log_audit(tid, "DIGITAL_CHECKIN", "checkin", checkin_record["id"], "guest",
                    {"room_code": room_code, "guest_name": data.get("guest_name", "")})

    return {
        "checkin_id": checkin_record["id"],
        "status": "SUBMITTED",
        "message": "Digital check-in submitted successfully"
    }
