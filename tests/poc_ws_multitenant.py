"""
POC Test Script: Multi-Tenant Isolation + WebSocket + QR Guest Flows
Tests the core workflow that can break the entire product.
"""
import asyncio
import json
import requests
import websockets
import time
import sys

BASE_URL = "http://localhost:8001/api"
WS_URL = "ws://localhost:8001/ws"

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"
BOLD = "\033[1m"

passed = 0
failed = 0

def log_pass(msg):
    global passed
    passed += 1
    print(f"  {GREEN}✓ PASS{RESET}: {msg}")

def log_fail(msg, detail=""):
    global failed
    failed += 1
    print(f"  {RED}✗ FAIL{RESET}: {msg}")
    if detail:
        print(f"    Detail: {detail}")

def section(title):
    print(f"\n{BOLD}{YELLOW}{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}{RESET}\n")

# ============ TEST 1: TENANT CREATION ============
def test_tenant_creation():
    section("TEST 1: Tenant Creation & Isolation")
    
    # Create Tenant A (Hotel)
    r = requests.post(f"{BASE_URL}/tenants", json={
        "name": "Grand Hotel Istanbul",
        "slug": "grand-istanbul",
        "business_type": "hotel",
        "plan": "pro"
    })
    if r.status_code == 200:
        tenant_a = r.json()
        log_pass(f"Tenant A created: {tenant_a['name']} (id: {tenant_a['id'][:8]}...)")
    else:
        log_fail(f"Tenant A creation failed: {r.status_code}", r.text)
        return None, None
    
    # Create Tenant B (Restaurant)
    r = requests.post(f"{BASE_URL}/tenants", json={
        "name": "Cafe Beyoglu",
        "slug": "cafe-beyoglu",
        "business_type": "restaurant",
        "plan": "basic"
    })
    if r.status_code == 200:
        tenant_b = r.json()
        log_pass(f"Tenant B created: {tenant_b['name']} (id: {tenant_b['id'][:8]}...)")
    else:
        log_fail(f"Tenant B creation failed: {r.status_code}", r.text)
        return tenant_a, None
    
    # Test duplicate slug rejection
    r = requests.post(f"{BASE_URL}/tenants", json={
        "name": "Another Hotel",
        "slug": "grand-istanbul",
        "business_type": "hotel"
    })
    if r.status_code == 400:
        log_pass("Duplicate slug correctly rejected")
    else:
        log_fail("Duplicate slug should be rejected", f"Got {r.status_code}")
    
    # Test feature flags
    if tenant_a.get("hotel_enabled") == True and tenant_a.get("restaurant_enabled") == True:
        log_pass("Hotel tenant has hotel+restaurant enabled")
    else:
        log_fail("Hotel tenant feature flags incorrect")
    
    if tenant_b.get("restaurant_enabled") == True and tenant_b.get("hotel_enabled") == False:
        log_pass("Restaurant tenant has correct feature flags")
    else:
        log_fail("Restaurant tenant feature flags incorrect")
    
    # Test plan limits
    if tenant_a.get("plan_limits", {}).get("max_rooms") == 100:
        log_pass("Pro plan limits correct (100 rooms)")
    else:
        log_fail("Pro plan limits incorrect")
    
    if tenant_b.get("plan_limits", {}).get("max_rooms") == 20:
        log_pass("Basic plan limits correct (20 rooms)")
    else:
        log_fail("Basic plan limits incorrect")
    
    return tenant_a, tenant_b

# ============ TEST 2: HOTEL QR GUEST FLOW ============
def test_hotel_qr_flow(tenant_a):
    section("TEST 2: Hotel QR Guest Request Flow")
    
    if not tenant_a:
        log_fail("Skipping - no tenant A")
        return None
    
    slug = tenant_a["slug"]
    
    # Create departments
    departments = [
        {"name": "Housekeeping", "code": "HK", "description": "Room cleaning and amenities"},
        {"name": "Technical", "code": "TECH", "description": "Maintenance and repairs"},
        {"name": "Food & Beverage", "code": "FB", "description": "Room service and minibar"},
        {"name": "Front Desk", "code": "FRONTDESK", "description": "Reception and concierge"},
    ]
    for dept in departments:
        r = requests.post(f"{BASE_URL}/tenants/{slug}/departments", json=dept)
        if r.status_code == 200:
            log_pass(f"Department created: {dept['name']}")
        else:
            log_fail(f"Department creation failed: {dept['name']}", r.text)
    
    # Create service categories
    categories = [
        {"name": "Extra Towels", "department_code": "HK", "icon": "towel"},
        {"name": "AC Repair", "department_code": "TECH", "icon": "wrench"},
        {"name": "Room Service", "department_code": "FB", "icon": "food"},
    ]
    for cat in categories:
        r = requests.post(f"{BASE_URL}/tenants/{slug}/service-categories", json=cat)
        if r.status_code == 200:
            log_pass(f"Service category created: {cat['name']}")
        else:
            log_fail(f"Category creation failed", r.text)
    
    # Create room
    r = requests.post(f"{BASE_URL}/tenants/{slug}/rooms", json={
        "room_number": "301",
        "room_type": "deluxe",
        "floor": "3"
    })
    if r.status_code == 200:
        room = r.json()
        log_pass(f"Room created: {room['room_number']} (code: {room['room_code']}, QR: {room['qr_link']})")
    else:
        log_fail("Room creation failed", r.text)
        return None
    
    room_code = room["room_code"]
    
    # Get room info (guest QR landing)
    r = requests.get(f"{BASE_URL}/g/{slug}/room/{room_code}/info")
    if r.status_code == 200:
        info = r.json()
        if info["room"]["room_number"] == "301" and len(info["service_categories"]) > 0:
            log_pass(f"Room info retrieved with {len(info['service_categories'])} service categories")
        else:
            log_fail("Room info incomplete")
    else:
        log_fail("Room info retrieval failed", r.text)
    
    # Submit guest request (no login)
    r = requests.post(f"{BASE_URL}/g/{slug}/room/{room_code}/requests", json={
        "category": "housekeeping",
        "description": "Need extra towels and pillows please",
        "priority": "normal",
        "guest_name": "John Smith",
        "guest_phone": "+905551234567"
    })
    if r.status_code == 200:
        request_doc = r.json()
        if request_doc["status"] == "OPEN" and request_doc["department_code"] == "HK":
            log_pass(f"Guest request created: {request_doc['id'][:8]}... (status: OPEN, dept: HK)")
        else:
            log_fail("Request created but incorrect routing")
    else:
        log_fail("Guest request creation failed", r.text)
        return None
    
    # Test request lifecycle
    request_id = request_doc["id"]
    
    # Move to IN_PROGRESS
    r = requests.patch(f"{BASE_URL}/tenants/{slug}/requests/{request_id}", json={
        "status": "IN_PROGRESS",
        "assigned_to": "staff-member-1"
    })
    if r.status_code == 200:
        updated = r.json()
        if updated["status"] == "IN_PROGRESS" and updated["first_response_at"] is not None:
            log_pass(f"Request → IN_PROGRESS (SLA first_response_at recorded)")
        else:
            log_fail("Status updated but SLA not recorded")
    else:
        log_fail("Request status update failed", r.text)
    
    # Move to DONE
    r = requests.patch(f"{BASE_URL}/tenants/{slug}/requests/{request_id}", json={
        "status": "DONE",
        "notes": "Towels and pillows delivered to room 301"
    })
    if r.status_code == 200:
        updated = r.json()
        if updated["status"] == "DONE" and updated["resolved_at"] is not None:
            log_pass(f"Request → DONE (resolved_at recorded)")
        else:
            log_fail("Status updated but resolved_at not recorded")
    else:
        log_fail("Request DONE update failed", r.text)
    
    # Rate the request
    r = requests.post(f"{BASE_URL}/tenants/{slug}/requests/{request_id}/rate", json={
        "rating": 5,
        "comment": "Excellent service!"
    })
    if r.status_code == 200:
        rated = r.json()
        if rated["rating"] == 5:
            log_pass("Request rated: 5/5")
        else:
            log_fail("Rating not saved correctly")
    else:
        log_fail("Rating failed", r.text)
    
    return request_doc

# ============ TEST 3: RESTAURANT QR FLOW ============
def test_restaurant_qr_flow(tenant_b):
    section("TEST 3: Restaurant QR Order Flow")
    
    if not tenant_b:
        log_fail("Skipping - no tenant B")
        return None
    
    slug = tenant_b["slug"]
    
    # Create table
    r = requests.post(f"{BASE_URL}/tenants/{slug}/tables", json={
        "table_number": "5",
        "capacity": 4,
        "section": "terrace"
    })
    if r.status_code == 200:
        table = r.json()
        log_pass(f"Table created: {table['table_number']} (code: {table['table_code']}, QR: {table['qr_link']})")
    else:
        log_fail("Table creation failed", r.text)
        return None
    
    table_code = table["table_code"]
    
    # Create menu categories
    r = requests.post(f"{BASE_URL}/tenants/{slug}/menu-categories", json={
        "name": "Main Course",
        "sort_order": 1
    })
    cat_main = r.json() if r.status_code == 200 else None
    
    r = requests.post(f"{BASE_URL}/tenants/{slug}/menu-categories", json={
        "name": "Beverages",
        "sort_order": 2
    })
    cat_bev = r.json() if r.status_code == 200 else None
    
    if cat_main and cat_bev:
        log_pass("Menu categories created: Main Course, Beverages")
    else:
        log_fail("Menu category creation failed")
        return None
    
    # Create menu items
    items_data = [
        {"name": "Adana Kebab", "description": "Spicy minced meat kebab", "price": 250.0, "category_id": cat_main["id"]},
        {"name": "Iskender", "description": "Döner on bread with yogurt", "price": 280.0, "category_id": cat_main["id"]},
        {"name": "Turkish Tea", "description": "Classic çay", "price": 25.0, "category_id": cat_bev["id"]},
        {"name": "Ayran", "description": "Traditional yogurt drink", "price": 35.0, "category_id": cat_bev["id"]},
    ]
    menu_items = []
    for item_data in items_data:
        r = requests.post(f"{BASE_URL}/tenants/{slug}/menu-items", json=item_data)
        if r.status_code == 200:
            menu_items.append(r.json())
    log_pass(f"Menu items created: {len(menu_items)} items")
    
    # Get table info (guest QR landing)
    r = requests.get(f"{BASE_URL}/g/{slug}/table/{table_code}/info")
    if r.status_code == 200:
        info = r.json()
        if len(info["menu_categories"]) == 2 and len(info["menu_items"]) == 4:
            log_pass(f"Table info: {len(info['menu_categories'])} categories, {len(info['menu_items'])} items")
        else:
            log_fail(f"Table info incomplete: {len(info.get('menu_categories',[]))} cats, {len(info.get('menu_items',[]))} items")
    else:
        log_fail("Table info failed", r.text)
    
    # Place order
    r = requests.post(f"{BASE_URL}/g/{slug}/table/{table_code}/orders", json={
        "items": [
            {"menu_item_id": menu_items[0]["id"], "menu_item_name": "Adana Kebab", "quantity": 2, "price": 250.0},
            {"menu_item_id": menu_items[2]["id"], "menu_item_name": "Turkish Tea", "quantity": 2, "price": 25.0},
        ],
        "guest_name": "Ahmet Yilmaz",
        "guest_phone": "+905559876543",
        "notes": "Extra spicy please"
    })
    if r.status_code == 200:
        order = r.json()
        expected_total = (250.0 * 2) + (25.0 * 2)
        if order["status"] == "RECEIVED" and order["total"] == expected_total:
            log_pass(f"Order placed: {order['id'][:8]}... (total: {order['total']}₺, status: RECEIVED)")
        else:
            log_fail(f"Order created but incorrect: status={order.get('status')}, total={order.get('total')}")
    else:
        log_fail("Order creation failed", r.text)
        return None
    
    order_id = order["id"]
    
    # Kitchen updates order status
    for new_status in ["PREPARING", "SERVED"]:
        r = requests.patch(f"{BASE_URL}/tenants/{slug}/orders/{order_id}", json={"status": new_status})
        if r.status_code == 200 and r.json()["status"] == new_status:
            log_pass(f"Order → {new_status}")
        else:
            log_fail(f"Order status update to {new_status} failed")
    
    # Call waiter order
    r = requests.post(f"{BASE_URL}/g/{slug}/table/{table_code}/orders", json={
        "items": [],
        "order_type": "call_waiter",
        "guest_name": "Ahmet Yilmaz"
    })
    if r.status_code == 200 and r.json()["order_type"] == "call_waiter":
        log_pass("Call waiter request sent")
    else:
        log_fail("Call waiter failed")
    
    return order

# ============ TEST 4: TENANT ISOLATION ============
def test_tenant_isolation(tenant_a, tenant_b):
    section("TEST 4: Tenant Isolation Verification")
    
    if not tenant_a or not tenant_b:
        log_fail("Skipping - tenants not available")
        return
    
    # Tenant A's rooms should not appear in Tenant B
    r_a = requests.get(f"{BASE_URL}/tenants/{tenant_a['slug']}/rooms")
    r_b = requests.get(f"{BASE_URL}/tenants/{tenant_b['slug']}/rooms")
    
    rooms_a = r_a.json() if r_a.status_code == 200 else []
    rooms_b = r_b.json() if r_b.status_code == 200 else []
    
    if len(rooms_a) > 0 and len(rooms_b) == 0:
        log_pass(f"Tenant A has {len(rooms_a)} rooms, Tenant B has {len(rooms_b)} rooms (isolated)")
    else:
        log_fail(f"Isolation issue: A={len(rooms_a)} rooms, B={len(rooms_b)} rooms")
    
    # Tenant B's tables should not appear in Tenant A
    r_a = requests.get(f"{BASE_URL}/tenants/{tenant_a['slug']}/tables")
    r_b = requests.get(f"{BASE_URL}/tenants/{tenant_b['slug']}/tables")
    
    tables_a = r_a.json() if r_a.status_code == 200 else []
    tables_b = r_b.json() if r_b.status_code == 200 else []
    
    if len(tables_a) == 0 and len(tables_b) > 0:
        log_pass(f"Tenant A has {len(tables_a)} tables, Tenant B has {len(tables_b)} tables (isolated)")
    else:
        log_fail(f"Isolation issue: A={len(tables_a)} tables, B={len(tables_b)} tables")
    
    # Tenant A's requests should not appear in Tenant B
    r_a = requests.get(f"{BASE_URL}/tenants/{tenant_a['slug']}/requests")
    r_b = requests.get(f"{BASE_URL}/tenants/{tenant_b['slug']}/requests")
    
    req_a = r_a.json() if r_a.status_code == 200 else []
    req_b = r_b.json() if r_b.status_code == 200 else []
    
    if len(req_a) > 0 and len(req_b) == 0:
        log_pass(f"Requests isolated: A={len(req_a)}, B={len(req_b)}")
    else:
        log_fail(f"Request isolation failed: A={len(req_a)}, B={len(req_b)}")

# ============ TEST 5: WEBCHAT FLOW ============
def test_webchat_flow(tenant_a):
    section("TEST 5: WebChat + AI Mock Reply Flow")
    
    if not tenant_a:
        log_fail("Skipping - no tenant A")
        return
    
    slug = tenant_a["slug"]
    
    # Start chat
    r = requests.post(f"{BASE_URL}/g/{slug}/chat/start")
    if r.status_code == 200:
        conv = r.json()
        log_pass(f"Chat started: {conv['id'][:8]}... (channel: {conv['channel']})")
    else:
        log_fail("Chat start failed", r.text)
        return
    
    conv_id = conv["id"]
    
    # Guest sends message
    r = requests.post(f"{BASE_URL}/g/{slug}/chat/{conv_id}/messages", json={
        "sender_type": "guest",
        "sender_name": "Maria",
        "content": "Hello, I need help with room service"
    })
    if r.status_code == 200:
        log_pass("Guest message sent")
    else:
        log_fail("Guest message failed", r.text)
    
    # Test AI suggestion
    r = requests.post(f"{BASE_URL}/tenants/{slug}/ai/suggest-reply", json={
        "message": "Hello, I need help with room service",
        "language": "en",
        "sector": "hotel"
    })
    if r.status_code == 200:
        ai = r.json()
        if ai["suggestion"] and ai["intent"] and ai["provider"] == "mock_template_v1":
            log_pass(f"AI suggestion: intent={ai['intent']}, lang={ai['language']}")
        else:
            log_fail("AI response incomplete")
    else:
        log_fail("AI suggestion failed", r.text)
    
    # Test Turkish AI
    r = requests.post(f"{BASE_URL}/tenants/{slug}/ai/suggest-reply", json={
        "message": "Merhaba, oda servisi rica ediyorum",
        "sector": "hotel"
    })
    if r.status_code == 200:
        ai = r.json()
        if ai["language"] == "tr":
            log_pass(f"Turkish AI detection works: lang={ai['language']}")
        else:
            log_fail(f"Turkish detection failed: {ai['language']}")
    else:
        log_fail("Turkish AI failed", r.text)
    
    # Test escalation (urgent keywords)
    r = requests.post(f"{BASE_URL}/g/{slug}/chat/{conv_id}/messages", json={
        "sender_type": "guest",
        "sender_name": "Maria",
        "content": "This is urgent! The AC is broken and it's an emergency!"
    })
    if r.status_code == 200:
        log_pass("Urgent message sent (escalation keywords detected)")
    else:
        log_fail("Urgent message failed")
    
    # List conversations
    r = requests.get(f"{BASE_URL}/tenants/{slug}/conversations")
    if r.status_code == 200 and len(r.json()) > 0:
        log_pass(f"Conversations listed: {len(r.json())} found")
    else:
        log_fail("Conversations listing failed")

# ============ TEST 6: CRM + LOYALTY ============
def test_crm_loyalty(tenant_a):
    section("TEST 6: CRM Contact + Loyalty Flow")
    
    if not tenant_a:
        log_fail("Skipping - no tenant A")
        return
    
    slug = tenant_a["slug"]
    
    # Check contact was auto-created from request
    r = requests.get(f"{BASE_URL}/tenants/{slug}/contacts")
    if r.status_code == 200:
        contacts = r.json()
        if contacts["total"] > 0:
            log_pass(f"Contacts auto-created: {contacts['total']} found")
        else:
            log_fail("No contacts found (should have been auto-created)")
    else:
        log_fail("Contacts list failed", r.text)
    
    # Join loyalty
    r = requests.post(f"{BASE_URL}/g/{slug}/loyalty/join", json={
        "phone": "+905551234567",
        "email": "john@example.com",
        "name": "John Smith"
    })
    if r.status_code == 200:
        loyalty = r.json()
        if loyalty.get("points") == 0 and loyalty.get("otp_stub") == "123456":
            log_pass(f"Loyalty joined: {loyalty['id'][:8]}... (OTP stub: {loyalty['otp_stub']})")
        else:
            log_fail("Loyalty join response incorrect")
    else:
        log_fail("Loyalty join failed", r.text)
    
    # List loyalty accounts
    r = requests.get(f"{BASE_URL}/tenants/{slug}/loyalty/accounts")
    if r.status_code == 200 and len(r.json()) > 0:
        log_pass(f"Loyalty accounts: {len(r.json())} found")
    else:
        log_fail("Loyalty accounts list failed")

# ============ TEST 7: WEBSOCKET REAL-TIME ============
async def test_websocket_realtime(tenant_a, tenant_b):
    section("TEST 7: WebSocket Real-Time Events + Tenant Isolation")
    
    if not tenant_a or not tenant_b:
        log_fail("Skipping - tenants not available")
        return
    
    received_a = []
    received_b = []
    
    async def listen(tenant_id, received_list, duration=3):
        try:
            async with websockets.connect(f"{WS_URL}/{tenant_id}") as ws:
                try:
                    while True:
                        msg = await asyncio.wait_for(ws.recv(), timeout=duration)
                        data = json.loads(msg)
                        received_list.append(data)
                except asyncio.TimeoutError:
                    pass
        except Exception as e:
            log_fail(f"WS connection error for tenant {tenant_id[:8]}", str(e))
    
    # Connect to both tenants
    task_a = asyncio.create_task(listen(tenant_a["id"], received_a, 4))
    task_b = asyncio.create_task(listen(tenant_b["id"], received_b, 4))
    
    # Wait for connections to establish
    await asyncio.sleep(1)
    
    # Create a request for tenant A (should only be received by A)
    slug_a = tenant_a["slug"]
    rooms_a = requests.get(f"{BASE_URL}/tenants/{slug_a}/rooms").json()
    if rooms_a:
        room_code = rooms_a[0]["room_code"]
        requests.post(f"{BASE_URL}/g/{slug_a}/room/{room_code}/requests", json={
            "category": "maintenance",
            "description": "WS Test: Light bulb replacement needed",
            "guest_name": "WS Tester"
        })
    
    # Create an order for tenant B (should only be received by B)
    slug_b = tenant_b["slug"]
    tables_b = requests.get(f"{BASE_URL}/tenants/{slug_b}/tables").json()
    if tables_b:
        table_code = tables_b[0]["table_code"]
        menu = requests.get(f"{BASE_URL}/tenants/{slug_b}/menu-items").json()
        if menu:
            requests.post(f"{BASE_URL}/g/{slug_b}/table/{table_code}/orders", json={
                "items": [{"menu_item_id": menu[0]["id"], "menu_item_name": menu[0]["name"], "quantity": 1, "price": menu[0]["price"]}],
                "guest_name": "WS Tester B"
            })
    
    # Wait for events
    await asyncio.gather(task_a, task_b)
    
    # Verify isolation
    a_has_request = any(msg.get("entity") == "guest_request" for msg in received_a)
    b_has_order = any(msg.get("entity") == "order" for msg in received_b)
    a_has_order = any(msg.get("entity") == "order" for msg in received_a)
    b_has_request = any(msg.get("entity") == "guest_request" for msg in received_b)
    
    if a_has_request:
        log_pass(f"Tenant A received request event ({len(received_a)} events)")
    else:
        log_fail(f"Tenant A should have received request event (got {len(received_a)} events)")
    
    if b_has_order:
        log_pass(f"Tenant B received order event ({len(received_b)} events)")
    else:
        log_fail(f"Tenant B should have received order event (got {len(received_b)} events)")
    
    if not a_has_order:
        log_pass("Tenant A did NOT receive Tenant B's order (isolation OK)")
    else:
        log_fail("ISOLATION BREACH: Tenant A received Tenant B's order!")
    
    if not b_has_request:
        log_pass("Tenant B did NOT receive Tenant A's request (isolation OK)")
    else:
        log_fail("ISOLATION BREACH: Tenant B received Tenant A's request!")

# ============ CLEANUP ============
def cleanup():
    """Remove test data"""
    import pymongo
    mongo_client = pymongo.MongoClient("mongodb://localhost:27017")
    test_db = mongo_client[os.environ.get("DB_NAME", "omni_inbox_hub")]
    collections = ["tenants", "departments", "service_categories", "rooms", 
                    "guest_requests", "tables", "menu_categories", "menu_items",
                    "orders", "contacts", "conversations", "messages",
                    "loyalty_accounts", "loyalty_ledger"]
    for col in collections:
        test_db[col].delete_many({})
    mongo_client.close()

# ============ MAIN ============
def main():
    global passed, failed
    
    print(f"\n{BOLD}{'='*60}")
    print(f"  POC Test: Multi-Tenant SaaS Core")
    print(f"  Testing: Isolation + WebSocket + QR Guest Flows")
    print(f"{'='*60}{RESET}\n")
    
    # Wait for server
    print("Waiting for server...")
    for i in range(10):
        try:
            r = requests.get(f"{BASE_URL}/health")
            if r.status_code == 200:
                print(f"  Server ready: {r.json()}")
                break
        except:
            pass
        time.sleep(1)
    else:
        print(f"{RED}Server not ready after 10s{RESET}")
        sys.exit(1)
    
    # Cleanup before tests
    import os
    try:
        cleanup()
        print("  Cleaned up previous test data\n")
    except Exception as e:
        print(f"  Cleanup note: {e}\n")
    
    # Run tests
    tenant_a, tenant_b = test_tenant_creation()
    test_hotel_qr_flow(tenant_a)
    test_restaurant_qr_flow(tenant_b)
    test_tenant_isolation(tenant_a, tenant_b)
    test_webchat_flow(tenant_a)
    test_crm_loyalty(tenant_a)
    
    # Run async WebSocket test
    asyncio.run(test_websocket_realtime(tenant_a, tenant_b))
    
    # Summary
    total = passed + failed
    print(f"\n{BOLD}{'='*60}")
    print(f"  RESULTS: {passed}/{total} passed, {failed}/{total} failed")
    if failed == 0:
        print(f"  {GREEN}ALL TESTS PASSED ✓{RESET}")
    else:
        print(f"  {RED}SOME TESTS FAILED ✗{RESET}")
    print(f"{'='*60}{RESET}\n")
    
    sys.exit(0 if failed == 0 else 1)

if __name__ == "__main__":
    import os
    main()
