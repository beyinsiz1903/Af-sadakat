"""Demo & Seed routes — extracted from server.py.
Endpoints: POST /api/seed, POST /api/demo/reset
Mounted under api_router prefix=/api by include_router below.
"""
from fastapi import APIRouter
from datetime import timedelta
import bcrypt

from core.config import db
from core.legacy_helpers import now_utc, new_id

router = APIRouter(prefix="/api", tags=["demo-seed"])


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


@router.post("/seed")
async def seed_data():
    """Create sample data for demo purposes"""
    # Check if already seeded
    existing = await db.tenants.find_one({"slug": "grand-hotel"})
    if existing:
        return {"message": "Already seeded", "tenant_slug": "grand-hotel"}
    
    # Create tenant
    tenant_id = new_id()
    tenant = {
        "id": tenant_id,
        "name": "Grand Hotel Istanbul",
        "slug": "grand-hotel",
        "business_type": "hotel",
        "plan": "pro",
        "hotel_enabled": True,
        "restaurant_enabled": True,
        "agency_enabled": False,
        "clinic_enabled": False,
        "plan_limits": {"max_users": 25, "max_rooms": 100, "max_tables": 50, "monthly_ai_replies": 500},
        "usage_counters": {"users": 1, "rooms": 5, "tables": 3, "ai_replies_this_month": 12},
        "loyalty_rules": {"enabled": True, "points_per_request": 10, "points_per_order": 5, "points_per_currency_unit": 1},
        "created_at": now_utc().isoformat(),
        "updated_at": now_utc().isoformat()
    }
    await db.tenants.insert_one(tenant)
    
    # Create owner user
    owner_id = new_id()
    await db.users.insert_one({
        "id": owner_id,
        "tenant_id": tenant_id,
        "email": "admin@grandhotel.com",
        "password_hash": hash_password("admin123"),
        "name": "Admin User",
        "role": "owner",
        "department_code": None,
        "active": True,
        "created_at": now_utc().isoformat()
    })
    
    # Departments
    departments = [
        {"id": new_id(), "tenant_id": tenant_id, "name": "Housekeeping", "code": "HK", "description": "Room cleaning and amenities", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Technical", "code": "TECH", "description": "Maintenance and repairs", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Food & Beverage", "code": "FB", "description": "Room service and minibar", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Front Desk", "code": "FRONTDESK", "description": "Reception and concierge", "created_at": now_utc().isoformat()},
    ]
    await db.departments.insert_many(departments)
    
    # Service categories
    service_cats = [
        {"id": new_id(), "tenant_id": tenant_id, "name": "Extra Towels", "department_code": "HK", "icon": "towel", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Room Cleaning", "department_code": "HK", "icon": "sparkles", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "AC/Heating", "department_code": "TECH", "icon": "thermometer", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Plumbing", "department_code": "TECH", "icon": "wrench", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Room Service", "department_code": "FB", "icon": "utensils", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Wake-up Call", "department_code": "FRONTDESK", "icon": "bell", "created_at": now_utc().isoformat()},
    ]
    await db.service_categories.insert_many(service_cats)
    
    # Rooms (using simple codes for demo - production uses secure random codes)
    room_guests = {
        "101": {"name": "John Smith", "check_in": (now_utc() - timedelta(days=2)).strftime("%Y-%m-%d"), "check_out": (now_utc() + timedelta(days=1)).strftime("%Y-%m-%d")},
        "102": {"name": "Maria Garcia", "check_in": (now_utc() - timedelta(days=1)).strftime("%Y-%m-%d"), "check_out": (now_utc() + timedelta(days=3)).strftime("%Y-%m-%d")},
        "201": {"name": "Ahmed Hassan", "check_in": (now_utc() - timedelta(days=3)).strftime("%Y-%m-%d"), "check_out": (now_utc() + timedelta(days=2)).strftime("%Y-%m-%d")},
        "202": {"name": "Elif Yilmaz", "check_in": now_utc().strftime("%Y-%m-%d"), "check_out": (now_utc() + timedelta(days=4)).strftime("%Y-%m-%d")},
    }
    rooms = []
    for floor in range(1, 4):
        for room_num in range(1, 3):
            rn = f"{floor}0{room_num}"
            guest = room_guests.get(rn)
            room_data = {
                "id": new_id(), "tenant_id": tenant_id,
                "room_number": rn, "room_code": f"R{rn}",
                "room_type": "deluxe" if floor == 3 else "standard",
                "floor": str(floor),
                "is_active": True,
                "qr_version": 1,
                "qr_link": f"/g/grand-hotel/room/R{rn}",
                "status": "occupied" if guest else "available",
                "current_guest_name": guest["name"] if guest else "",
                "current_guest_check_in": guest["check_in"] if guest else "",
                "current_guest_check_out": guest["check_out"] if guest else "",
                "created_at": now_utc().isoformat()
            }
            rooms.append(room_data)
    await db.rooms.insert_many(rooms)
    
    # Tables (using simple codes for demo)
    tables = []
    for t in range(1, 4):
        tables.append({
            "id": new_id(), "tenant_id": tenant_id,
            "table_number": str(t), "table_code": f"T{t}",
            "capacity": 4, "section": "terrace" if t <= 2 else "indoor",
            "is_active": True,
            "qr_version": 1,
            "qr_link": f"/g/grand-hotel/table/T{t}",
            "created_at": now_utc().isoformat()
        })
    await db.tables.insert_many(tables)
    
    # Menu categories
    cat_main_id = new_id()
    cat_app_id = new_id()
    cat_bev_id = new_id()
    cat_dessert_id = new_id()
    menu_cats = [
        {"id": cat_app_id, "tenant_id": tenant_id, "name": "Appetizers", "sort_order": 0, "created_at": now_utc().isoformat()},
        {"id": cat_main_id, "tenant_id": tenant_id, "name": "Main Course", "sort_order": 1, "created_at": now_utc().isoformat()},
        {"id": cat_dessert_id, "tenant_id": tenant_id, "name": "Desserts", "sort_order": 2, "created_at": now_utc().isoformat()},
        {"id": cat_bev_id, "tenant_id": tenant_id, "name": "Beverages", "sort_order": 3, "created_at": now_utc().isoformat()},
    ]
    await db.menu_categories.insert_many(menu_cats)
    
    # Menu items
    menu_items = [
        {"id": new_id(), "tenant_id": tenant_id, "name": "Hummus", "description": "Classic chickpea dip with olive oil", "price": 85.0, "category_id": cat_app_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Mercimek Soup", "description": "Traditional red lentil soup", "price": 65.0, "category_id": cat_app_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Adana Kebab", "description": "Spicy minced meat kebab on skewers", "price": 250.0, "category_id": cat_main_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Iskender", "description": "Doner on bread with tomato sauce and yogurt", "price": 280.0, "category_id": cat_main_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Grilled Sea Bass", "description": "Fresh daily catch, grilled with herbs", "price": 350.0, "category_id": cat_main_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Kunefe", "description": "Crispy kadayif with melted cheese and syrup", "price": 120.0, "category_id": cat_dessert_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Baklava", "description": "Pistachio baklava, 4 pieces", "price": 95.0, "category_id": cat_dessert_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Turkish Tea", "description": "Classic cay", "price": 25.0, "category_id": cat_bev_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Turkish Coffee", "description": "Traditional Turkish coffee", "price": 45.0, "category_id": cat_bev_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Ayran", "description": "Traditional yogurt drink", "price": 35.0, "category_id": cat_bev_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Fresh Orange Juice", "description": "Freshly squeezed", "price": 55.0, "category_id": cat_bev_id, "available": True, "image_url": "", "created_at": now_utc().isoformat()},
    ]
    await db.menu_items.insert_many(menu_items)
    
    # Sample guest requests
    sample_requests = [
        {"id": new_id(), "tenant_id": tenant_id, "room_id": rooms[0]["id"], "room_code": rooms[0]["room_code"], "room_number": rooms[0]["room_number"], "category": "housekeeping", "department_code": "HK", "description": "Need extra towels and pillows", "priority": "normal", "status": "OPEN", "guest_name": "John Smith", "guest_phone": "+905551234567", "guest_email": "", "assigned_to": None, "notes": "", "first_response_at": None, "resolved_at": None, "rating": None, "rating_comment": None, "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "room_id": rooms[1]["id"], "room_code": rooms[1]["room_code"], "room_number": rooms[1]["room_number"], "category": "maintenance", "department_code": "TECH", "description": "Air conditioning not working properly", "priority": "high", "status": "IN_PROGRESS", "guest_name": "Maria Garcia", "guest_phone": "+905559876543", "guest_email": "maria@email.com", "assigned_to": "Maintenance Team", "notes": "Technician dispatched", "first_response_at": now_utc().isoformat(), "resolved_at": None, "rating": None, "rating_comment": None, "created_at": (now_utc() - timedelta(hours=2)).isoformat(), "updated_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "room_id": rooms[2]["id"], "room_code": rooms[2]["room_code"], "room_number": rooms[2]["room_number"], "category": "room_service", "department_code": "FB", "description": "Breakfast order: 2x eggs, toast, coffee", "priority": "normal", "status": "DONE", "guest_name": "Ahmed Hassan", "guest_phone": "+905553456789", "guest_email": "", "assigned_to": "Room Service", "notes": "Delivered", "first_response_at": (now_utc() - timedelta(hours=1)).isoformat(), "resolved_at": now_utc().isoformat(), "rating": 5, "rating_comment": "Excellent service!", "created_at": (now_utc() - timedelta(hours=3)).isoformat(), "updated_at": now_utc().isoformat()},
    ]
    await db.guest_requests.insert_many(sample_requests)
    
    # Sample contacts
    contacts = [
        {"id": new_id(), "tenant_id": tenant_id, "name": "John Smith", "phone": "+905551234567", "email": "john@email.com", "tags": ["vip", "repeat"], "notes": "Prefers high floor", "consent_marketing": True, "consent_data": True, "loyalty_account_id": None, "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Maria Garcia", "phone": "+905559876543", "email": "maria@email.com", "tags": ["new"], "notes": "", "consent_marketing": False, "consent_data": True, "loyalty_account_id": None, "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Ahmed Hassan", "phone": "+905553456789", "email": "ahmed@email.com", "tags": ["loyalty"], "notes": "Allergic to nuts", "consent_marketing": True, "consent_data": True, "loyalty_account_id": None, "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat()},
    ]
    await db.contacts.insert_many(contacts)
    
    # Sample orders
    sample_orders = [
        {"id": new_id(), "tenant_id": tenant_id, "table_id": tables[0]["id"], "table_code": "T1", "table_number": "1", "items": [{"menu_item_id": menu_items[2]["id"], "menu_item_name": "Adana Kebab", "quantity": 2, "price": 250.0, "notes": ""}, {"menu_item_id": menu_items[7]["id"], "menu_item_name": "Turkish Tea", "quantity": 2, "price": 25.0, "notes": ""}], "total": 550.0, "status": "PREPARING", "order_type": "dine_in", "guest_name": "Table 1 Guest", "guest_phone": "", "guest_email": "", "notes": "Extra spicy", "created_at": (now_utc() - timedelta(minutes=15)).isoformat(), "updated_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "table_id": tables[1]["id"], "table_code": "T2", "table_number": "2", "items": [{"menu_item_id": menu_items[3]["id"], "menu_item_name": "Iskender", "quantity": 1, "price": 280.0, "notes": ""}, {"menu_item_id": menu_items[9]["id"], "menu_item_name": "Ayran", "quantity": 1, "price": 35.0, "notes": ""}], "total": 315.0, "status": "RECEIVED", "order_type": "dine_in", "guest_name": "Table 2 Guest", "guest_phone": "", "guest_email": "", "notes": "", "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat()},
    ]
    await db.orders.insert_many(sample_orders)
    
    # Sprint 3: Seed conversations + messages
    conv1_id = new_id()
    conv2_id = new_id()
    conv3_id = new_id()
    await db.conversations.insert_many([
        {"id": conv1_id, "tenant_id": tenant_id, "channel_type": "WEBCHAT", "contact_id": contacts[0]["id"],
         "status": "OPEN", "assigned_user_id": None, "guest_name": "John Smith",
         "last_message_at": now_utc().isoformat(), "needs_attention": False, "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat()},
        {"id": conv2_id, "tenant_id": tenant_id, "channel_type": "WHATSAPP", "contact_id": contacts[1]["id"],
         "status": "OPEN", "assigned_user_id": None, "guest_name": "Maria Garcia",
         "last_message_at": (now_utc() - timedelta(hours=1)).isoformat(), "needs_attention": True, "created_at": (now_utc() - timedelta(hours=2)).isoformat(), "updated_at": now_utc().isoformat()},
        {"id": conv3_id, "tenant_id": tenant_id, "channel_type": "INSTAGRAM", "contact_id": None,
         "status": "OPEN", "assigned_user_id": None, "guest_name": "@travel_adventures",
         "last_message_at": (now_utc() - timedelta(hours=3)).isoformat(), "created_at": (now_utc() - timedelta(hours=3)).isoformat(), "updated_at": now_utc().isoformat()},
    ])
    await db.messages.insert_many([
        {"id": new_id(), "tenant_id": tenant_id, "conversation_id": conv1_id, "direction": "IN",
         "body": "Hello, I'd like to request late checkout for tomorrow.", "created_at": (now_utc() - timedelta(minutes=30)).isoformat(),
         "meta": {"sender_type": "guest", "sender_name": "John Smith"}},
        {"id": new_id(), "tenant_id": tenant_id, "conversation_id": conv1_id, "direction": "OUT",
         "body": "Of course! We can extend your checkout to 2 PM. Would that work?", "created_at": (now_utc() - timedelta(minutes=25)).isoformat(),
         "last_updated_by": "Admin User", "meta": {"sender_type": "agent"}},
        {"id": new_id(), "tenant_id": tenant_id, "conversation_id": conv1_id, "direction": "IN",
         "body": "Perfect, thank you so much!", "created_at": now_utc().isoformat(),
         "meta": {"sender_type": "guest", "sender_name": "John Smith"}},
        {"id": new_id(), "tenant_id": tenant_id, "conversation_id": conv2_id, "direction": "IN",
         "body": "The AC in my room is not working. This is urgent!", "created_at": (now_utc() - timedelta(hours=1)).isoformat(),
         "meta": {"sender_type": "guest", "channel": "WHATSAPP", "is_stub": True}},
        {"id": new_id(), "tenant_id": tenant_id, "conversation_id": conv3_id, "direction": "IN",
         "body": "Love your hotel photos! Do you have availability next month?", "created_at": (now_utc() - timedelta(hours=3)).isoformat(),
         "meta": {"sender_type": "guest", "channel": "INSTAGRAM", "is_stub": True}},
    ])

    # Sprint 3: Seed connector credentials (enabled stubs)
    for ct in ["WEBCHAT", "WHATSAPP", "INSTAGRAM", "GOOGLE_REVIEWS", "TRIPADVISOR"]:
        await db.connector_credentials.insert_one({
            "id": new_id(), "tenant_id": tenant_id, "connector_type": ct,
            "enabled": True, "encrypted_json": "", "last_sync_at": now_utc().isoformat() if ct != "WEBCHAT" else None,
            "status": "active" if ct == "WEBCHAT" else "synced",
            "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat(),
        })

    # Sprint 3: Seed usage counter
    month_key = now_utc().strftime("%Y-%m")
    await db.usage_counters.insert_one({
        "id": new_id(), "tenant_id": tenant_id, "month_key": month_key,
        "ai_replies_used": 13, "ai_replies_limit": 500, "updated_at": now_utc().isoformat(),
    })

    # Sprint 4: Loyalty rules
    await db.loyalty_rules.insert_one({
        "id": new_id(), "tenant_id": tenant_id, "enabled": True,
        "earn": {"per_request_closed_points": 10, "per_order_completed_points": 5, "per_reservation_confirmed_points": 20},
        "tiers": [
            {"name": "Silver", "min_points": 0, "perks": ["5% off room service"]},
            {"name": "Gold", "min_points": 500, "perks": ["10% off all services", "Late checkout"]},
            {"name": "Platinum", "min_points": 1500, "perks": ["20% off all services", "Late checkout", "Room upgrade", "Welcome amenity"]},
        ],
        "updated_at": now_utc().isoformat(),
    })

    # Sprint 4: Loyalty accounts for contacts
    john_acct_id = new_id()
    ahmed_acct_id = new_id()
    await db.loyalty_accounts.insert_many([
        {"id": john_acct_id, "tenant_id": tenant_id, "contact_id": contacts[0]["id"],
         "points_balance": 120, "tier_name": "Silver", "enrolled_at": now_utc().isoformat(), "updated_at": now_utc().isoformat()},
        {"id": ahmed_acct_id, "tenant_id": tenant_id, "contact_id": contacts[2]["id"],
         "points_balance": 520, "tier_name": "Gold", "enrolled_at": (now_utc() - timedelta(days=30)).isoformat(), "updated_at": now_utc().isoformat()},
    ])
    await db.contacts.update_one({"id": contacts[0]["id"]}, {"$set": {"loyalty_account_id": john_acct_id}})
    await db.contacts.update_one({"id": contacts[2]["id"]}, {"$set": {"loyalty_account_id": ahmed_acct_id}})

    # Sprint 4: Loyalty ledger
    await db.loyalty_ledger.insert_many([
        {"id": new_id(), "tenant_id": tenant_id, "contact_id": contacts[0]["id"], "direction": "EARN",
         "points": 10, "reason": "Request completed", "ref_type": "request_closed", "created_at": (now_utc() - timedelta(days=7)).isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "contact_id": contacts[0]["id"], "direction": "EARN",
         "points": 5, "reason": "Order completed", "ref_type": "order_completed", "created_at": (now_utc() - timedelta(days=5)).isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "contact_id": contacts[0]["id"], "direction": "EARN",
         "points": 105, "reason": "Welcome bonus", "ref_type": "enrollment", "created_at": (now_utc() - timedelta(days=10)).isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "contact_id": contacts[2]["id"], "direction": "EARN",
         "points": 300, "reason": "Stay completed", "ref_type": "request_closed", "created_at": (now_utc() - timedelta(days=20)).isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "contact_id": contacts[2]["id"], "direction": "EARN",
         "points": 220, "reason": "Orders + referral bonus", "ref_type": "order_completed", "created_at": (now_utc() - timedelta(days=10)).isoformat()},
    ])

    # Sprint 4: Contact events (rich timeline)
    contact_events = [
        {"id": new_id(), "tenant_id": tenant_id, "contact_id": contacts[0]["id"], "type": "LOYALTY_ENROLLED",
         "title": "Enrolled in loyalty program", "body": "", "ref_type": "", "ref_id": "", "created_at": (now_utc() - timedelta(days=10)).isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "contact_id": contacts[0]["id"], "type": "LOYALTY_EARNED",
         "title": "+105 pts: Welcome bonus", "body": "", "ref_type": "enrollment", "ref_id": "", "created_at": (now_utc() - timedelta(days=10)).isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "contact_id": contacts[0]["id"], "type": "REQUEST_CREATED",
         "title": "Room request submitted", "body": "Extra towels and pillows", "ref_type": "request", "ref_id": sample_requests[0]["id"], "created_at": (now_utc() - timedelta(days=7)).isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "contact_id": contacts[0]["id"], "type": "LOYALTY_EARNED",
         "title": "+10 pts: Request completed", "body": "", "ref_type": "request_closed", "ref_id": "", "created_at": (now_utc() - timedelta(days=7)).isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "contact_id": contacts[0]["id"], "type": "MESSAGE_IN",
         "title": "WebChat message", "body": "Hello, I'd like to request late checkout", "ref_type": "conversation", "ref_id": conv1_id, "created_at": (now_utc() - timedelta(minutes=30)).isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "contact_id": contacts[1]["id"], "type": "MESSAGE_IN",
         "title": "WhatsApp message", "body": "AC not working", "ref_type": "conversation", "ref_id": conv2_id, "created_at": (now_utc() - timedelta(hours=1)).isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "contact_id": contacts[2]["id"], "type": "LOYALTY_ENROLLED",
         "title": "Enrolled in loyalty program", "body": "", "ref_type": "", "ref_id": "", "created_at": (now_utc() - timedelta(days=30)).isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "contact_id": contacts[2]["id"], "type": "LOYALTY_EARNED",
         "title": "+300 pts: Stay completed", "body": "", "ref_type": "request_closed", "ref_id": "", "created_at": (now_utc() - timedelta(days=20)).isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "contact_id": contacts[2]["id"], "type": "REQUEST_CREATED",
         "title": "Room service request", "body": "Breakfast order", "ref_type": "request", "ref_id": sample_requests[2]["id"], "created_at": (now_utc() - timedelta(hours=3)).isoformat()},
    ]
    await db.contact_events.insert_many(contact_events)

    # ============ SPRINT 5: PROPERTIES, OFFERS, RESERVATIONS ============
    # Properties
    prop_main_id = new_id()
    prop_annex_id = new_id()
    properties = [
        {"id": prop_main_id, "tenant_id": tenant_id, "name": "Grand Hotel Istanbul - Main", "slug": "main",
         "timezone": "Europe/Istanbul", "address": "Beyoglu, Istanbul", "phone": "+90 212 555 0001",
         "email": "main@grandhotel.com", "is_active": True, "last_updated_by": "Admin User",
         "created_at": (now_utc() - timedelta(days=90)).isoformat(), "updated_at": now_utc().isoformat()},
        {"id": prop_annex_id, "tenant_id": tenant_id, "name": "Grand Hotel Istanbul - Annex", "slug": "annex",
         "timezone": "Europe/Istanbul", "address": "Sisli, Istanbul", "phone": "+90 212 555 0002",
         "email": "annex@grandhotel.com", "is_active": True, "last_updated_by": "Admin User",
         "created_at": (now_utc() - timedelta(days=60)).isoformat(), "updated_at": now_utc().isoformat()},
    ]
    await db.properties.insert_many(properties)

    # Update existing rooms with property_id (first 4 to main, last 2 to annex)
    for i, room in enumerate(rooms):
        pid = prop_main_id if i < 4 else prop_annex_id
        await db.rooms.update_one({"id": room["id"]}, {"$set": {"property_id": pid}})

    # Update existing tables with property_id
    for i, table in enumerate(tables):
        pid = prop_main_id if i < 2 else prop_annex_id
        await db.tables.update_one({"id": table["id"]}, {"$set": {"property_id": pid}})

    # Offers (4 total: 2 SENT, 1 PAID, 1 EXPIRED)
    offer_sent_1_id = new_id()
    offer_sent_2_id = new_id()
    offer_paid_id = new_id()
    offer_expired_id = new_id()
    pl_sent_1_id = new_id()
    pl_sent_2_id = new_id()
    pl_paid_id = new_id()

    offers_seed = [
        {"id": offer_sent_1_id, "tenant_id": tenant_id, "property_id": prop_main_id,
         "contact_id": contacts[0]["id"], "source": "MANUAL",
         "check_in": (now_utc() + timedelta(days=14)).strftime("%Y-%m-%d"),
         "check_out": (now_utc() + timedelta(days=17)).strftime("%Y-%m-%d"),
         "guests_count": 2, "room_type": "deluxe", "price_total": 4500.0, "currency": "TRY",
         "status": "SENT", "expires_at": (now_utc() + timedelta(hours=24)).isoformat(),
         "notes": "Includes breakfast and spa access",
         "guest_name": "John Smith", "guest_email": "", "guest_phone": "+905551234567",
         "payment_link_id": pl_sent_1_id, "last_updated_by": "Admin User", "meta": {},
         "created_at": (now_utc() - timedelta(hours=6)).isoformat(), "updated_at": now_utc().isoformat()},
        {"id": offer_sent_2_id, "tenant_id": tenant_id, "property_id": prop_main_id,
         "contact_id": contacts[1]["id"], "source": "INBOX",
         "check_in": (now_utc() + timedelta(days=7)).strftime("%Y-%m-%d"),
         "check_out": (now_utc() + timedelta(days=10)).strftime("%Y-%m-%d"),
         "guests_count": 1, "room_type": "standard", "price_total": 2700.0, "currency": "TRY",
         "status": "SENT", "expires_at": (now_utc() + timedelta(hours=36)).isoformat(),
         "notes": "Room with city view",
         "guest_name": "Maria Garcia", "guest_email": "maria@email.com", "guest_phone": "+905559876543",
         "payment_link_id": pl_sent_2_id, "last_updated_by": "Admin User", "meta": {},
         "created_at": (now_utc() - timedelta(hours=12)).isoformat(), "updated_at": now_utc().isoformat()},
        {"id": offer_paid_id, "tenant_id": tenant_id, "property_id": prop_main_id,
         "contact_id": contacts[2]["id"], "source": "MANUAL",
         "check_in": (now_utc() + timedelta(days=3)).strftime("%Y-%m-%d"),
         "check_out": (now_utc() + timedelta(days=5)).strftime("%Y-%m-%d"),
         "guests_count": 2, "room_type": "suite", "price_total": 8000.0, "currency": "TRY",
         "status": "PAID", "expires_at": (now_utc() - timedelta(hours=12)).isoformat(),
         "notes": "VIP guest - suite with Bosphorus view",
         "guest_name": "Ahmed Hassan", "guest_email": "", "guest_phone": "+905553456789",
         "payment_link_id": pl_paid_id, "last_updated_by": "Admin User", "meta": {},
         "created_at": (now_utc() - timedelta(days=2)).isoformat(), "updated_at": (now_utc() - timedelta(hours=12)).isoformat()},
        {"id": offer_expired_id, "tenant_id": tenant_id, "property_id": prop_annex_id,
         "contact_id": "", "source": "MANUAL",
         "check_in": (now_utc() + timedelta(days=1)).strftime("%Y-%m-%d"),
         "check_out": (now_utc() + timedelta(days=3)).strftime("%Y-%m-%d"),
         "guests_count": 1, "room_type": "standard", "price_total": 1800.0, "currency": "TRY",
         "status": "EXPIRED", "expires_at": (now_utc() - timedelta(hours=48)).isoformat(),
         "notes": "Walk-in inquiry",
         "guest_name": "Walk-in Guest", "guest_email": "", "guest_phone": "",
         "payment_link_id": None, "last_updated_by": "Admin User", "meta": {},
         "created_at": (now_utc() - timedelta(days=3)).isoformat(), "updated_at": (now_utc() - timedelta(hours=48)).isoformat()},
    ]
    await db.offers.insert_many(offers_seed)

    # Payment links
    public_url = os.environ.get("PUBLIC_BASE_URL", "https://kritik-billing.preview.emergentagent.com")
    payment_links_seed = [
        {"id": pl_sent_1_id, "tenant_id": tenant_id, "offer_id": offer_sent_1_id,
         "provider": "STRIPE_STUB", "url": f"{public_url}/pay/{pl_sent_1_id}",
         "status": "PENDING", "idempotency_key": f"offer_{offer_sent_1_id}_abc123",
         "amount": 4500.0, "currency": "TRY",
         "created_at": (now_utc() - timedelta(hours=6)).isoformat(), "updated_at": now_utc().isoformat()},
        {"id": pl_sent_2_id, "tenant_id": tenant_id, "offer_id": offer_sent_2_id,
         "provider": "STRIPE_STUB", "url": f"{public_url}/pay/{pl_sent_2_id}",
         "status": "PENDING", "idempotency_key": f"offer_{offer_sent_2_id}_def456",
         "amount": 2700.0, "currency": "TRY",
         "created_at": (now_utc() - timedelta(hours=12)).isoformat(), "updated_at": now_utc().isoformat()},
        {"id": pl_paid_id, "tenant_id": tenant_id, "offer_id": offer_paid_id,
         "provider": "STRIPE_STUB", "url": f"{public_url}/pay/{pl_paid_id}",
         "status": "SUCCEEDED", "idempotency_key": f"offer_{offer_paid_id}_ghi789",
         "amount": 8000.0, "currency": "TRY",
         "created_at": (now_utc() - timedelta(days=1)).isoformat(), "updated_at": (now_utc() - timedelta(hours=12)).isoformat()},
    ]
    await db.payment_links.insert_many(payment_links_seed)

    # Payments
    await db.payments.insert_one({
        "id": new_id(), "tenant_id": tenant_id, "offer_id": offer_paid_id,
        "payment_link_id": pl_paid_id, "provider": "STRIPE_STUB",
        "amount": 8000.0, "currency": "TRY", "status": "SUCCEEDED",
        "provider_payment_id": "pi_stub_seed12345678",
        "created_at": (now_utc() - timedelta(hours=12)).isoformat(),
        "updated_at": (now_utc() - timedelta(hours=12)).isoformat(),
    })

    # Reservations (2 confirmed)
    res1_id = new_id()
    res2_id = new_id()
    reservations_seed = [
        {"id": res1_id, "tenant_id": tenant_id, "property_id": prop_main_id,
         "contact_id": contacts[2]["id"], "offer_id": offer_paid_id,
         "status": "CONFIRMED", "confirmation_code": "RES-A1B2C3",
         "guest_name": "Ahmed Hassan", "guest_email": "", "guest_phone": "+905553456789",
         "room_type": "suite",
         "check_in": (now_utc() + timedelta(days=3)).strftime("%Y-%m-%d"),
         "check_out": (now_utc() + timedelta(days=5)).strftime("%Y-%m-%d"),
         "guests_count": 2, "price_total": 8000.0, "currency": "TRY",
         "last_updated_by": "system",
         "created_at": (now_utc() - timedelta(hours=12)).isoformat(),
         "updated_at": (now_utc() - timedelta(hours=12)).isoformat()},
        {"id": res2_id, "tenant_id": tenant_id, "property_id": prop_main_id,
         "contact_id": contacts[0]["id"], "offer_id": "",
         "status": "CONFIRMED", "confirmation_code": "RES-D4E5F6",
         "guest_name": "John Smith", "guest_email": "", "guest_phone": "+905551234567",
         "room_type": "deluxe",
         "check_in": (now_utc() - timedelta(days=2)).strftime("%Y-%m-%d"),
         "check_out": (now_utc() + timedelta(days=1)).strftime("%Y-%m-%d"),
         "guests_count": 2, "price_total": 6000.0, "currency": "TRY",
         "last_updated_by": "system",
         "created_at": (now_utc() - timedelta(days=5)).isoformat(),
         "updated_at": (now_utc() - timedelta(days=5)).isoformat()},
    ]
    await db.reservations.insert_many(reservations_seed)

    # Additional contact events for offers/reservations
    offer_res_events = [
        {"id": new_id(), "tenant_id": tenant_id, "contact_id": contacts[2]["id"], "type": "OFFER_CREATED",
         "title": "Offer created: suite", "body": "VIP guest - suite with Bosphorus view",
         "ref_type": "offer", "ref_id": offer_paid_id, "created_at": (now_utc() - timedelta(days=2)).isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "contact_id": contacts[2]["id"], "type": "OFFER_SENT",
         "title": "Offer sent", "body": "",
         "ref_type": "offer", "ref_id": offer_paid_id, "created_at": (now_utc() - timedelta(days=1, hours=12)).isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "contact_id": contacts[2]["id"], "type": "RESERVATION_CONFIRMED",
         "title": "Reservation RES-A1B2C3 confirmed", "body": "Payment received",
         "ref_type": "reservation", "ref_id": res1_id, "created_at": (now_utc() - timedelta(hours=12)).isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "contact_id": contacts[0]["id"], "type": "OFFER_CREATED",
         "title": "Offer created: deluxe", "body": "Includes breakfast and spa access",
         "ref_type": "offer", "ref_id": offer_sent_1_id, "created_at": (now_utc() - timedelta(hours=6)).isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "contact_id": contacts[0]["id"], "type": "OFFER_SENT",
         "title": "Offer sent", "body": "",
         "ref_type": "offer", "ref_id": offer_sent_1_id, "created_at": (now_utc() - timedelta(hours=5)).isoformat()},
    ]
    await db.contact_events.insert_many(offer_res_events)

    # ========== Sprint 7: AI Sales Engine Seed Data ==========
    
    # Room Rates for Main property
    room_rates_seed = [
        {"id": new_id(), "tenant_id": tenant_id, "property_id": prop_main_id,
         "room_type_code": "standard", "room_type_name": "Standard Room",
         "description": "Comfortable room with city view, 25m2",
         "base_price_per_night": 1200.0, "currency": "TRY",
         "weekend_multiplier": 1.2, "season_rules": [
             {"start": "2025-06-01", "end": "2025-09-30", "multiplier": 1.3},
             {"start": "2025-12-20", "end": "2026-01-05", "multiplier": 1.5},
         ],
         "min_stay_nights": 1, "max_guests": 2,
         "refundable": True, "breakfast_included": False, "is_active": True,
         "last_updated_by": "Admin User",
         "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "property_id": prop_main_id,
         "room_type_code": "deluxe", "room_type_name": "Deluxe Room",
         "description": "Spacious room with Bosphorus view, 35m2, minibar included",
         "base_price_per_night": 2200.0, "currency": "TRY",
         "weekend_multiplier": 1.15, "season_rules": [
             {"start": "2025-06-01", "end": "2025-09-30", "multiplier": 1.25},
             {"start": "2025-12-20", "end": "2026-01-05", "multiplier": 1.4},
         ],
         "min_stay_nights": 1, "max_guests": 3,
         "refundable": True, "breakfast_included": True, "is_active": True,
         "last_updated_by": "Admin User",
         "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "property_id": prop_main_id,
         "room_type_code": "suite", "room_type_name": "Suite",
         "description": "Luxury suite with panoramic Bosphorus view, 55m2, living area, jacuzzi",
         "base_price_per_night": 4500.0, "currency": "TRY",
         "weekend_multiplier": 1.1, "season_rules": [
             {"start": "2025-06-01", "end": "2025-09-30", "multiplier": 1.2},
             {"start": "2025-12-20", "end": "2026-01-05", "multiplier": 1.35},
         ],
         "min_stay_nights": 2, "max_guests": 4,
         "refundable": True, "breakfast_included": True, "is_active": True,
         "last_updated_by": "Admin User",
         "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat()},
    ]
    await db.room_rates.insert_many(room_rates_seed)

    # Room Rates for Annex property
    annex_rates = [
        {"id": new_id(), "tenant_id": tenant_id, "property_id": prop_annex_id,
         "room_type_code": "standard", "room_type_name": "Standard Room",
         "description": "Cozy room in Annex building, 22m2",
         "base_price_per_night": 900.0, "currency": "TRY",
         "weekend_multiplier": 1.15, "season_rules": [],
         "min_stay_nights": 1, "max_guests": 2,
         "refundable": True, "breakfast_included": False, "is_active": True,
         "last_updated_by": "Admin User",
         "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "property_id": prop_annex_id,
         "room_type_code": "deluxe", "room_type_name": "Deluxe Room",
         "description": "Premium room in Annex building, 30m2, balcony",
         "base_price_per_night": 1600.0, "currency": "TRY",
         "weekend_multiplier": 1.1, "season_rules": [],
         "min_stay_nights": 1, "max_guests": 3,
         "refundable": True, "breakfast_included": True, "is_active": True,
         "last_updated_by": "Admin User",
         "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat()},
    ]
    await db.room_rates.insert_many(annex_rates)

    # Discount Rules
    discount_rules_seed = [
        {"id": new_id(), "tenant_id": tenant_id, "property_id": prop_main_id,
         "enabled": True, "max_discount_percent": 10,
         "min_nights_for_discount": 3,
         "allowed_channels": ["webchat", "whatsapp", "instagram"],
         "blackouts": [{"start": "2025-12-20", "end": "2026-01-05"}],
         "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat(),
         "last_updated_by": "Admin User"},
        {"id": new_id(), "tenant_id": tenant_id, "property_id": prop_annex_id,
         "enabled": True, "max_discount_percent": 15,
         "min_nights_for_discount": 2,
         "allowed_channels": ["webchat"],
         "blackouts": [],
         "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat(),
         "last_updated_by": "Admin User"},
    ]
    await db.discount_rules.insert_many(discount_rules_seed)

    # Business Policies
    policies_seed = [
        {"id": new_id(), "tenant_id": tenant_id, "property_id": prop_main_id,
         "check_in_time": "14:00", "check_out_time": "12:00",
         "cancellation_policy_text": "Free cancellation up to 48 hours before check-in. Late cancellation: 1 night charge.",
         "pets_allowed": False, "smoking_policy": "Non-smoking property",
         "parking_info": "Free valet parking available",
         "location_info": "Located in Beyoglu, 5 min walk to Istiklal Street",
         "contact_phone": "+90 212 555 0001",
         "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat(),
         "last_updated_by": "Admin User"},
        {"id": new_id(), "tenant_id": tenant_id, "property_id": prop_annex_id,
         "check_in_time": "15:00", "check_out_time": "11:00",
         "cancellation_policy_text": "Free cancellation up to 24 hours before check-in.",
         "pets_allowed": True, "smoking_policy": "Smoking areas available",
         "parking_info": "Street parking only",
         "location_info": "Located in Sisli, near metro station",
         "contact_phone": "+90 212 555 0002",
         "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat(),
         "last_updated_by": "Admin User"},
    ]
    await db.business_policies.insert_many(policies_seed)

    # AI Sales Settings (enabled for Main, disabled for Annex by default)
    ai_settings_seed = [
        {"id": new_id(), "tenant_id": tenant_id, "property_id": prop_main_id,
         "enabled": True, "allowed_languages": ["TR", "EN"],
         "max_messages_without_human": 20,
         "escalation_keywords": ["complaint", "manager", "lawyer", "sikayet", "mudur", "avukat"],
         "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat(),
         "last_updated_by": "Admin User"},
        {"id": new_id(), "tenant_id": tenant_id, "property_id": prop_annex_id,
         "enabled": False, "allowed_languages": ["TR", "EN"],
         "max_messages_without_human": 20,
         "escalation_keywords": ["complaint", "manager", "lawyer", "sikayet", "mudur"],
         "created_at": now_utc().isoformat(), "updated_at": now_utc().isoformat(),
         "last_updated_by": "Admin User"},
    ]
    await db.ai_sales_settings.insert_many(ai_settings_seed)

    # ========== Meta Integration Seed Data ==========
    # Meta connector credential (DISCONNECTED by default - needs real app credentials)
    import secrets as _sec
    meta_verify_token = _sec.token_urlsafe(24)
    await db.connector_credentials.update_one(
        {"tenant_id": tenant_id, "connector_type": "META"},
        {"$set": {
            "tenant_id": tenant_id,
            "connector_type": "META",
            "meta_app_id": "",
            "meta_app_secret": "",
            "meta_verify_token": meta_verify_token,
            "oauth_redirect_uri": f"https://kritik-billing.preview.emergentagent.com/api/v2/integrations/meta/oauth/callback",
            "access_token": "",
            "token_expires_at": None,
            "scopes": [],
            "status": "DISCONNECTED",
            "last_error": None,
            "updated_at": now_utc().isoformat(),
        }, "$setOnInsert": {"id": new_id(), "created_at": now_utc().isoformat()}},
        upsert=True
    )

    # ========== Sprint 9: Enhanced Feature Seed Data ==========
    
    # Hotel Info
    await db.hotel_info.update_one(
        {"tenant_id": tenant_id},
        {"$set": {
            "tenant_id": tenant_id,
            "id": new_id(),
            "hotel_name": "Grand Hotel Istanbul",
            "description": "Luxury 5-star hotel in the heart of Istanbul with stunning Bosphorus views",
            "address": "Ciragan Caddesi No:32, Besiktas, Istanbul, Turkey",
            "phone": "+90 212 555 0100",
            "email": "info@grandhotel.com",
            "website": "www.grandhotelistanbul.com",
            "wifi_name": "GrandHotel-Guest",
            "wifi_password": "Welcome2025!",
            "check_in_time": "14:00",
            "check_out_time": "12:00",
            "facilities": [
                {"name": "Swimming Pool", "icon": "pool", "hours": "07:00 - 22:00", "floor": "Rooftop", "description": "Heated infinity pool with Bosphorus view"},
                {"name": "Spa & Wellness", "icon": "spa", "hours": "09:00 - 21:00", "floor": "B1", "description": "Full-service spa with Turkish bath, sauna, steam room"},
                {"name": "Fitness Center", "icon": "gym", "hours": "06:00 - 23:00", "floor": "B1", "description": "State-of-the-art gym equipment"},
                {"name": "Restaurant - Bosphorus", "icon": "restaurant", "hours": "07:00 - 23:00", "floor": "1", "description": "Fine dining with panoramic views"},
                {"name": "Bar & Lounge", "icon": "bar", "hours": "16:00 - 01:00", "floor": "Rooftop", "description": "Cocktails and live music"},
                {"name": "Business Center", "icon": "business", "hours": "08:00 - 20:00", "floor": "2", "description": "Meeting rooms and workspace"},
                {"name": "Kids Club", "icon": "kids", "hours": "09:00 - 18:00", "floor": "1", "description": "Activities for children aged 4-12"},
                {"name": "Parking", "icon": "parking", "hours": "24/7", "floor": "B2", "description": "Valet and self-parking available"}
            ],
            "emergency_contacts": [
                {"name": "Reception", "number": "0", "description": "24/7 front desk"},
                {"name": "Security", "number": "111", "description": "Emergency security"},
                {"name": "Medical", "number": "112", "description": "Emergency medical services"},
                {"name": "Fire", "number": "110", "description": "Fire department"}
            ],
            "pool_hours": "07:00 - 22:00",
            "spa_hours": "09:00 - 21:00",
            "restaurant_hours": "07:00 - 23:00",
            "gym_hours": "06:00 - 23:00",
            "parking_info": "Valet parking available 24/7. Self-parking at B2 level.",
            "pet_policy": "Small pets allowed with prior arrangement. Pet fee: 200 TRY/night",
            "smoking_policy": "Non-smoking hotel. Designated smoking areas on terrace.",
            "languages": ["tr", "en", "de", "ru", "ar"],
            "currency": "TRY",
            "created_at": now_utc().isoformat(),
            "updated_at": now_utc().isoformat(),
        }},
        upsert=True
    )
    
    # Spa Services
    spa_services = [
        {"id": new_id(), "tenant_id": tenant_id, "name": "Turkish Bath (Hamam)", "description": "Traditional Turkish bath experience with foam massage", "duration_minutes": 60, "price": 500, "category": "bath", "available": True, "sort_order": 1, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Swedish Massage", "description": "Full body relaxation massage", "duration_minutes": 60, "price": 700, "category": "massage", "available": True, "sort_order": 2, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Aromatherapy Massage", "description": "Essential oil massage for deep relaxation", "duration_minutes": 90, "price": 900, "category": "massage", "available": True, "sort_order": 3, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Facial Treatment", "description": "Deep cleansing and hydrating facial", "duration_minutes": 45, "price": 400, "category": "facial", "available": True, "sort_order": 4, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Couples Massage", "description": "Side-by-side massage for two", "duration_minutes": 90, "price": 1600, "category": "massage", "available": True, "sort_order": 5, "created_at": now_utc().isoformat()},
    ]
    await db.spa_services.delete_many({"tenant_id": tenant_id})
    await db.spa_services.insert_many(spa_services)
    
    # SLA Rules
    sla_rules = [
        {"id": new_id(), "tenant_id": tenant_id, "category": "housekeeping", "department_code": "HK", "priority": "normal", "response_time_minutes": 15, "resolution_time_minutes": 45, "escalation_after_minutes": 30, "escalate_to_role": "manager", "auto_escalation_enabled": True, "notification_on_breach": True, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "category": "maintenance", "department_code": "TECH", "priority": "normal", "response_time_minutes": 20, "resolution_time_minutes": 120, "escalation_after_minutes": 60, "escalate_to_role": "manager", "auto_escalation_enabled": True, "notification_on_breach": True, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "category": "room_service", "department_code": "FB", "priority": "normal", "response_time_minutes": 10, "resolution_time_minutes": 30, "escalation_after_minutes": 20, "escalate_to_role": "manager", "auto_escalation_enabled": True, "notification_on_breach": True, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "category": "reception", "department_code": "FRONTDESK", "priority": "normal", "response_time_minutes": 5, "resolution_time_minutes": 30, "escalation_after_minutes": 15, "escalate_to_role": "manager", "auto_escalation_enabled": True, "notification_on_breach": True, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "category": "laundry", "department_code": "HK", "priority": "normal", "response_time_minutes": 15, "resolution_time_minutes": 240, "escalation_after_minutes": 60, "escalate_to_role": "manager", "auto_escalation_enabled": True, "notification_on_breach": True, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "category": "spa", "department_code": "SPA", "priority": "normal", "response_time_minutes": 15, "resolution_time_minutes": 60, "escalation_after_minutes": 30, "escalate_to_role": "manager", "auto_escalation_enabled": True, "notification_on_breach": True, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "category": "transport", "department_code": "CONCIERGE", "priority": "normal", "response_time_minutes": 10, "resolution_time_minutes": 60, "escalation_after_minutes": 30, "escalate_to_role": "manager", "auto_escalation_enabled": True, "notification_on_breach": True, "active": True, "created_at": now_utc().isoformat()},
    ]
    await db.sla_rules.delete_many({"tenant_id": tenant_id})
    await db.sla_rules.insert_many(sla_rules)
    
    # Response Templates
    templates = [
        {"id": new_id(), "tenant_id": tenant_id, "name": "Towels on the way", "category": "housekeeping", "body_tr": "Havlulariniz en kisa surede odaniza getirilecektir.", "body_en": "Your towels will be delivered to your room shortly.", "shortcut": "/towels", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Room cleaning scheduled", "category": "housekeeping", "body_tr": "Oda temizliginiz planlanmistir. Tahmini sure: 30 dakika.", "body_en": "Your room cleaning has been scheduled. Estimated time: 30 minutes.", "shortcut": "/clean", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Maintenance dispatched", "category": "maintenance", "body_tr": "Teknik ekibimiz konuyla ilgilenmek uzere yola cikmistir.", "body_en": "Our maintenance team has been dispatched to handle your request.", "shortcut": "/maint", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Order received", "category": "room_service", "body_tr": "Siparisini aldik! Tahmini teslimat: 25-35 dakika.", "body_en": "We received your order! Estimated delivery: 25-35 minutes.", "shortcut": "/order", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Thank you", "category": "general", "body_tr": "Geri bildiriminiz icin tesekkur ederiz. Iyi gunler dileriz!", "body_en": "Thank you for your feedback. We wish you a pleasant stay!", "shortcut": "/thanks", "created_at": now_utc().isoformat()},
    ]
    await db.response_templates.delete_many({"tenant_id": tenant_id})
    await db.response_templates.insert_many(templates)
    
    # Housekeeping Checklists
    checklists = [
        {"id": new_id(), "tenant_id": tenant_id, "name": "Standard Room Cleaning", "room_type": "standard", "items": [
            {"text": "Make bed with fresh linens", "required": True},
            {"text": "Vacuum carpets and mop floors", "required": True},
            {"text": "Clean and sanitize bathroom", "required": True},
            {"text": "Replace towels and amenities", "required": True},
            {"text": "Empty trash bins", "required": True},
            {"text": "Dust all surfaces", "required": True},
            {"text": "Check minibar and restock", "required": False},
            {"text": "Clean windows and mirrors", "required": False},
            {"text": "Check all lights and fixtures", "required": True},
            {"text": "Spray room freshener", "required": False},
        ], "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Suite Deep Cleaning", "room_type": "suite", "items": [
            {"text": "Make bed with premium linens", "required": True},
            {"text": "Vacuum and steam clean carpets", "required": True},
            {"text": "Deep clean all bathrooms", "required": True},
            {"text": "Replace premium amenities set", "required": True},
            {"text": "Clean and polish all surfaces", "required": True},
            {"text": "Clean kitchen/bar area", "required": True},
            {"text": "Restock minibar fully", "required": True},
            {"text": "Clean all windows and balcony", "required": True},
            {"text": "Place welcome amenity", "required": True},
            {"text": "Check all electronics and AC", "required": True},
            {"text": "Arrange fresh flowers", "required": False},
            {"text": "Final quality inspection", "required": True},
        ], "active": True, "created_at": now_utc().isoformat()},
    ]
    await db.hk_checklists.delete_many({"tenant_id": tenant_id})
    await db.hk_checklists.insert_many(checklists)
    
    # Announcements
    announcements = [
        {"id": new_id(), "tenant_id": tenant_id, "title": "Pool Hours Extended", "title_tr": "Havuz Saatleri Uzatildi", "body": "The rooftop pool hours have been extended to 23:00 for the summer season. Enjoy!", "body_tr": "Cati havuz saatleri yaz sezonu icin 23:00'e uzatilmistir. Keyifli yuzuler!", "type": "info", "active": True, "priority": "normal", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "title": "Live Jazz Night", "title_tr": "Canli Caz Gecesi", "body": "Join us every Friday at the Rooftop Bar for live jazz music from 20:00 to midnight.", "body_tr": "Her Cuma Cati Bar'da 20:00-24:00 arasi canli caz muzigi keyfine davetlisiniz.", "type": "event", "active": True, "priority": "normal", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "title": "Spa Special Offer", "title_tr": "Spa Ozel Firsati", "body": "20% discount on all spa treatments when booked before 14:00. Valid this month!", "body_tr": "Saat 14:00 oncesi yapilan tum spa randevularinda %20 indirim! Bu ay gecerli.", "type": "promo", "active": True, "priority": "normal", "created_at": now_utc().isoformat()},
    ]
    await db.announcements.delete_many({"tenant_id": tenant_id})
    await db.announcements.insert_many(announcements)
    
    # Restaurants
    restaurants_seed = [
        {"id": new_id(), "tenant_id": tenant_id, "name": "Bosphorus Restaurant", "description": "Fine dining with panoramic Bosphorus views. Turkish and international cuisine.", "cuisine_type": "Turkish & International", "open_time": "12:00", "close_time": "23:00", "slot_duration_minutes": 90, "total_seats": 60, "dress_code": "Smart casual", "phone": "Ext. 101", "location": "1st Floor", "active": True, "sort_order": 1, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Terrace Grill", "description": "Open-air rooftop BBQ and seafood grill.", "cuisine_type": "Grill & Seafood", "open_time": "18:00", "close_time": "23:00", "slot_duration_minutes": 90, "total_seats": 30, "dress_code": "Casual", "phone": "Ext. 102", "location": "Rooftop", "active": True, "sort_order": 2, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Sakura Asian Kitchen", "description": "Japanese, Thai and Chinese cuisine with teppanyaki.", "cuisine_type": "Asian", "open_time": "12:00", "close_time": "22:00", "slot_duration_minutes": 75, "total_seats": 24, "dress_code": "Smart casual", "phone": "Ext. 103", "location": "2nd Floor", "active": True, "sort_order": 3, "created_at": now_utc().isoformat()},
    ]
    await db.restaurants.delete_many({"tenant_id": tenant_id})
    await db.restaurants.insert_many(restaurants_seed)
    
    # Additional Departments for new services
    extra_depts = [
        {"id": new_id(), "tenant_id": tenant_id, "name": "Spa & Wellness", "code": "SPA", "description": "Spa, massage, Turkish bath services", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Concierge", "code": "CONCIERGE", "description": "Transport, tours, reservations, special requests", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Bellboy", "code": "BELL", "description": "Luggage, room escort, valet services", "created_at": now_utc().isoformat()},
    ]
    for dept in extra_depts:
        existing_dept = await db.departments.find_one({"tenant_id": tenant_id, "code": dept["code"]})
        if not existing_dept:
            await db.departments.insert_one(dept)
    
    # Additional Service Categories for extended guest requests
    extra_categories = [
        {"id": new_id(), "tenant_id": tenant_id, "name": "Laundry & Ironing", "department_code": "HK", "icon": "laundry", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Spa & Massage", "department_code": "SPA", "icon": "spa", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Transport & Transfer", "department_code": "CONCIERGE", "icon": "transport", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Wake-up Call", "department_code": "FRONTDESK", "icon": "alarm", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Bellboy & Luggage", "department_code": "BELL", "icon": "luggage", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Key & Access", "department_code": "FRONTDESK", "icon": "key", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Minibar", "department_code": "FB", "icon": "minibar", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Express Check-out", "department_code": "FRONTDESK", "icon": "checkout", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Complaint", "department_code": "FRONTDESK", "icon": "complaint", "created_at": now_utc().isoformat()},
    ]
    for cat in extra_categories:
        existing_cat = await db.service_categories.find_one({"tenant_id": tenant_id, "name": cat["name"]})
        if not existing_cat:
            await db.service_categories.insert_one(cat)

    # ---- Gamification Seed Data ----
    badges_seed = [
        {"id": new_id(), "tenant_id": tenant_id, "name": "Ilk Rezervasyon", "description": "Ilk otel rezervasyonunu tamamladiniz", "icon": "calendar-check", "color": "#10B981", "category": "milestone", "criteria_type": "auto", "criteria_value": 1, "criteria_event": "reservation_confirmed", "points_reward": 50, "sort_order": 1, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Yorum Krali", "description": "5 yorum yazdiniz", "icon": "message-square", "color": "#3B82F6", "category": "engagement", "criteria_type": "count", "criteria_value": 5, "criteria_event": "review_written", "points_reward": 100, "sort_order": 2, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Sadik Misafir", "description": "10 kez konakladiniz", "icon": "heart", "color": "#EF4444", "category": "loyalty", "criteria_type": "count", "criteria_value": 10, "criteria_event": "stay_completed", "points_reward": 500, "sort_order": 3, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Spa Gurmesi", "description": "3 farkli spa hizmeti denediniz", "icon": "sparkles", "color": "#8B5CF6", "category": "experience", "criteria_type": "count", "criteria_value": 3, "criteria_event": "spa_booking", "points_reward": 75, "sort_order": 4, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Erken Kusu", "description": "3 kez erken check-in yapildi", "icon": "sunrise", "color": "#F59E0B", "category": "behavior", "criteria_type": "count", "criteria_value": 3, "criteria_event": "early_checkin", "points_reward": 30, "sort_order": 5, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "VIP Misafir", "description": "Platinum seviyesine ulastiniz", "icon": "crown", "color": "#D97706", "category": "milestone", "criteria_type": "tier", "criteria_value": 1500, "criteria_event": "tier_upgrade", "points_reward": 200, "sort_order": 6, "active": True, "created_at": now_utc().isoformat()},
    ]
    await db.badges.delete_many({"tenant_id": tenant_id})
    await db.badges.insert_many(badges_seed)

    challenges_seed = [
        {"id": new_id(), "tenant_id": tenant_id, "name": "Hosgeldin Challenge", "description": "Bu ay 3 farkli otel hizmetinden faydalanin", "type": "count", "target_event": "service_used", "target_value": 3, "points_reward": 100, "badge_reward_id": "", "start_date": now_utc().isoformat(), "end_date": "", "status": "active", "participants_count": 12, "completions_count": 4, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Gurme Kesfetici", "description": "Tum restoranlarda en az 1 siparis verin", "type": "count", "target_event": "restaurant_order", "target_value": 3, "points_reward": 150, "badge_reward_id": "", "start_date": now_utc().isoformat(), "end_date": "", "status": "active", "participants_count": 8, "completions_count": 2, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Spa Haftaligi", "description": "Bu hafta 2 spa randevusu alin", "type": "count", "target_event": "spa_booking", "target_value": 2, "points_reward": 75, "badge_reward_id": "", "start_date": now_utc().isoformat(), "end_date": "", "status": "active", "participants_count": 5, "completions_count": 1, "created_at": now_utc().isoformat()},
    ]
    await db.challenges.delete_many({"tenant_id": tenant_id})
    await db.challenges.insert_many(challenges_seed)

    rewards_seed = [
        {"id": new_id(), "tenant_id": tenant_id, "name": "Ucretsiz Spa Masaji", "description": "30 dakikalik rahatlama masaji", "points_cost": 500, "category": "spa", "icon": "sparkles", "stock": 10, "redeemed_count": 3, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Oda Yukseltme", "description": "Bir ust oda kategorisine ucretsiz gecis", "points_cost": 1000, "category": "room", "icon": "arrow-up-circle", "stock": 5, "redeemed_count": 1, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Gec Check-out", "description": "14:00'e kadar uzatilmis check-out", "points_cost": 200, "category": "service", "icon": "clock", "stock": -1, "redeemed_count": 7, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Restoran Indirimi %20", "description": "Tum restoranlarda %20 indirim", "points_cost": 300, "category": "dining", "icon": "utensils", "stock": -1, "redeemed_count": 5, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Havalimanı Transferi", "description": "Ucretsiz VIP havalimanı transferi", "points_cost": 800, "category": "transport", "icon": "car", "stock": 3, "redeemed_count": 0, "active": True, "created_at": now_utc().isoformat()},
    ]
    await db.rewards_catalog.delete_many({"tenant_id": tenant_id})
    await db.rewards_catalog.insert_many(rewards_seed)

    # ---- A/B Testing Seed Data ----
    ab_experiments_seed = [
        {"id": new_id(), "tenant_id": tenant_id, "name": "Check-in Akisi Optimizasyonu", "description": "Yeni check-in formu vs mevcut form karsilastirmasi", "hypothesis": "Yeni form check-in suresini %30 azaltir", "feature_area": "guest_experience", "variants": [{"name": "control", "traffic_percent": 50, "description": "Mevcut check-in formu"}, {"name": "variant_a", "traffic_percent": 50, "description": "Yeni hizli check-in formu"}], "status": "running", "target_audience": "all_guests", "target_sample_size": 200, "primary_metric": "conversion_rate", "secondary_metrics": ["time_to_complete", "satisfaction_score"], "start_date": now_utc().isoformat(), "end_date": "", "total_participants": 87, "created_by": "system", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Oda Servisi Menu Duzeni", "description": "Foto galeri vs liste gorunumu karsilastirmasi", "hypothesis": "Galeri gorunumu siparis oranini %15 artirir", "feature_area": "room_service", "variants": [{"name": "control", "traffic_percent": 50, "description": "Liste gorunumu"}, {"name": "variant_a", "traffic_percent": 50, "description": "Foto galeri gorunumu"}], "status": "running", "target_audience": "room_guests", "target_sample_size": 150, "primary_metric": "conversion_rate", "secondary_metrics": ["avg_order_value"], "start_date": now_utc().isoformat(), "end_date": "", "total_participants": 43, "created_by": "system", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Sadakat Puani Gosterimi", "description": "Progress bar vs sayisal gosterim testi", "hypothesis": "Progress bar motivasyonu artirir", "feature_area": "loyalty", "variants": [{"name": "control", "traffic_percent": 33, "description": "Sadece sayi"}, {"name": "variant_a", "traffic_percent": 33, "description": "Progress bar"}, {"name": "variant_b", "traffic_percent": 34, "description": "Progress bar + animasyon"}], "status": "draft", "target_audience": "loyalty_members", "target_sample_size": 300, "primary_metric": "engagement_rate", "secondary_metrics": ["points_earned", "redemption_rate"], "start_date": "", "end_date": "", "total_participants": 0, "created_by": "system", "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Karsilama Mesaji Testi", "description": "Resmi vs samimi karsilama mesaji", "hypothesis": "Samimi mesaj misafir memnuniyetini artirir", "feature_area": "communication", "variants": [{"name": "control", "traffic_percent": 50, "description": "Resmi ton"}, {"name": "variant_a", "traffic_percent": 50, "description": "Samimi ton"}], "status": "completed", "target_audience": "all_guests", "target_sample_size": 100, "primary_metric": "satisfaction_score", "secondary_metrics": ["response_rate"], "start_date": now_utc().isoformat(), "end_date": now_utc().isoformat(), "total_participants": 156, "created_by": "system", "created_at": now_utc().isoformat()},
    ]
    await db.ab_experiments.delete_many({"tenant_id": tenant_id})
    await db.ab_experiments.insert_many(ab_experiments_seed)

    # ---- Loyalty Engine V3 Seed Data ----
    # Tier config
    await db.tier_config.delete_many({"tenant_id": tenant_id})
    await db.tier_config.insert_one({
        "id": new_id(), "tenant_id": tenant_id,
        "tiers": [
            {"name": "Bronz", "slug": "bronze", "min_points": 0, "color": "#CD7F32", "icon": "shield",
             "benefits": ["Hosgeldin puani", "Dogum gunu surprizi"], "multiplier": 1.0, "sort_order": 1},
            {"name": "Gumus", "slug": "silver", "min_points": 500, "color": "#C0C0C0", "icon": "award",
             "benefits": ["Oda servisi %5 indirim", "Ucretsiz WiFi yukseltme", "Oncelikli rezervasyon"], "multiplier": 1.25, "sort_order": 2},
            {"name": "Altin", "slug": "gold", "min_points": 1500, "color": "#FFD700", "icon": "star",
             "benefits": ["Tum hizmetlerde %10 indirim", "Gec check-out (14:00)", "Ucretsiz oda yukseltme", "Lounge erisimi"], "multiplier": 1.5, "sort_order": 3},
            {"name": "Platin", "slug": "platinum", "min_points": 5000, "color": "#E5E4E2", "icon": "crown",
             "benefits": ["Tum hizmetlerde %20 indirim", "Gec check-out (16:00)", "Garantili oda yukseltme", "VIP lounge erisimi", "Hosgeldin amenity", "Ucretsiz havalimanı transferi", "Ozel concierge"], "multiplier": 2.0, "sort_order": 4},
        ],
        "auto_upgrade": True, "auto_downgrade": True, "downgrade_period_days": 365,
        "evaluation_period": "yearly", "updated_at": now_utc().isoformat()
    })

    # Update existing loyalty accounts with tier_slug
    await db.loyalty_accounts.update_many(
        {"tenant_id": tenant_id, "tier_name": "Silver"},
        {"$set": {"tier_slug": "silver", "tier_color": "#C0C0C0"}}
    )
    await db.loyalty_accounts.update_many(
        {"tenant_id": tenant_id, "tier_name": "Gold"},
        {"$set": {"tier_slug": "gold", "tier_color": "#FFD700"}}
    )

    # Point rules
    await db.point_rules.delete_many({"tenant_id": tenant_id})
    point_rules_seed = [
        {"id": new_id(), "tenant_id": tenant_id, "name": "Konaklama Puani", "description": "Her gece konaklama icin puan kazanin", "rule_type": "accommodation", "condition": {"hotel": "*", "min_nights": 1, "room_type": "*"}, "points": 100, "multiplier_enabled": True, "active": True, "valid_from": "", "valid_until": "", "sort_order": 1, "applies_to_tiers": [], "property_ids": [], "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Deluxe 3 Gece Bonusu", "description": "Deluxe odada 3+ gece kalin, ekstra 500 puan", "rule_type": "accommodation", "condition": {"hotel": "*", "min_nights": 3, "room_type": "deluxe"}, "points": 500, "multiplier_enabled": True, "active": True, "valid_from": "", "valid_until": "", "sort_order": 2, "applies_to_tiers": [], "property_ids": [], "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Suite VIP Bonus", "description": "Suite odada konaklama icin 1000 bonus puan", "rule_type": "accommodation", "condition": {"hotel": "*", "min_nights": 1, "room_type": "suite"}, "points": 1000, "multiplier_enabled": True, "active": True, "valid_from": "", "valid_until": "", "sort_order": 3, "applies_to_tiers": [], "property_ids": [], "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Harcama Puani", "description": "Her 100 TRY harcama icin 10 puan", "rule_type": "spend", "condition": {"per_amount": 100, "currency": "TRY"}, "points": 10, "multiplier_enabled": True, "active": True, "valid_from": "", "valid_until": "", "sort_order": 4, "applies_to_tiers": [], "property_ids": [], "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Spa Aktivite Puani", "description": "Her spa rezervasyonunda 50 puan", "rule_type": "activity", "condition": {"event_type": "spa_booking"}, "points": 50, "multiplier_enabled": True, "active": True, "valid_from": "", "valid_until": "", "sort_order": 5, "applies_to_tiers": [], "property_ids": [], "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Restoran Siparis Puani", "description": "Her restoran siparisinde 25 puan", "rule_type": "activity", "condition": {"event_type": "order_completed"}, "points": 25, "multiplier_enabled": True, "active": True, "valid_from": "", "valid_until": "", "sort_order": 6, "applies_to_tiers": [], "property_ids": [], "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Yorum Yazma Bonusu", "description": "Yorum yazin 30 puan kazanin", "rule_type": "activity", "condition": {"event_type": "review_written"}, "points": 30, "multiplier_enabled": False, "active": True, "valid_from": "", "valid_until": "", "sort_order": 7, "applies_to_tiers": [], "property_ids": [], "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "VIP Ozel Davet", "description": "VIP etkinlik davetlerine ozel puan", "rule_type": "custom", "condition": {"trigger": "manual"}, "points": 1000, "multiplier_enabled": False, "active": True, "valid_from": "", "valid_until": "", "sort_order": 8, "applies_to_tiers": ["gold", "platinum"], "property_ids": [], "created_at": now_utc().isoformat()},
    ]
    await db.point_rules.insert_many(point_rules_seed)

    # Enhanced rewards catalog V3
    await db.rewards_catalog_v3.delete_many({"tenant_id": tenant_id})
    rewards_v3_seed = [
        {"id": new_id(), "tenant_id": tenant_id, "name": "Ucretsiz Gece Konaklama", "description": "1 gece ucretsiz standart oda konaklama", "points_cost": 2000, "category": "konaklama", "subcategory": "standart", "icon": "bed", "image_url": "", "min_tier": "silver", "is_partner": False, "partner_name": "", "partner_type": "", "is_seasonal": False, "season": "", "valid_from": "", "valid_until": "", "stock": 10, "redeemed_count": 2, "sort_order": 1, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Spa Paketi", "description": "60 dakika tam vucut masaji + sauna", "points_cost": 800, "category": "spa", "subcategory": "masaj", "icon": "sparkles", "image_url": "", "min_tier": "bronze", "is_partner": False, "partner_name": "", "partner_type": "", "is_seasonal": False, "season": "", "valid_from": "", "valid_until": "", "stock": 20, "redeemed_count": 5, "sort_order": 2, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Restoran Aksam Yemegi", "description": "2 kisilik ozel aksam yemegi", "points_cost": 1200, "category": "restoran", "subcategory": "fine_dining", "icon": "utensils", "image_url": "", "min_tier": "silver", "is_partner": False, "partner_name": "", "partner_type": "", "is_seasonal": False, "season": "", "valid_from": "", "valid_until": "", "stock": -1, "redeemed_count": 3, "sort_order": 3, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Oda Yukseltme", "description": "Bir ust kategori odaya ucretsiz gecis", "points_cost": 1500, "category": "konaklama", "subcategory": "upgrade", "icon": "arrow-up-circle", "image_url": "", "min_tier": "gold", "is_partner": False, "partner_name": "", "partner_type": "", "is_seasonal": False, "season": "", "valid_from": "", "valid_until": "", "stock": 5, "redeemed_count": 1, "sort_order": 4, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Havayolu Milleri (1000 Mil)", "description": "Turkish Airlines 1000 mil transferi", "points_cost": 3000, "category": "partner", "subcategory": "havayolu", "icon": "plane", "image_url": "", "min_tier": "gold", "is_partner": True, "partner_name": "Turkish Airlines", "partner_type": "havayolu", "is_seasonal": False, "season": "", "valid_from": "", "valid_until": "", "stock": -1, "redeemed_count": 0, "sort_order": 5, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Arac Kiralama 1 Gun", "description": "1 gunluk ucretsiz arac kiralama", "points_cost": 2500, "category": "partner", "subcategory": "arac", "icon": "car", "image_url": "", "min_tier": "gold", "is_partner": True, "partner_name": "Enterprise", "partner_type": "arac_kiralama", "is_seasonal": False, "season": "", "valid_from": "", "valid_until": "", "stock": 3, "redeemed_count": 0, "sort_order": 6, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Gec Check-out (16:00)", "description": "16:00'ye kadar uzatilmis check-out", "points_cost": 300, "category": "hizmet", "subcategory": "checkout", "icon": "clock", "image_url": "", "min_tier": "bronze", "is_partner": False, "partner_name": "", "partner_type": "", "is_seasonal": False, "season": "", "valid_from": "", "valid_until": "", "stock": -1, "redeemed_count": 12, "sort_order": 7, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Yaz Ozel: Havuz VIP", "description": "Tum gun VIP havuz alani erisimi", "points_cost": 500, "category": "sezonsal", "subcategory": "yaz", "icon": "sun", "image_url": "", "min_tier": "bronze", "is_partner": False, "partner_name": "", "partner_type": "", "is_seasonal": True, "season": "yaz", "valid_from": "2025-06-01", "valid_until": "2025-09-30", "stock": 50, "redeemed_count": 8, "sort_order": 8, "active": True, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Platin Ozel: Ozel Concierge", "description": "24 saat kisisel concierge hizmeti", "points_cost": 5000, "category": "ozel", "subcategory": "platin", "icon": "crown", "image_url": "", "min_tier": "platinum", "is_partner": False, "partner_name": "", "partner_type": "", "is_seasonal": False, "season": "", "valid_from": "", "valid_until": "", "stock": 2, "redeemed_count": 0, "sort_order": 9, "active": True, "created_at": now_utc().isoformat()},
    ]
    await db.rewards_catalog_v3.insert_many(rewards_v3_seed)

    # Loyalty campaigns
    await db.loyalty_campaigns.delete_many({"tenant_id": tenant_id})
    campaigns_seed = [
        {"id": new_id(), "tenant_id": tenant_id, "name": "Yaz Kampanyasi 2x Puan", "description": "Temmuz-Agustos arasinda tum konaklamalarda 2x puan", "campaign_type": "seasonal", "target_segment": "all", "target_tiers": [], "channel": "all", "bonus_points": 0, "bonus_multiplier": 2.0, "reward_id": "", "message_template": "Bu yaz tatilinde 2x puan kazanin!", "start_date": "2025-07-01", "end_date": "2025-08-31", "status": "active", "sent_count": 450, "opened_count": 280, "converted_count": 85, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Dogum Gunu Surprizi", "description": "Dogum gununde 500 bonus puan", "campaign_type": "birthday", "target_segment": "all", "target_tiers": [], "channel": "email", "bonus_points": 500, "bonus_multiplier": 1.0, "reward_id": "", "message_template": "Dogum gununuz kutlu olsun! 500 bonus puan hediyemiz!", "start_date": "", "end_date": "", "status": "active", "sent_count": 120, "opened_count": 95, "converted_count": 78, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Geri Donus Kampanyasi", "description": "60+ gun inaktif uyelere ozel 300 puan", "campaign_type": "win_back", "target_segment": "inactive", "target_tiers": [], "channel": "sms", "bonus_points": 300, "bonus_multiplier": 1.0, "reward_id": "", "message_template": "Sizi ozledik! Geri donun, 300 bonus puan kazanin!", "start_date": "", "end_date": "", "status": "active", "sent_count": 35, "opened_count": 20, "converted_count": 8, "created_at": now_utc().isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "name": "Altin Seviye Ozel Teklif", "description": "Altin ve ustu uyeler icin ozel spa indirimi", "campaign_type": "tier_exclusive", "target_segment": "tier_based", "target_tiers": ["gold", "platinum"], "channel": "push", "bonus_points": 200, "bonus_multiplier": 1.0, "reward_id": "", "message_template": "Altin uyelerimize ozel: Ucretsiz spa deneyimi!", "start_date": "2025-07-01", "end_date": "2025-07-31", "status": "draft", "sent_count": 0, "opened_count": 0, "converted_count": 0, "created_at": now_utc().isoformat()},
    ]
    await db.loyalty_campaigns.insert_many(campaigns_seed)

    # Referral config
    await db.referral_config.delete_many({"tenant_id": tenant_id})
    await db.referral_config.insert_one({
        "id": new_id(), "tenant_id": tenant_id,
        "enabled": True, "referrer_points": 200, "referee_points": 100,
        "max_referrals_per_member": 20, "require_first_stay": True,
        "updated_at": now_utc().isoformat()
    })

    # Sample referrals
    await db.member_referrals.delete_many({"tenant_id": tenant_id})
    ref_code = "REF-" + hashlib.md5(f"{tenant_id}{contacts[2]['id']}".encode()).hexdigest()[:6].upper()
    await db.loyalty_accounts.update_one(
        {"tenant_id": tenant_id, "contact_id": contacts[2]["id"]},
        {"$set": {"referral_code": ref_code}}
    )
    await db.member_referrals.insert_many([
        {"id": new_id(), "tenant_id": tenant_id, "referrer_contact_id": contacts[2]["id"], "referee_contact_id": contacts[0]["id"], "referral_code": ref_code, "status": "completed", "referrer_points_earned": 200, "referee_points_earned": 100, "created_at": (now_utc() - timedelta(days=15)).isoformat()},
        {"id": new_id(), "tenant_id": tenant_id, "referrer_contact_id": contacts[2]["id"], "referee_contact_id": contacts[1]["id"], "referral_code": ref_code, "status": "pending", "referrer_points_earned": 0, "referee_points_earned": 0, "created_at": (now_utc() - timedelta(days=5)).isoformat()},
    ])

    # Communication preferences
    await db.comm_prefs.delete_many({"tenant_id": tenant_id})
    await db.comm_prefs.insert_one({
        "id": new_id(), "tenant_id": tenant_id,
        "email_enabled": True, "sms_enabled": False, "whatsapp_enabled": False,
        "push_enabled": True, "inapp_enabled": True,
        "birthday_campaign": True, "anniversary_campaign": True,
        "tier_change_notification": True, "points_reminder_days": 30,
        "inactive_reminder_days": 60, "updated_at": now_utc().isoformat()
    })

    return {
        "message": "Seed data created successfully",
        "tenant_slug": "grand-hotel",
        "login": {"email": "admin@grandhotel.com", "password": "admin123"},
        "sample_qr_links": {
            "room": "/g/grand-hotel/room/R101",
            "table": "/g/grand-hotel/table/T1"
        }
    }

# ============ PHASE 5: DEMO MODE ============
@router.post("/demo/reset")
async def reset_demo():
    """Reset demo tenant data for fresh demo"""
    collections = ["tenants", "users", "departments", "service_categories", "rooms",
                    "guest_requests", "tables", "menu_categories", "menu_items",
                    "orders", "contacts", "conversations", "messages",
                    "loyalty_accounts", "loyalty_ledger", "reviews", "review_replies",
                    "offers", "payment_links", "reservations", "connector_credentials",
                    "audit_logs", "sessions", "billing_accounts", "subscriptions", "invoices",
                    "onboarding", "referrals", "referral_events", "consent_logs", "retention_policies"]
    for col in collections:
        await db[col].delete_many({})
    
    # Re-seed
    return await seed_data()
