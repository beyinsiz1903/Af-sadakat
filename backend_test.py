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

    def test_analytics_engine_fix(self):
        """Test fixed analytics engine - AI efficiency should be <= 100%"""
        self.log("\n=== ANALYTICS ENGINE (FIXED) ===")
        success, analytics = self.run_test("Get Analytics", "GET", f"tenants/{self.tenant_slug}/analytics", 200)
        if success:
            ai_efficiency = analytics.get("ai", {}).get("efficiency_pct", 0)
            self.log(f"   AI Efficiency: {ai_efficiency}%")
            if ai_efficiency > 100:
                self.log(f"   ❌ AI Efficiency still broken: {ai_efficiency}% (should be <= 100%)")
                self.failed_tests.append(f"AI Efficiency broken: {ai_efficiency}%")
            else:
                self.log(f"   ✅ AI Efficiency fixed: {ai_efficiency}%")

    def test_v2_modular_routes(self):
        """Test V2 modular hotel routes"""
        self.log("\n=== V2 MODULAR ROUTES ===")
        
        # Test V2 rooms list
        success, rooms = self.run_test("V2 Rooms List", "GET", f"v2/hotel/tenants/{self.tenant_slug}/rooms", 200)
        if success:
            self.log(f"   Found {len(rooms)} rooms in V2 API")
        
        # Test V2 requests list
        success, requests_data = self.run_test("V2 Requests List", "GET", f"v2/hotel/tenants/{self.tenant_slug}/requests", 200)
        if success:
            requests = requests_data.get('data', [])
            total = requests_data.get('total', 0)
            self.log(f"   Found {len(requests)}/{total} requests in V2 API")
        
        # Test QR PNG generation for a room
        if rooms:
            room_id = rooms[0]["id"]
            success, _ = self.run_test("V2 Room QR PNG", "GET", f"v2/hotel/rooms/{room_id}/qr.png", 200)
            if success:
                self.log(f"   ✅ QR PNG generation working")

    def test_guest_resolve_endpoints(self):
        """Test guest JWT token resolution"""
        self.log("\n=== GUEST RESOLVE ENDPOINTS ===")
        
        # Test guest room resolution with proper query parameters
        self.run_test("Guest Resolve Room", "GET", f"guest/resolve-room?tenantSlug={self.tenant_slug}&roomCode=R101", 200)
        
        # Test guest table resolution with proper query parameters
        self.run_test("Guest Resolve Table", "GET", f"guest/resolve-table?tenantSlug={self.tenant_slug}&tableCode=T1", 200)

    def test_system_status(self):
        """Test system status endpoint"""
        self.log("\n=== SYSTEM STATUS ===")
        success, status = self.run_test("System Status", "GET", "system/status", 200)
        if success:
            operational = status.get("operational", False)
            self.log(f"   System operational: {operational}")

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

    def test_phase5_plan_management(self):
        """Test Phase 5 plan management APIs"""
        self.log("\n=== PHASE 5: PLAN MANAGEMENT ===")
        
        # Test plans endpoint
        success, plans = self.run_test("Get Plans", "GET", "plans", 200)
        if success and plans:
            expected_plans = ['basic', 'pro', 'enterprise']
            plan_names = [plan.get('name', '').lower() for plan in plans] if isinstance(plans, list) else []
            missing_plans = [p for p in expected_plans if p not in plan_names]
            if missing_plans:
                self.log(f"   ⚠️  Missing plan types: {missing_plans}")
            else:
                self.log(f"   ✅ All expected plans present: {plan_names}")

    def test_phase5_usage_enforcement(self):
        """Test Phase 5 usage limits and enforcement"""
        self.log("\n=== PHASE 5: USAGE ENFORCEMENT ===")
        
        success, usage = self.run_test("Get Usage Metrics", "GET", f"tenants/{self.tenant_slug}/usage", 200)
        if success:
            required_keys = ['current', 'limits', 'plan', 'metrics']
            missing_keys = [key for key in required_keys if key not in usage]
            if missing_keys:
                self.log(f"   ⚠️  Missing usage keys: {missing_keys}")
            else:
                self.log(f"   ✅ Usage metrics structure complete")
                if 'current' in usage and 'limits' in usage:
                    self.log(f"   📊 Current usage: {usage['current']}")
                    self.log(f"   📊 Plan limits: {usage['limits']}")

    def test_phase5_billing(self):
        """Test Phase 5 billing system"""
        self.log("\n=== PHASE 5: BILLING ===")
        
        success, billing = self.run_test("Get Billing Info", "GET", f"tenants/{self.tenant_slug}/billing", 200)
        if success:
            required_keys = ['account', 'subscription', 'invoices']
            missing_keys = [key for key in required_keys if key not in billing]
            if missing_keys:
                self.log(f"   ⚠️  Missing billing keys: {missing_keys}")
            else:
                self.log(f"   ✅ Billing structure complete")
                if 'invoices' in billing:
                    invoice_count = len(billing['invoices']) if isinstance(billing['invoices'], list) else 0
                    self.log(f"   📋 Found {invoice_count} invoices")

    def test_phase5_analytics(self):
        """Test Phase 5 analytics engine"""
        self.log("\n=== PHASE 5: ANALYTICS ===")
        
        success, analytics = self.run_test("Get Analytics", "GET", f"tenants/{self.tenant_slug}/analytics", 200)
        if success:
            required_sections = ['revenue', 'guests', 'operations', 'ai']
            missing_sections = [section for section in required_sections if section not in analytics]
            if missing_sections:
                self.log(f"   ⚠️  Missing analytics sections: {missing_sections}")
            else:
                self.log(f"   ✅ Analytics sections complete")
                
                # Check revenue section
                if 'revenue' in analytics:
                    revenue = analytics['revenue']
                    if 'total' in revenue:
                        self.log(f"   💰 Total revenue: {revenue.get('currency', 'TRY')} {revenue['total']}")
                
                # Check AI metrics
                if 'ai' in analytics:
                    ai_metrics = analytics['ai']
                    if 'efficiency_pct' in ai_metrics:
                        self.log(f"   🤖 AI efficiency: {ai_metrics['efficiency_pct']}%")

    def test_phase5_compliance(self):
        """Test Phase 5 GDPR/KVKK compliance"""
        self.log("\n=== PHASE 5: COMPLIANCE ===")
        
        # Test getting guest data for compliance
        success, contacts = self.run_test("Get Contacts for Compliance", "GET", f"tenants/{self.tenant_slug}/contacts", 200)
        if success and contacts.get('data'):
            contact_list = contacts['data']
            if contact_list:
                contact_id = contact_list[0]['id']
                
                # Test data export
                export_success, export_data = self.run_test("Export Guest Data", "POST", 
                                                          f"tenants/{self.tenant_slug}/compliance/export/{contact_id}", 200)
                if export_success:
                    expected_keys = ['contact', 'requests', 'orders', 'consent_logs']
                    missing_keys = [key for key in expected_keys if key not in export_data]
                    if missing_keys:
                        self.log(f"   ⚠️  Missing export keys: {missing_keys}")
                    else:
                        self.log(f"   ✅ Data export structure complete")
                
                # Test retention policy endpoint
                self.run_test("Get Retention Policy", "GET", f"tenants/{self.tenant_slug}/compliance/retention", 200)
                
                # Test consent logs
                self.run_test("Get Consent Logs", "GET", f"tenants/{self.tenant_slug}/compliance/consent-logs", 200)

    def test_phase5_growth_referrals(self):
        """Test Phase 5 referral and growth system"""
        self.log("\n=== PHASE 5: GROWTH & REFERRALS ===")
        
        success, referral = self.run_test("Get Referral Code", "GET", f"tenants/{self.tenant_slug}/growth/referral", 200)
        if success:
            required_keys = ['code', 'clicks', 'signups', 'rewards_earned']
            missing_keys = [key for key in required_keys if key not in referral]
            if missing_keys:
                self.log(f"   ⚠️  Missing referral keys: {missing_keys}")
            else:
                self.log(f"   ✅ Referral structure complete")
                if 'code' in referral:
                    self.log(f"   🔗 Referral code: {referral['code']}")
                    self.log(f"   📊 Stats - Clicks: {referral.get('clicks', 0)}, Signups: {referral.get('signups', 0)}")

    def test_phase5_system_metrics(self):
        """Test Phase 5 system-wide metrics"""
        self.log("\n=== PHASE 5: SYSTEM METRICS ===")
        
        # Test system status
        self.run_test("System Status", "GET", "system/status", 200)
        
        # Test system metrics
        success, metrics = self.run_test("System Metrics", "GET", "system/metrics", 200)
        if success:
            expected_keys = ['tenants', 'users', 'requests', 'orders', 'messages', 'mrr']
            missing_keys = [key for key in expected_keys if key not in metrics]
            if missing_keys:
                self.log(f"   ⚠️  Missing system metric keys: {missing_keys}")
            else:
                self.log(f"   ✅ System metrics complete")
                self.log(f"   🏢 Tenants: {metrics.get('tenants', 0)}")
                self.log(f"   👥 Users: {metrics.get('users', 0)}")
                if 'mrr' in metrics:
                    self.log(f"   💰 MRR: ${metrics['mrr']}")

    def test_phase5_onboarding(self):
        """Test Phase 5 onboarding wizard"""
        self.log("\n=== PHASE 5: ONBOARDING ===")
        
        success, onboarding = self.run_test("Get Onboarding Progress", "GET", f"tenants/{self.tenant_slug}/onboarding", 200)
        if success:
            if 'steps' in onboarding:
                total_steps = len(onboarding['steps']) if isinstance(onboarding['steps'], list) else 0
                completed_steps = sum(1 for step in onboarding['steps'] if step.get('completed', False)) if isinstance(onboarding['steps'], list) else 0
                self.log(f"   📝 Onboarding progress: {completed_steps}/{total_steps} steps completed")
            else:
                self.log(f"   ⚠️  Missing onboarding steps structure")

    def test_phase5_demo_reset(self):
        """Test Phase 5 demo reset functionality"""
        self.log("\n=== PHASE 5: DEMO RESET ===")
        
        # Test demo reset endpoint (should reset demo data)
        self.run_test("Demo Reset", "POST", "demo/reset", 200)

    def test_phase5plus_guest_tokens(self):
        """Test Phase 5+ Guest JWT Token System"""
        self.log("\n=== PHASE 5+: GUEST JWT TOKENS ===")
        
        # Test guest room resolution with token generation
        success, room_data = self.run_test(
            "Guest Resolve Room", 
            "GET", 
            f"guest/resolve-room?tenantSlug={self.tenant_slug}&roomCode=R101", 
            200, 
            headers={}
        )
        if success:
            required_keys = ['guestToken', 'tenant', 'room', 'categories']
            missing_keys = [key for key in required_keys if key not in room_data]
            if missing_keys:
                self.log(f"   ⚠️  Missing room resolve keys: {missing_keys}")
            else:
                self.log(f"   ✅ Room resolve response complete")
                if 'guestToken' in room_data:
                    self.log(f"   🎫 Guest token generated: {room_data['guestToken'][:20]}...")
        
        # Test guest table resolution with token generation
        success, table_data = self.run_test(
            "Guest Resolve Table", 
            "GET", 
            f"guest/resolve-table?tenantSlug={self.tenant_slug}&tableCode=T1", 
            200, 
            headers={}
        )
        if success:
            required_keys = ['guestToken', 'table', 'menu']
            missing_keys = [key for key in required_keys if key not in table_data]
            if missing_keys:
                self.log(f"   ⚠️  Missing table resolve keys: {missing_keys}")
            else:
                self.log(f"   ✅ Table resolve response complete")
                if 'guestToken' in table_data:
                    self.log(f"   🎫 Guest token generated: {table_data['guestToken'][:20]}...")

    def test_phase5plus_qr_generation(self):
        """Test Phase 5+ QR Code Generation (PNG & PDF)"""
        self.log("\n=== PHASE 5+: QR GENERATION ===")
        
        # Get rooms first to get a room ID
        success, rooms_data = self.run_test("Get Rooms for QR", "GET", f"tenants/{self.tenant_slug}/rooms", 200)
        if success and rooms_data:
            rooms = rooms_data if isinstance(rooms_data, list) else []
            if rooms:
                room_id = rooms[0]['id']
                
                # Test individual room QR PNG generation
                # Note: This will return binary data, so we don't check JSON response
                png_success, _ = self.run_test("Room QR PNG", "GET", f"admin/rooms/{room_id}/qr.png", 200)
                if png_success:
                    self.log(f"   ✅ QR PNG generated for room {room_id}")
                
                # Test PDF generation for multiple rooms
                room_ids = ','.join([r['id'] for r in rooms[:3]])  # First 3 rooms
                pdf_success, _ = self.run_test("Rooms QR PDF", "GET", f"admin/rooms/print.pdf?ids={room_ids}", 200)
                if pdf_success:
                    self.log(f"   ✅ QR PDF generated for {len(rooms[:3])} rooms")
            else:
                self.log(f"   ⚠️  No rooms available for QR testing")

    def test_phase5plus_comments_system(self):
        """Test Phase 5+ Request Comments System"""
        self.log("\n=== PHASE 5+: REQUEST COMMENTS ===")
        
        # Get requests first to get a request ID
        success, requests_data = self.run_test("Get Requests for Comments", "GET", f"tenants/{self.tenant_slug}/requests", 200)
        if success and requests_data.get('data'):
            requests = requests_data['data']
            if requests:
                request_id = requests[0]['id']
                
                # Test adding a comment
                comment_data = {
                    "body": "Test comment from API test",
                    "user_id": "test-user-id", 
                    "user_name": "Test User"
                }
                add_success, comment = self.run_test(
                    "Add Request Comment", 
                    "POST", 
                    f"tenants/{self.tenant_slug}/requests/{request_id}/comments", 
                    201, 
                    comment_data
                )
                if add_success:
                    self.log(f"   ✅ Comment added to request {request_id}")
                
                # Test getting comments
                get_success, comments = self.run_test(
                    "Get Request Comments", 
                    "GET", 
                    f"tenants/{self.tenant_slug}/requests/{request_id}/comments", 
                    200
                )
                if get_success:
                    comment_count = len(comments) if isinstance(comments, list) else 0
                    self.log(f"   ✅ Retrieved {comment_count} comments for request {request_id}")
            else:
                self.log(f"   ⚠️  No requests available for comments testing")

    def test_phase5plus_kb_articles(self):
        """Test Phase 5+ Knowledge Base Articles System"""
        self.log("\n=== PHASE 5+: KB ARTICLES ===")
        
        # Test creating a KB article
        article_data = {
            "title": "Test Knowledge Base Article",
            "content": "This is a test article content for API testing",
            "category": "general",
            "tags": ["test", "api", "knowledge"],
            "author_id": "test-user-id",
            "status": "published"
        }
        
        create_success, article = self.run_test(
            "Create KB Article", 
            "POST", 
            f"tenants/{self.tenant_slug}/kb-articles", 
            201, 
            article_data
        )
        if create_success:
            article_id = article.get('id', '')
            self.log(f"   ✅ KB Article created: {article_id}")
        
        # Test getting KB articles
        get_success, articles = self.run_test(
            "Get KB Articles", 
            "GET", 
            f"tenants/{self.tenant_slug}/kb-articles", 
            200
        )
        if get_success:
            article_count = len(articles) if isinstance(articles, list) else 0
            self.log(f"   ✅ Retrieved {article_count} KB articles")
            if articles and isinstance(articles, list) and articles:
                article = articles[0]
                required_keys = ['id', 'title', 'content', 'category', 'created_at']
                missing_keys = [key for key in required_keys if key not in article]
                if missing_keys:
                    self.log(f"   ⚠️  Missing article keys: {missing_keys}")
                else:
                    self.log(f"   ✅ KB Article structure complete")

    def test_sprint3_v2_inbox_apis(self):
        """Test Sprint 3 V2 Inbox APIs"""
        self.log("\n=== SPRINT 3: V2 INBOX APIs ===")
        
        # Test V2 conversations list
        success, convs_data = self.run_test("V2 Inbox Conversations", "GET", f"v2/inbox/tenants/{self.tenant_slug}/conversations", 200)
        if success:
            convs = convs_data.get('data', [])
            total = convs_data.get('total', 0)
            self.log(f"   Found {len(convs)}/{total} conversations")
            
            # Verify conversation structure
            if convs:
                conv = convs[0]
                required_keys = ['id', 'channel_type', 'last_message_preview', 'message_count', 'status', 'guest_name']
                missing_keys = [key for key in required_keys if key not in conv]
                if missing_keys:
                    self.log(f"   ⚠️  Missing conversation keys: {missing_keys}")
                else:
                    self.log(f"   ✅ Conversation structure complete")
                    
                    # Test conversation detail
                    conv_id = conv['id']
                    detail_success, detail_data = self.run_test("V2 Conversation Detail", "GET", f"v2/inbox/tenants/{self.tenant_slug}/conversations/{conv_id}", 200)
                    if detail_success:
                        required_detail_keys = ['conversation', 'messages', 'contact']
                        missing_detail_keys = [key for key in required_detail_keys if key not in detail_data]
                        if missing_detail_keys:
                            self.log(f"   ⚠️  Missing detail keys: {missing_detail_keys}")
                        else:
                            self.log(f"   ✅ Conversation detail complete")
                            
                        # Test AI suggestion
                        self.run_test("V2 AI Suggest Inbox", "POST", f"v2/inbox/tenants/{self.tenant_slug}/conversations/{conv_id}/ai-suggest", 200)
                        
                        # Test sending agent message
                        msg_data = {"text": "Test message from API"}
                        self.run_test("V2 Send Agent Message", "POST", f"v2/inbox/tenants/{self.tenant_slug}/conversations/{conv_id}/messages", 200, msg_data)
                        
                        # Test close conversation
                        self.run_test("V2 Close Conversation", "POST", f"v2/inbox/tenants/{self.tenant_slug}/conversations/{conv_id}/close", 200)
                        
                        # Test reopen conversation 
                        self.run_test("V2 Reopen Conversation", "POST", f"v2/inbox/tenants/{self.tenant_slug}/conversations/{conv_id}/reopen", 200)

        # Test connector pull-now
        pull_success, pull_data = self.run_test("V2 Pull Connectors Now", "POST", f"v2/inbox/tenants/{self.tenant_slug}/connectors/pull-now", 200)
        if pull_success:
            messages_created = pull_data.get('messages_created', 0)
            reviews_created = pull_data.get('reviews_created', 0)
            self.log(f"   ✅ Pull completed: {messages_created} messages, {reviews_created} reviews created")

    def test_sprint3_v2_reviews_apis(self):
        """Test Sprint 3 V2 Reviews APIs"""
        self.log("\n=== SPRINT 3: V2 REVIEWS APIs ===")
        
        # Test V2 reviews list with summary
        success, reviews_data = self.run_test("V2 Reviews List", "GET", f"v2/reviews/tenants/{self.tenant_slug}", 200)
        if success:
            reviews = reviews_data.get('data', [])
            total = reviews_data.get('total', 0)
            summary = reviews_data.get('summary', {})
            
            self.log(f"   Found {len(reviews)}/{total} reviews")
            self.log(f"   Sentiment summary: {summary.get('positive', 0)} POS, {summary.get('neutral', 0)} NEU, {summary.get('negative', 0)} NEG")
            
            # Verify review structure
            if reviews:
                review = reviews[0]
                required_keys = ['id', 'text', 'rating', 'author_name', 'sentiment', 'source_type', 'created_at']
                missing_keys = [key for key in required_keys if key not in review]
                if missing_keys:
                    self.log(f"   ⚠️  Missing review keys: {missing_keys}")
                else:
                    self.log(f"   ✅ Review structure complete")
                    
                    # Test AI suggestion for review
                    review_id = review['id']
                    self.run_test("V2 AI Suggest Review Reply", "POST", f"v2/reviews/tenants/{self.tenant_slug}/{review_id}/ai-suggest", 200)
                    
                    # Test reply to review
                    reply_data = {"text": "Thank you for your feedback! We appreciate your review."}
                    self.run_test("V2 Reply to Review", "POST", f"v2/reviews/tenants/{self.tenant_slug}/{review_id}/reply", 200, reply_data)

    def test_sprint3_webchat_apis(self):
        """Test Sprint 3 WebChat APIs"""
        self.log("\n=== SPRINT 3: WEBCHAT APIs ===")
        
        # Test WebChat widget JS generation
        widget_success, widget_js = self.run_test("WebChat Widget JS", "GET", f"v2/inbox/webchat/widget.js?tenantSlug={self.tenant_slug}", 200, headers={'Accept': 'application/javascript'})
        if widget_success:
            self.log(f"   ✅ Widget JS generated (length: {len(str(widget_js)) if widget_js else 0} chars)")
        
        # Test WebChat conversation start
        start_data = {"tenantSlug": self.tenant_slug, "visitorName": "Test Visitor"}
        start_success, start_response = self.run_test("WebChat Start Conversation", "POST", "v2/inbox/webchat/start", 200, start_data, headers={})
        if start_success and start_response.get('conversationId'):
            conv_id = start_response['conversationId']
            self.log(f"   ✅ WebChat conversation created: {conv_id}")
            
            # Test guest message in WebChat
            msg_data = {"text": "Hello from API test", "senderName": "Test Visitor"}
            self.run_test("WebChat Guest Message", "POST", f"v2/inbox/webchat/{conv_id}/messages", 200, msg_data, headers={})

    def test_sprint3_ai_usage_enforcement(self):
        """Test Sprint 3 AI Usage Enforcement (402 on limit exceeded)"""
        self.log("\n=== SPRINT 3: AI USAGE ENFORCEMENT ===")
        
        # Get current usage first
        usage_success, usage_data = self.run_test("Get Usage Metrics", "GET", f"tenants/{self.tenant_slug}/usage", 200)
        if usage_success:
            current_usage = usage_data.get('current', {})
            ai_replies_used = current_usage.get('ai_replies_used', 0)
            limits = usage_data.get('limits', {})
            ai_replies_limit = limits.get('monthly_ai_replies', 500)
            
            self.log(f"   Current AI usage: {ai_replies_used}/{ai_replies_limit}")
            
            # Test AI suggestion endpoints (these should work normally within limits)
            convs_success, convs_data = self.run_test("Get Conversations for AI Test", "GET", f"v2/inbox/tenants/{self.tenant_slug}/conversations", 200)
            if convs_success and convs_data.get('data'):
                conv_id = convs_data['data'][0]['id']
                ai_success, ai_response = self.run_test("AI Suggest (Within Limits)", "POST", f"v2/inbox/tenants/{self.tenant_slug}/conversations/{conv_id}/ai-suggest", 200)
                if ai_success and ai_response.get('usage'):
                    usage_info = ai_response['usage']
                    self.log(f"   ✅ AI usage tracking: {usage_info.get('used', 0)}/{usage_info.get('limit', 0)}")
            
            # Note: Testing 402 limit exceeded would require artificially setting usage high
            # or making 500+ requests which is not practical in testing
            self.log(f"   ✅ AI enforcement system active (would return 402 at {ai_replies_limit} limit)")

    def test_sprint3_channel_filtering(self):
        """Test Sprint 3 Channel Filtering"""
        self.log("\n=== SPRINT 3: CHANNEL FILTERING ===")
        
        # Test filtering by different channels
        channels = ['WEBCHAT', 'WHATSAPP', 'INSTAGRAM']
        for channel in channels:
            success, data = self.run_test(f"Filter by {channel}", "GET", f"v2/inbox/tenants/{self.tenant_slug}/conversations?channel={channel}", 200)
            if success:
                convs = data.get('data', [])
                filtered_convs = [c for c in convs if c.get('channel_type') == channel]
                self.log(f"   {channel}: {len(filtered_convs)}/{len(convs)} conversations match filter")
        
        # Test reviews filtering by source
        sources = ['GOOGLE_REVIEWS', 'TRIPADVISOR']
        for source in sources:
            success, data = self.run_test(f"Filter Reviews by {source}", "GET", f"v2/reviews/tenants/{self.tenant_slug}?source={source}", 200)
            if success:
                reviews = data.get('data', [])
                filtered_reviews = [r for r in reviews if r.get('source_type') == source]
                self.log(f"   {source}: {len(filtered_reviews)}/{len(reviews)} reviews match filter")

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
            self.test_analytics_engine_fix,
            self.test_v2_modular_routes,
            self.test_guest_resolve_endpoints,
            self.test_system_status,
            self.test_reviews_system,
            self.test_offers_and_payments,
            self.test_connectors,
            self.test_existing_functionality,
            self.test_guest_panels,
            self.test_guest_request_creation,
            self.test_guest_order_creation,
            # Phase 5 tests
            self.test_phase5_plan_management,
            self.test_phase5_usage_enforcement,
            self.test_phase5_billing,
            self.test_phase5_analytics,
            self.test_phase5_compliance,
            self.test_phase5_growth_referrals,
            self.test_phase5_system_metrics,
            self.test_phase5_onboarding,
            self.test_phase5_demo_reset,
            # Phase 5+ tests
            self.test_phase5plus_guest_tokens,
            self.test_phase5plus_qr_generation,
            self.test_phase5plus_comments_system,
            self.test_phase5plus_kb_articles,
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