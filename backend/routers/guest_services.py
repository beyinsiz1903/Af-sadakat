"""Guest Services Router - Enhanced guest experience
Hotel info, room service ordering, spa/activity booking, transport,
laundry, wake-up calls, minibar, surveys, announcements, multi-language
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import os

from core.config import db
from core.tenant_guard import (
    resolve_tenant, serialize_doc, new_id, now_utc,
    find_one_scoped, find_many_scoped, count_scoped,
    insert_scoped, update_scoped, delete_scoped, log_audit, get_current_user
)
from fastapi import Depends

router = APIRouter(prefix="/api/v2/guest-services", tags=["guest-services"])

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
    
    return {"spa_bookings": spa, "transport_requests": transport, "wakeup_calls": wakeup, "laundry_requests": laundry}

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
        "body": data.get("body", ""),
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
    update = {}
    if "status" in data:
        update["status"] = data["status"].upper()
    if "notes" in data:
        update["notes"] = data["notes"]
    return await update_scoped("spa_bookings", tenant["id"], booking_id, update)

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
    update = {}
    if "status" in data:
        update["status"] = data["status"].upper()
    if "notes" in data:
        update["notes"] = data["notes"]
    if "driver_name" in data:
        update["driver_name"] = data["driver_name"]
    if "vehicle_info" in data:
        update["vehicle_info"] = data["vehicle_info"]
    return await update_scoped("transport_requests", tenant["id"], req_id, update)

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
    update = {}
    if "status" in data:
        update["status"] = data["status"].upper()
    if "notes" in data:
        update["notes"] = data["notes"]
    return await update_scoped("laundry_requests", tenant["id"], req_id, update)

# Wake-up Calls Admin
@router.get("/tenants/{tenant_slug}/wakeup-calls")
async def list_wakeup_calls(tenant_slug: str, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    return await find_many_scoped("wakeup_calls", tenant["id"], sort=[("wakeup_date", 1), ("wakeup_time", 1)])

@router.patch("/tenants/{tenant_slug}/wakeup-calls/{call_id}")
async def update_wakeup_call(tenant_slug: str, call_id: str, data: dict, user=Depends(get_current_user)):
    tenant = await resolve_tenant(tenant_slug)
    update = {}
    if "status" in data:
        update["status"] = data["status"].upper()
    return await update_scoped("wakeup_calls", tenant["id"], call_id, update)

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
