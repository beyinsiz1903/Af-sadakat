#!/usr/bin/env python3
"""
Sprint 6 Hardening Features Test Suite
Tests the production hardening features for multi-tenant hotel SaaS
"""
import asyncio
import aiohttp
import json
import os
import sys
import time
from pathlib import Path

# Configuration
BASE_URL = "https://property-payments-1.preview.emergentagent.com/api"
TENANT_SLUG = "grand-hotel"
LOGIN_CREDENTIALS = {
    "email": "admin@grandhotel.com", 
    "password": "admin123"
}

class TestResults:
    def __init__(self):
        self.tests = []
        self.passed = 0
        self.failed = 0
        
    def add_test(self, name, passed, details=""):
        self.tests.append({
            "name": name,
            "passed": passed,
            "details": details
        })
        if passed:
            self.passed += 1
        else:
            self.failed += 1
            
    def print_summary(self):
        print(f"\n=== SPRINT 6 TEST RESULTS ===")
        print(f"Total: {len(self.tests)}, Passed: {self.passed}, Failed: {self.failed}")
        print(f"Success Rate: {(self.passed/len(self.tests)*100):.1f}%")
        
        if self.failed > 0:
            print(f"\n=== FAILED TESTS ===")
            for test in self.tests:
                if not test["passed"]:
                    print(f"❌ {test['name']}: {test['details']}")
        
        print(f"\n=== PASSED TESTS ===")
        for test in self.tests:
            if test["passed"]:
                print(f"✅ {test['name']}")

class Sprint6Tester:
    def __init__(self):
        self.session = None
        self.token = None
        self.results = TestResults()
        
    async def setup(self):
        """Setup HTTP session and get auth token"""
        self.session = aiohttp.ClientSession()
        
        # Login to get token
        try:
            async with self.session.post(f"{BASE_URL}/auth/login", json=LOGIN_CREDENTIALS) as response:
                if response.status == 200:
                    data = await response.json()
                    self.token = data["token"]
                    self.results.add_test("Authentication Setup", True, "Successfully logged in")
                    print(f"✅ Authenticated as {LOGIN_CREDENTIALS['email']}")
                else:
                    self.results.add_test("Authentication Setup", False, f"Login failed: {response.status}")
                    print(f"❌ Login failed: {response.status}")
                    return False
        except Exception as e:
            self.results.add_test("Authentication Setup", False, f"Login error: {str(e)}")
            print(f"❌ Login error: {str(e)}")
            return False
            
        return True
        
    async def cleanup(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            
    def get_headers(self):
        """Get headers with auth token"""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers
    
    async def test_health_endpoint(self):
        """Test 1: Health endpoint returns Sprint 6 data"""
        print("\n🔍 Testing Health Endpoint...")
        try:
            async with self.session.get(f"{BASE_URL}/health") as response:
                data = await response.json()
                request_id = response.headers.get("X-Request-Id")
                
                # Check basic response
                if response.status != 200:
                    self.results.add_test("Health Status Code", False, f"Expected 200, got {response.status}")
                    return
                    
                # Check version 6.0.0
                if data.get("version") != "6.0.0":
                    self.results.add_test("Health Version", False, f"Expected 6.0.0, got {data.get('version')}")
                else:
                    self.results.add_test("Health Version", True)
                
                # Check status "ok"
                if data.get("status") != "ok":
                    self.results.add_test("Health Status", False, f"Expected 'ok', got {data.get('status')}")
                else:
                    self.results.add_test("Health Status", True)
                
                # Check uptime_seconds > 0
                uptime = data.get("uptime_seconds", 0)
                if uptime > 0:
                    self.results.add_test("Health Uptime", True, f"Uptime: {uptime}s")
                else:
                    self.results.add_test("Health Uptime", False, f"Expected > 0, got {uptime}")
                
                # Check services
                services = data.get("services", {})
                if services.get("mongodb") == True:
                    self.results.add_test("Health MongoDB", True)
                else:
                    self.results.add_test("Health MongoDB", False, f"MongoDB service: {services.get('mongodb')}")
                    
                if services.get("redis") == True:
                    self.results.add_test("Health Redis", True)
                else:
                    self.results.add_test("Health Redis", False, f"Redis service: {services.get('redis')}")
                
                # Check X-Request-Id header
                if request_id:
                    self.results.add_test("Health Request ID Header", True, f"Request ID: {request_id}")
                else:
                    self.results.add_test("Health Request ID Header", False, "Missing X-Request-Id header")
                    
        except Exception as e:
            self.results.add_test("Health Endpoint Error", False, str(e))
    
    async def test_request_id_middleware(self):
        """Test 2: Request ID middleware on various endpoints"""
        print("\n🔍 Testing Request ID Middleware...")
        
        endpoints = [
            f"{BASE_URL}/health",
            f"{BASE_URL}/auth/login"
        ]
        
        for endpoint in endpoints:
            try:
                if "login" in endpoint:
                    async with self.session.post(endpoint, json=LOGIN_CREDENTIALS) as response:
                        request_id = response.headers.get("X-Request-Id")
                else:
                    async with self.session.get(endpoint) as response:
                        request_id = response.headers.get("X-Request-Id")
                
                if request_id:
                    self.results.add_test(f"Request ID on {endpoint.split('/')[-1]}", True, f"ID: {request_id}")
                else:
                    self.results.add_test(f"Request ID on {endpoint.split('/')[-1]}", False, "Missing X-Request-Id")
                    
            except Exception as e:
                self.results.add_test(f"Request ID test {endpoint}", False, str(e))
    
    async def test_confirmation_code_format(self):
        """Test 3: New confirmation code format (PREFIX-YYYYMM-XXXXXX)"""
        print("\n🔍 Testing Confirmation Code Format...")
        
        try:
            # 1. Create an offer
            offer_data = {
                "guest_name": "CodeTest",
                "price_total": 500,
                "currency": "TRY", 
                "room_type": "standard",
                "check_in": "2026-05-01",
                "check_out": "2026-05-03"
            }
            
            async with self.session.post(
                f"{BASE_URL}/v2/offers/tenants/{TENANT_SLUG}/offers",
                json=offer_data,
                headers=self.get_headers()
            ) as response:
                if response.status != 200:
                    self.results.add_test("Confirmation Code - Create Offer", False, f"Status: {response.status}")
                    return
                offer = await response.json()
                offer_id = offer["id"]
                self.results.add_test("Confirmation Code - Create Offer", True, f"Offer ID: {offer_id}")
            
            # 2. Create payment link
            async with self.session.post(
                f"{BASE_URL}/v2/offers/tenants/{TENANT_SLUG}/offers/{offer_id}/create-payment-link",
                headers=self.get_headers()
            ) as response:
                if response.status != 200:
                    self.results.add_test("Confirmation Code - Payment Link", False, f"Status: {response.status}")
                    return
                payment_link = await response.json()
                payment_link_id = payment_link["id"]
                self.results.add_test("Confirmation Code - Payment Link", True, f"Link ID: {payment_link_id}")
            
            # 3. Mock payment success
            webhook_data = {"paymentLinkId": payment_link_id}
            async with self.session.post(
                f"{BASE_URL}/v2/payments/webhook/mock/succeed",
                json=webhook_data
            ) as response:
                if response.status != 200:
                    self.results.add_test("Confirmation Code - Mock Payment", False, f"Status: {response.status}")
                    return
                result = await response.json()
                self.results.add_test("Confirmation Code - Mock Payment", True, "Payment succeeded")
                
                # 4. Check confirmation code format
                reservation = result.get("reservation", {})
                confirmation_code = reservation.get("confirmation_code", "")
                
                if not confirmation_code:
                    self.results.add_test("Confirmation Code Format", False, "No confirmation code in response")
                    return
                
                # Check format: XXX-YYYYMM-XXXXXX
                parts = confirmation_code.split("-")
                if len(parts) != 3:
                    self.results.add_test("Confirmation Code Format", False, f"Wrong format: {confirmation_code}")
                    return
                
                prefix, date_part, random_part = parts
                
                # Check prefix (3 letters)
                if len(prefix) == 3 and prefix.isalpha():
                    prefix_ok = True
                else:
                    prefix_ok = False
                
                # Check date part (6 digits YYYYMM)
                if len(date_part) == 6 and date_part.isdigit():
                    date_ok = True
                else:
                    date_ok = False
                
                # Check random part (6 alphanumeric)
                if len(random_part) == 6 and random_part.isalnum():
                    random_ok = True
                else:
                    random_ok = False
                
                # Check it's NOT the old RES-XXXXXX format
                old_format = confirmation_code.startswith("RES-") and len(confirmation_code.split("-")) == 2
                
                if prefix_ok and date_ok and random_ok and not old_format:
                    self.results.add_test("Confirmation Code Format", True, f"Valid format: {confirmation_code}")
                else:
                    self.results.add_test("Confirmation Code Format", False, 
                                        f"Invalid format: {confirmation_code} (prefix:{prefix_ok}, date:{date_ok}, random:{random_ok}, old_format:{old_format})")
                
        except Exception as e:
            self.results.add_test("Confirmation Code Test Error", False, str(e))
    
    async def test_payment_idempotency(self):
        """Test 4: Payment idempotency (atomic operations)"""
        print("\n🔍 Testing Payment Idempotency...")
        
        try:
            # Create offer and payment link
            offer_data = {
                "guest_name": "IdempotencyTest",
                "price_total": 750,
                "currency": "TRY",
                "room_type": "deluxe", 
                "check_in": "2026-06-01",
                "check_out": "2026-06-03"
            }
            
            # Create offer
            async with self.session.post(
                f"{BASE_URL}/v2/offers/tenants/{TENANT_SLUG}/offers",
                json=offer_data,
                headers=self.get_headers()
            ) as response:
                offer = await response.json()
                offer_id = offer["id"]
            
            # Create payment link
            async with self.session.post(
                f"{BASE_URL}/v2/offers/tenants/{TENANT_SLUG}/offers/{offer_id}/create-payment-link",
                headers=self.get_headers()
            ) as response:
                payment_link = await response.json()
                payment_link_id = payment_link["id"]
            
            # First payment success
            webhook_data = {"paymentLinkId": payment_link_id}
            async with self.session.post(
                f"{BASE_URL}/v2/payments/webhook/mock/succeed",
                json=webhook_data
            ) as response:
                first_result = await response.json()
                first_idempotent = first_result.get("idempotent", None)
                first_reservation_id = first_result.get("reservation", {}).get("id")
                
                if first_idempotent == False:
                    self.results.add_test("Payment First Success", True, "New payment processed")
                else:
                    self.results.add_test("Payment First Success", False, f"Unexpected idempotent: {first_idempotent}")
            
            # Second payment success (should be idempotent)
            async with self.session.post(
                f"{BASE_URL}/v2/payments/webhook/mock/succeed", 
                json=webhook_data
            ) as response:
                second_result = await response.json()
                second_idempotent = second_result.get("idempotent", None)
                second_reservation_id = second_result.get("reservation", {}).get("id")
                
                if second_idempotent == True:
                    self.results.add_test("Payment Second Success (Idempotent)", True, "Idempotent response")
                else:
                    self.results.add_test("Payment Second Success (Idempotent)", False, f"Expected idempotent=true, got {second_idempotent}")
                
                # Same reservation returned
                if first_reservation_id == second_reservation_id and first_reservation_id:
                    self.results.add_test("Payment Same Reservation", True, f"Same reservation ID: {first_reservation_id}")
                else:
                    self.results.add_test("Payment Same Reservation", False, f"Different reservations: {first_reservation_id} vs {second_reservation_id}")
            
            # Verify only one reservation exists
            async with self.session.get(
                f"{BASE_URL}/v2/reservations/tenants/{TENANT_SLUG}/reservations",
                headers=self.get_headers()
            ) as response:
                reservations_data = await response.json()
                reservations = reservations_data.get("data", [])
                matching_reservations = [r for r in reservations if r.get("offer_id") == offer_id]
                
                if len(matching_reservations) == 1:
                    self.results.add_test("Payment Single Reservation", True, "Only one reservation created")
                else:
                    self.results.add_test("Payment Single Reservation", False, f"Found {len(matching_reservations)} reservations for offer")
                    
        except Exception as e:
            self.results.add_test("Payment Idempotency Error", False, str(e))
    
    async def test_payment_safety(self):
        """Test 5: Payment safety (error handling)"""
        print("\n🔍 Testing Payment Safety...")
        
        # Test checkout on non-existent payment link
        try:
            async with self.session.post(f"{BASE_URL}/v2/payments/pay/nonexistent-link/checkout") as response:
                if response.status == 404:
                    self.results.add_test("Payment Safety - 404 for non-existent link", True, "Correctly returned 404")
                else:
                    self.results.add_test("Payment Safety - 404 for non-existent link", False, f"Expected 404, got {response.status}")
        except Exception as e:
            self.results.add_test("Payment Safety - 404 test error", False, str(e))
        
        # Test mock/succeed without paymentLinkId  
        try:
            async with self.session.post(f"{BASE_URL}/v2/payments/webhook/mock/succeed", json={}) as response:
                if response.status == 400:
                    self.results.add_test("Payment Safety - 400 for missing paymentLinkId", True, "Correctly returned 400")
                else:
                    self.results.add_test("Payment Safety - 400 for missing paymentLinkId", False, f"Expected 400, got {response.status}")
        except Exception as e:
            self.results.add_test("Payment Safety - 400 test error", False, str(e))
    
    async def test_notification_engine(self):
        """Test 6: Notification engine (check DB records)"""
        print("\n🔍 Testing Notification Engine...")
        
        try:
            # Look for notification records in audit logs
            async with self.session.get(
                f"{BASE_URL}/tenants/{TENANT_SLUG}/audit-logs",
                headers=self.get_headers()
            ) as response:
                if response.status != 200:
                    self.results.add_test("Notification Engine - Audit Logs Access", False, f"Status: {response.status}")
                    return
                
                audit_data = await response.json()
                audit_logs = audit_data.get("data", [])
                
                # Look for notification-related entries
                notification_logs = []
                for log in audit_logs:
                    action = log.get("action", "")
                    if "NOTIFICATION" in action:
                        notification_logs.append(log)
                
                if notification_logs:
                    self.results.add_test("Notification Engine - Records Found", True, f"Found {len(notification_logs)} notification log entries")
                    
                    # Check for specific notification types
                    payment_notifications = [log for log in notification_logs if "PAYMENT_SUCCEEDED" in log.get("action", "")]
                    reservation_notifications = [log for log in notification_logs if "RESERVATION_CONFIRMED" in log.get("action", "")]
                    
                    if payment_notifications:
                        self.results.add_test("Notification Engine - Payment Notifications", True, f"Found {len(payment_notifications)} payment notifications")
                    else:
                        self.results.add_test("Notification Engine - Payment Notifications", False, "No payment notification records found")
                        
                    if reservation_notifications:
                        self.results.add_test("Notification Engine - Reservation Notifications", True, f"Found {len(reservation_notifications)} reservation notifications")
                    else:
                        self.results.add_test("Notification Engine - Reservation Notifications", False, "No reservation notification records found")
                else:
                    self.results.add_test("Notification Engine - Records Found", False, "No notification records found in audit logs")
                    
        except Exception as e:
            self.results.add_test("Notification Engine Error", False, str(e))
    
    async def test_rate_limiting(self):
        """Test 7: Rate limiting on public endpoints"""
        print("\n🔍 Testing Rate Limiting...")
        
        try:
            # Make 5 rapid requests to a public payment endpoint
            responses = []
            for i in range(5):
                async with self.session.get(f"{BASE_URL}/v2/payments/pay/nonexistent") as response:
                    responses.append(response.status)
                await asyncio.sleep(0.1)  # Small delay
            
            # All should succeed (within 30/min limit)
            success_count = sum(1 for status in responses if status in [404, 200])  # 404 is expected for nonexistent
            
            if success_count >= 4:  # Allow for some variance
                self.results.add_test("Rate Limiting - Normal Load", True, f"All {success_count}/5 requests succeeded")
            else:
                self.results.add_test("Rate Limiting - Normal Load", False, f"Only {success_count}/5 requests succeeded")
                
        except Exception as e:
            self.results.add_test("Rate Limiting Error", False, str(e))
    
    async def test_properties_still_work(self):
        """Test 8: Properties V2 endpoints still working"""
        print("\n🔍 Testing Properties V2 Still Work...")
        
        try:
            async with self.session.get(
                f"{BASE_URL}/v2/properties/tenants/{TENANT_SLUG}/properties",
                headers=self.get_headers()
            ) as response:
                if response.status != 200:
                    self.results.add_test("Properties V2 - Status", False, f"Status: {response.status}")
                    return
                
                properties_data = await response.json()
                properties = properties_data.get("data", [])
                
                if len(properties) >= 2:
                    self.results.add_test("Properties V2 - Count", True, f"Found {len(properties)} properties")
                else:
                    self.results.add_test("Properties V2 - Count", False, f"Expected >= 2 properties, found {len(properties)}")
                    
        except Exception as e:
            self.results.add_test("Properties V2 Error", False, str(e))
    
    async def test_cli_export_verification(self):
        """Test 9: Verify data exists for CLI export"""
        print("\n🔍 Testing CLI Export Data Verification...")
        
        collections_to_check = [
            ("contacts", f"{BASE_URL}/tenants/{TENANT_SLUG}/contacts"),
            ("reservations", f"{BASE_URL}/v2/reservations/tenants/{TENANT_SLUG}/reservations"),
            ("offers", f"{BASE_URL}/v2/offers/tenants/{TENANT_SLUG}/offers"),
            ("loyalty_accounts", f"{BASE_URL}/tenants/{TENANT_SLUG}/loyalty/accounts")
        ]
        
        for collection_name, endpoint in collections_to_check:
            try:
                async with self.session.get(endpoint, headers=self.get_headers()) as response:
                    if response.status != 200:
                        self.results.add_test(f"CLI Export Data - {collection_name}", False, f"Status: {response.status}")
                        continue
                        
                    data = await response.json()
                    items = data.get("data", data)  # Some endpoints return data directly, others in "data" key
                    
                    if isinstance(items, list) and len(items) > 0:
                        self.results.add_test(f"CLI Export Data - {collection_name}", True, f"Found {len(items)} items")
                    else:
                        self.results.add_test(f"CLI Export Data - {collection_name}", False, f"No data found (got: {type(items)})")
                        
            except Exception as e:
                self.results.add_test(f"CLI Export Data - {collection_name} Error", False, str(e))

    async def run_all_tests(self):
        """Run all Sprint 6 tests"""
        print("🚀 Starting Sprint 6 Hardening Features Test Suite...")
        
        if not await self.setup():
            return
        
        try:
            # Run all tests
            await self.test_health_endpoint()
            await self.test_request_id_middleware()
            await self.test_confirmation_code_format()
            await self.test_payment_idempotency()
            await self.test_payment_safety()
            await self.test_notification_engine()
            await self.test_rate_limiting()
            await self.test_properties_still_work()
            await self.test_cli_export_verification()
            
        finally:
            await self.cleanup()
        
        # Print results
        self.results.print_summary()
        return self.results

async def main():
    """Main test runner"""
    tester = Sprint6Tester()
    results = await tester.run_all_tests()
    
    # Exit with proper code
    if results.failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())