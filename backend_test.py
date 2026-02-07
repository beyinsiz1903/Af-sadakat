import requests
import sys
import json
from datetime import datetime

class ComprehensiveAPITester:
    def __init__(self):
        self.base_url = "https://omni-inbox-hub.preview.emergentagent.com/api"
        self.token = None
        self.tenant_slug = "grand-hotel"
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []

    def log(self, message):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        self.log(f"🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PATCH':
                response = requests.patch(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json() if response.text else {}
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_response = response.json() if response.text else {"detail": "No response body"}
                    print(f"   Response: {error_response}")
                except:
                    print(f"   Response: {response.text[:200]}")
                self.failed_tests.append(f"{name}: {response.status_code} (expected {expected_status})")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            self.failed_tests.append(f"{name}: {str(e)}")
            return False, {}
            if success:
                self.tests_passed += 1
                self.log(f"✅ {name} - Status: {response.status_code}")
                return True, response.json() if response.content else {}
            else:
                self.log(f"❌ {name} - Expected {expected_status}, got {response.status_code}")
                if response.content:
                    try:
                        error_detail = response.json()
                        self.log(f"   Error: {error_detail}")
                    except:
                        self.log(f"   Response: {response.text[:200]}...")
                return False, {}

        except Exception as e:
            self.log(f"❌ {name} - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test API health"""
        return self.run_test("Health Check", "GET", "/health", 200)

    def test_seed_data(self):
        """Test seeding demo data"""
        success, response = self.run_test("Seed Demo Data", "POST", "/seed", 200)
        if success:
            self.log(f"   Demo tenant: {response.get('tenant_slug', 'grand-hotel')}")
            self.tenant_slug = "grand-hotel"
        return success

    def test_login(self):
        """Test login with demo credentials"""
        success, response = self.run_test(
            "Login with Demo Credentials",
            "POST",
            "/auth/login",
            200,
            data={"email": "admin@grandhotel.com", "password": "admin123"}
        )
        if success and 'token' in response:
            self.token = response['token']
            self.user_data = response.get('user', {})
            self.log(f"   Logged in as: {self.user_data.get('name', 'Unknown')}")
            return True
        return False

    def test_dashboard_stats(self):
        """Test dashboard statistics endpoint"""
        if not self.tenant_slug:
            return False
        return self.run_test("Dashboard Stats", "GET", f"/tenants/{self.tenant_slug}/stats", 200)[0]

    def test_requests_flow(self):
        """Test guest request management flow"""
        if not self.tenant_slug:
            return False
        
        # List all requests
        success, response = self.run_test("List All Requests", "GET", f"/tenants/{self.tenant_slug}/requests", 200)
        if not success:
            return False
        
        requests_list = response.get('data', [])
        self.log(f"   Found {len(requests_list)} existing requests")
        
        if requests_list:
            # Test updating first request status
            request_id = requests_list[0]['id']
            self.created_request_id = request_id
            return self.run_test(
                "Update Request Status", 
                "PATCH", 
                f"/tenants/{self.tenant_slug}/requests/{request_id}",
                200,
                data={"status": "IN_PROGRESS", "notes": "Testing status update"}
            )[0]
        
        return True

    def test_orders_flow(self):
        """Test order management flow"""
        if not self.tenant_slug:
            return False
        
        # List all orders
        success, response = self.run_test("List All Orders", "GET", f"/tenants/{self.tenant_slug}/orders", 200)
        if not success:
            return False
        
        orders_list = response.get('data', [])
        self.log(f"   Found {len(orders_list)} existing orders")
        
        if orders_list:
            # Test updating first order status
            order_id = orders_list[0]['id']
            self.created_order_id = order_id
            return self.run_test(
                "Update Order Status",
                "PATCH",
                f"/tenants/{self.tenant_slug}/orders/{order_id}",
                200,
                data={"status": "PREPARING"}
            )[0]
        
        return True

    def test_rooms_management(self):
        """Test room management"""
        if not self.tenant_slug:
            return False
        
        # List rooms
        success, response = self.run_test("List Rooms", "GET", f"/tenants/{self.tenant_slug}/rooms", 200)
        if not success:
            return False
        
        rooms = response
        self.log(f"   Found {len(rooms)} rooms")
        return len(rooms) > 0

    def test_tables_management(self):
        """Test table management"""
        if not self.tenant_slug:
            return False
        
        # List tables
        success, response = self.run_test("List Tables", "GET", f"/tenants/{self.tenant_slug}/tables", 200)
        if not success:
            return False
        
        tables = response
        self.log(f"   Found {len(tables)} tables")
        return len(tables) > 0

    def test_menu_management(self):
        """Test menu management"""
        if not self.tenant_slug:
            return False
        
        # List menu categories
        success, response = self.run_test("List Menu Categories", "GET", f"/tenants/{self.tenant_slug}/menu-categories", 200)
        if not success:
            return False
        
        categories = response
        self.log(f"   Found {len(categories)} menu categories")
        
        # List menu items
        success, response = self.run_test("List Menu Items", "GET", f"/tenants/{self.tenant_slug}/menu-items", 200)
        if not success:
            return False
        
        items = response
        self.log(f"   Found {len(items)} menu items")
        return len(categories) > 0 and len(items) > 0

    def test_contacts_management(self):
        """Test contacts/CRM management"""
        if not self.tenant_slug:
            return False
        
        # List contacts with search
        success, response = self.run_test("List Contacts", "GET", f"/tenants/{self.tenant_slug}/contacts", 200)
        if not success:
            return False
        
        contacts = response.get('data', [])
        self.log(f"   Found {len(contacts)} contacts")
        
        # Test search functionality
        success, response = self.run_test(
            "Search Contacts", 
            "GET", 
            f"/tenants/{self.tenant_slug}/contacts?search=john", 
            200
        )
        if success:
            search_results = response.get('data', [])
            self.log(f"   Search returned {len(search_results)} results")
        
        return success

    def test_conversations_management(self):
        """Test inbox/conversations management"""
        if not self.tenant_slug:
            return False
        
        # List conversations
        success, response = self.run_test("List Conversations", "GET", f"/tenants/{self.tenant_slug}/conversations", 200)
        if not success:
            return False
        
        conversations = response
        self.log(f"   Found {len(conversations)} conversations")
        return True

    def test_guest_room_panel(self):
        """Test guest room panel (no auth required)"""
        if not self.tenant_slug:
            return False
        
        # Test room info
        temp_token = self.token
        self.token = None  # Remove auth for guest endpoints
        
        success, response = self.run_test("Guest Room Info", "GET", f"/g/{self.tenant_slug}/room/R101/info", 200)
        
        if success:
            room_info = response.get('room', {})
            categories = response.get('service_categories', [])
            self.log(f"   Room {room_info.get('room_number', 'Unknown')} with {len(categories)} service categories")
            
            # Test creating a guest request
            success, request_response = self.run_test(
                "Create Guest Request",
                "POST",
                f"/g/{self.tenant_slug}/room/R101/requests",
                200,
                data={
                    "category": "housekeeping",
                    "description": "Test request from automated testing",
                    "priority": "normal",
                    "guest_name": "Test Guest",
                    "guest_phone": "+905551234567"
                }
            )
            
            if success:
                self.log(f"   Created request ID: {request_response.get('id', 'Unknown')}")
        
        self.token = temp_token  # Restore auth
        return success

    def test_guest_table_panel(self):
        """Test guest table panel (no auth required)"""
        if not self.tenant_slug:
            return False
        
        # Test table info
        temp_token = self.token
        self.token = None  # Remove auth for guest endpoints
        
        success, response = self.run_test("Guest Table Info", "GET", f"/g/{self.tenant_slug}/table/T1/info", 200)
        
        if success:
            table_info = response.get('table', {})
            menu_items = response.get('menu_items', [])
            self.log(f"   Table {table_info.get('table_number', 'Unknown')} with {len(menu_items)} menu items")
            
            # Test creating an order (simplified)
            if menu_items:
                item = menu_items[0]
                success, order_response = self.run_test(
                    "Create Guest Order",
                    "POST",
                    f"/g/{self.tenant_slug}/table/T1/orders",
                    200,
                    data={
                        "items": [
                            {
                                "menu_item_id": item['id'],
                                "menu_item_name": item['name'],
                                "quantity": 1,
                                "price": item['price']
                            }
                        ],
                        "guest_name": "Test Guest",
                        "guest_phone": "+905551234567",
                        "order_type": "dine_in"
                    }
                )
                
                if success:
                    self.log(f"   Created order ID: {order_response.get('id', 'Unknown')}")
        
        self.token = temp_token  # Restore auth
        return success

    def test_guest_chat(self):
        """Test guest chat functionality (no auth required)"""
        if not self.tenant_slug:
            return False
        
        temp_token = self.token
        self.token = None  # Remove auth for guest endpoints
        
        # Start chat
        success, response = self.run_test("Start Guest Chat", "POST", f"/g/{self.tenant_slug}/chat/start", 200)
        
        if success:
            conversation_id = response.get('id')
            self.conversation_id = conversation_id
            self.log(f"   Started chat: {conversation_id}")
            
            # Send a message
            success, msg_response = self.run_test(
                "Send Chat Message",
                "POST",
                f"/g/{self.tenant_slug}/chat/{conversation_id}/messages",
                200,
                data={
                    "content": "Hello, I need help with my room",
                    "sender_type": "guest",
                    "sender_name": "Test Guest"
                }
            )
            
            if success:
                self.log(f"   Sent message ID: {msg_response.get('id', 'Unknown')}")
                
                # Get messages
                success, messages = self.run_test(
                    "Get Chat Messages",
                    "GET",
                    f"/g/{self.tenant_slug}/chat/{conversation_id}/messages",
                    200
                )
                
                if success:
                    self.log(f"   Retrieved {len(messages)} messages")
        
        self.token = temp_token  # Restore auth
        return success

    def test_ai_mock_provider(self):
        """Test AI suggestion mock provider"""
        if not self.tenant_slug:
            return False
        
        success, response = self.run_test(
            "AI Suggest Reply",
            "POST",
            f"/tenants/{self.tenant_slug}/ai/suggest-reply",
            200,
            data={
                "message": "Hello, I need help with my room",
                "language": "en",
                "sector": "hotel"
            }
        )
        
        if success:
            suggestion = response.get('suggestion', '')
            provider = response.get('provider', '')
            self.log(f"   AI Provider: {provider}")
            self.log(f"   Suggestion: {suggestion[:50]}...")
        
        return success

    def run_all_tests(self):
        """Run comprehensive backend API tests"""
        self.log("🚀 Starting Tourism Platform Backend Tests")
        self.log(f"📍 Base URL: {self.base_url}")
        
        # Core API tests
        tests = [
            ("Health Check", self.test_health_check),
            ("Seed Demo Data", self.test_seed_data),
            ("Login Flow", self.test_login),
            ("Dashboard Stats", self.test_dashboard_stats),
            ("Requests Management", self.test_requests_flow),
            ("Orders Management", self.test_orders_flow),
            ("Rooms Management", self.test_rooms_management),
            ("Tables Management", self.test_tables_management),
            ("Menu Management", self.test_menu_management),
            ("Contacts Management", self.test_contacts_management),
            ("Conversations Management", self.test_conversations_management),
            ("Guest Room Panel", self.test_guest_room_panel),
            ("Guest Table Panel", self.test_guest_table_panel),
            ("Guest Chat", self.test_guest_chat),
            ("AI Mock Provider", self.test_ai_mock_provider),
        ]
        
        failed_tests = []
        
        for test_name, test_func in tests:
            try:
                if not test_func():
                    failed_tests.append(test_name)
            except Exception as e:
                self.log(f"❌ {test_name} - Exception: {str(e)}")
                failed_tests.append(test_name)
        
        # Print results
        self.log("\n" + "="*60)
        self.log(f"📊 BACKEND TEST RESULTS")
        self.log(f"📍 Tests Run: {self.tests_run}")
        self.log(f"✅ Tests Passed: {self.tests_passed}")
        self.log(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        
        if failed_tests:
            self.log(f"\n❌ Failed Tests:")
            for test in failed_tests:
                self.log(f"   - {test}")
        else:
            self.log(f"\n🎉 All backend tests passed!")
        
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        self.log(f"📈 Success Rate: {success_rate:.1f}%")
        
        return self.tests_run - self.tests_passed == 0

def main():
    tester = TourismPlatformTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())