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
                self.log(f"✅ {name} - Status: {response.status_code}")
                try:
                    return success, response.json() if response.text else {}
                except:
                    return success, {}
            else:
                self.log(f"❌ {name} - Expected {expected_status}, got {response.status_code}")
                try:
                    error_response = response.json() if response.text else {"detail": "No response body"}
                    self.log(f"   Response: {error_response}")
                except:
                    self.log(f"   Response: {response.text[:200]}")
                self.failed_tests.append(f"{name}: {response.status_code} (expected {expected_status})")
                return False, {}

        except Exception as e:
            self.log(f"❌ {name} - Error: {str(e)}")
            self.failed_tests.append(f"{name}: {str(e)}")
            return False, {}

    def test_health_and_root(self):
        """Test basic health endpoints"""
        self.log("\n=== HEALTH CHECK ===")
        self.run_test("API Root", "GET", "", 200)
        self.run_test("Health Check", "GET", "health", 200)

    def test_seeding(self):
        """Test data seeding"""
        self.log("\n=== DATA SEEDING ===")
        self.run_test("Seed Demo Data", "POST", "seed", 200)

    def test_auth(self):
        """Test authentication flow"""
        self.log("\n=== AUTHENTICATION ===")
        success, response = self.run_test(
            "Admin Login",
            "POST", 
            "auth/login",
            200,
            {"email": "admin@grandhotel.com", "password": "admin123"}
        )
        if success and 'token' in response:
            self.token = response['token']
            self.log(f"   Token acquired: {self.token[:20]}...")
            return True
        return False

    def test_tenant_management(self):
        """Test tenant operations"""
        self.log("\n=== TENANT MANAGEMENT ===")
        self.run_test("Get Tenant Info", "GET", f"tenants/{self.tenant_slug}", 200)
        self.run_test("List Tenants", "GET", "tenants", 200)

    def test_dashboard_stats(self):
        """Test enhanced dashboard statistics"""
        self.log("\n=== DASHBOARD STATS ===")
        success, stats = self.run_test("Dashboard Stats", "GET", f"tenants/{self.tenant_slug}/stats", 200)
        if success:
            required_keys = ['requests', 'orders', 'contacts', 'conversations', 'rooms', 'tables', 'avg_rating', 'usage', 'limits']
            missing_keys = [key for key in required_keys if key not in stats]
            if missing_keys:
                self.log(f"   ⚠️  Missing dashboard keys: {missing_keys}")
            else:
                self.log(f"   ✅ Dashboard has all required KPIs")

    def test_reviews_system(self):
        """Test reviews management and AI reply system"""
        self.log("\n=== REVIEWS SYSTEM ===")
        
        # Test review seeding
        self.run_test("Seed Review Stubs", "POST", f"tenants/{self.tenant_slug}/reviews/seed-stubs", 200)
        
        # Test getting reviews
        success, reviews_data = self.run_test("Get Reviews", "GET", f"tenants/{self.tenant_slug}/reviews", 200)
        if success and reviews_data.get('data'):
            reviews = reviews_data['data']
            self.log(f"   Found {len(reviews)} reviews")
            
            # Test review structure
            if reviews:
                review = reviews[0]
                required_fields = ['id', 'text', 'rating', 'author', 'sentiment', 'source']
                missing_fields = [f for f in required_fields if f not in review]
                if missing_fields:
                    self.log(f"   ⚠️  Missing review fields: {missing_fields}")
                else:
                    self.log(f"   ✅ Review structure is complete")
                    
                # Test AI reply suggestion
                self.run_test("AI Suggest Reply", "POST", f"tenants/{self.tenant_slug}/ai/suggest-reply", 200, 
                            {"message": review['text'], "language": "en", "sector": "hotel"})
                
                # Test reply to review
                if not review.get('replied'):
                    reply_success, _ = self.run_test("Reply to Review", "POST", 
                                                   f"tenants/{self.tenant_slug}/reviews/{review['id']}/reply", 
                                                   200, {"content": "Thank you for your feedback!"})

    def test_offers_and_payments(self):
        """Test offers creation and payment flow"""
        self.log("\n=== OFFERS & PAYMENTS ===")
        
        # Create offer
        offer_data = {
            "guest_name": "Test Guest",
            "guest_email": "test@example.com", 
            "guest_phone": "+905551234567",
            "room_type": "deluxe",
            "check_in": "2024-12-01",
            "check_out": "2024-12-03",
            "price": 500.0,
            "currency": "TRY",
            "notes": "Test offer",
            "created_by": "test-user-id"
        }
        
        success, offer = self.run_test("Create Offer", "POST", f"tenants/{self.tenant_slug}/offers", 201, offer_data)
        if success and offer.get('id'):
            offer_id = offer['id']
            self.log(f"   Created offer: {offer_id}")
            
            # Generate payment link
            link_success, link_response = self.run_test("Generate Payment Link", "POST", 
                                                      f"tenants/{self.tenant_slug}/offers/{offer_id}/generate-payment-link", 200)
            if link_success and link_response.get('payment_link_id'):
                link_id = link_response['payment_link_id']
                self.log(f"   Payment link ID: {link_id}")
                
                # Simulate payment
                self.run_test("Simulate Payment", "POST", f"payments/mock/succeed/{link_id}", 200)
                
                # Check reservations
                self.run_test("Get Reservations", "GET", f"tenants/{self.tenant_slug}/reservations", 200)

    def test_connectors(self):
        """Test connector framework"""
        self.log("\n=== CONNECTORS ===")
        success, connectors = self.run_test("Get Connectors", "GET", f"tenants/{self.tenant_slug}/connectors", 200)
        if success:
            connector_types = [c.get('type') for c in connectors]
            expected_types = ['WHATSAPP', 'INSTAGRAM', 'GOOGLE_REVIEWS', 'TRIPADVISOR', 'WEBCHAT']
            missing_types = [t for t in expected_types if t not in connector_types]
            if missing_types:
                self.log(f"   ⚠️  Missing connector types: {missing_types}")
            else:
                self.log(f"   ✅ All expected connectors present")

    def test_existing_functionality(self):
        """Test existing core functionality"""
        self.log("\n=== CORE FUNCTIONALITY ===")
        
        # Rooms
        self.run_test("Get Rooms", "GET", f"tenants/{self.tenant_slug}/rooms", 200)
        
        # Tables  
        self.run_test("Get Tables", "GET", f"tenants/{self.tenant_slug}/tables", 200)
        
        # Requests
        self.run_test("Get Requests", "GET", f"tenants/{self.tenant_slug}/requests", 200)
        
        # Orders
        self.run_test("Get Orders", "GET", f"tenants/{self.tenant_slug}/orders", 200)
        
        # Menu
        self.run_test("Get Menu Categories", "GET", f"tenants/{self.tenant_slug}/menu-categories", 200)
        self.run_test("Get Menu Items", "GET", f"tenants/{self.tenant_slug}/menu-items", 200)
        
        # Contacts
        self.run_test("Get Contacts", "GET", f"tenants/{self.tenant_slug}/contacts", 200)
        
        # Conversations (Inbox)
        self.run_test("Get Conversations", "GET", f"tenants/{self.tenant_slug}/conversations", 200)

    def test_guest_panels(self):
        """Test guest room and table panel access"""
        self.log("\n=== GUEST PANELS ===")
        
        # Test room info (guest access, no auth needed)
        self.run_test("Guest Room Info", "GET", f"g/{self.tenant_slug}/room/R101/info", 200, headers={})
        
        # Test table info (guest access, no auth needed)  
        self.run_test("Guest Table Info", "GET", f"g/{self.tenant_slug}/table/T1/info", 200, headers={})

    def test_guest_request_creation(self):
        """Test guest request creation flow"""
        self.log("\n=== GUEST REQUEST FLOW ===")
        request_data = {
            "category": "housekeeping",
            "description": "Test request from API test",
            "priority": "normal",
            "guest_name": "API Test Guest",
            "guest_phone": "+905551111111"
        }
        self.run_test("Create Guest Request", "POST", f"g/{self.tenant_slug}/room/R101/requests", 200, request_data, headers={})

    def test_guest_order_creation(self):
        """Test guest order creation flow"""
        self.log("\n=== GUEST ORDER FLOW ===")
        order_data = {
            "items": [
                {
                    "menu_item_id": "test-item-id",
                    "menu_item_name": "Test Item", 
                    "quantity": 2,
                    "price": 50.0,
                    "notes": "Test order from API"
                }
            ],
            "guest_name": "API Test Guest",
            "guest_phone": "+905551111111",
            "order_type": "dine_in"
        }
        self.run_test("Create Guest Order", "POST", f"g/{self.tenant_slug}/table/T1/orders", 200, order_data, headers={})

    def run_all_tests(self):
        """Run all test suites"""
        self.log("🚀 Starting Comprehensive API Testing for Multi-tenant SaaS Platform")
        self.log("=" * 80)
        
        # Test sequence
        test_methods = [
            self.test_health_and_root,
            self.test_seeding,
            self.test_auth,
            self.test_tenant_management, 
            self.test_dashboard_stats,
            self.test_reviews_system,
            self.test_offers_and_payments,
            self.test_connectors,
            self.test_existing_functionality,
            self.test_guest_panels,
            self.test_guest_request_creation,
            self.test_guest_order_creation,
        ]
        
        # Run all tests
        for test_method in test_methods:
            try:
                test_method()
            except Exception as e:
                self.log(f"\n❌ Test section failed: {str(e)}")
                self.failed_tests.append(f"Test section error: {str(e)}")
        
        # Print results
        self.log(f"\n" + "=" * 80)
        self.log(f"📊 TEST RESULTS")
        self.log(f"📊 Tests passed: {self.tests_passed}/{self.tests_run}")
        self.log(f"📊 Success rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "No tests run")
        
        if self.failed_tests:
            self.log(f"\n❌ FAILED TESTS:")
            for failed in self.failed_tests:
                self.log(f"   • {failed}")
        else:
            self.log(f"\n✅ ALL TESTS PASSED!")
        
        return self.tests_passed == self.tests_run

def main():
    tester = ComprehensiveAPITester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())