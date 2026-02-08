#!/usr/bin/env python3
"""
Sprint 7 AI Sales Engine Test Suite
Tests the AI-powered booking assistant with tool calling capabilities
"""
import asyncio
import aiohttp
import json
import os
import sys
import time
from pathlib import Path

# Configuration
BASE_URL = "https://booking-automation-2.preview.emergentagent.com/api"
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
        print(f"\n=== SPRINT 7 AI SALES ENGINE TEST RESULTS ===")
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

class Sprint7Tester:
    def __init__(self):
        self.session = None
        self.token = None
        self.results = TestResults()
        self.property_id = None
        
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
    
    async def test_ai_sales_settings(self):
        """Test 1: AI Sales Settings endpoint"""
        print("\n🔍 Testing AI Sales Settings...")
        try:
            async with self.session.get(
                f"{BASE_URL}/v2/ai-sales/tenants/{TENANT_SLUG}/settings",
                headers=self.get_headers()
            ) as response:
                if response.status != 200:
                    self.results.add_test("AI Sales Settings - Status", False, f"Expected 200, got {response.status}")
                    return
                
                settings = await response.json()
                
                if not isinstance(settings, list):
                    self.results.add_test("AI Sales Settings - Format", False, f"Expected list, got {type(settings)}")
                    return
                
                if len(settings) >= 2:
                    self.results.add_test("AI Sales Settings - Count", True, f"Found {len(settings)} property settings")
                else:
                    self.results.add_test("AI Sales Settings - Count", False, f"Expected >= 2 properties, got {len(settings)}")
                    return
                
                # Find enabled property and store property_id
                enabled_property = None
                for setting in settings:
                    if setting.get("enabled", False):
                        enabled_property = setting
                        self.property_id = setting.get("property_id")
                        break
                
                if enabled_property:
                    self.results.add_test("AI Sales Settings - Enabled Property", True, f"Found enabled property: {enabled_property.get('property_name')}")
                else:
                    self.results.add_test("AI Sales Settings - Enabled Property", False, "No enabled property found")
                    
        except Exception as e:
            self.results.add_test("AI Sales Settings Error", False, str(e))
    
    async def test_room_rates(self):
        """Test 2: Room Rates endpoint"""
        print("\n🔍 Testing Room Rates...")
        
        if not self.property_id:
            self.results.add_test("Room Rates - No Property ID", False, "Property ID not available from settings test")
            return
            
        try:
            async with self.session.get(
                f"{BASE_URL}/v2/ai-sales/tenants/{TENANT_SLUG}/properties/{self.property_id}/room-rates",
                headers=self.get_headers()
            ) as response:
                if response.status != 200:
                    self.results.add_test("Room Rates - Status", False, f"Expected 200, got {response.status}")
                    return
                
                rates = await response.json()
                
                if not isinstance(rates, list):
                    self.results.add_test("Room Rates - Format", False, f"Expected list, got {type(rates)}")
                    return
                
                if len(rates) >= 3:
                    self.results.add_test("Room Rates - Count", True, f"Found {len(rates)} room rates")
                else:
                    self.results.add_test("Room Rates - Count", False, f"Expected >= 3 rates, got {len(rates)}")
                
                # Check for main property rates
                standard_found = any(r.get("room_type_code") == "standard" for r in rates)
                deluxe_found = any(r.get("room_type_code") == "deluxe" for r in rates)
                suite_found = any(r.get("room_type_code") == "suite" for r in rates)
                
                if standard_found and deluxe_found and suite_found:
                    self.results.add_test("Room Rates - Expected Types", True, "Found standard, deluxe, suite rates")
                else:
                    self.results.add_test("Room Rates - Expected Types", False, f"Missing rate types (std:{standard_found}, dlx:{deluxe_found}, ste:{suite_found})")
                    
        except Exception as e:
            self.results.add_test("Room Rates Error", False, str(e))
    
    async def test_create_room_rate(self):
        """Test 3: Create Room Rate endpoint"""
        print("\n🔍 Testing Create Room Rate...")
        
        if not self.property_id:
            self.results.add_test("Create Room Rate - No Property ID", False, "Property ID not available")
            return
            
        try:
            rate_data = {
                "room_type_code": "economy",
                "room_type_name": "Economy Room",
                "base_price_per_night": 800,
                "max_guests": 2
            }
            
            async with self.session.post(
                f"{BASE_URL}/v2/ai-sales/tenants/{TENANT_SLUG}/properties/{self.property_id}/room-rates",
                json=rate_data,
                headers=self.get_headers()
            ) as response:
                if response.status == 200:
                    rate = await response.json()
                    self.results.add_test("Create Room Rate - Success", True, f"Created rate: {rate.get('room_type_code')}")
                    
                    # Verify the created rate has expected fields
                    if rate.get("base_price_per_night") == 800 and rate.get("max_guests") == 2:
                        self.results.add_test("Create Room Rate - Data Integrity", True, "Rate data matches input")
                    else:
                        self.results.add_test("Create Room Rate - Data Integrity", False, f"Data mismatch: {rate}")
                        
                elif response.status == 409:
                    self.results.add_test("Create Room Rate - Duplicate Handling", True, "Correctly rejected duplicate room type code")
                else:
                    self.results.add_test("Create Room Rate - Status", False, f"Unexpected status: {response.status}")
                    
        except Exception as e:
            self.results.add_test("Create Room Rate Error", False, str(e))
    
    async def test_room_rate_uniqueness(self):
        """Test 9: Room Rate Uniqueness (duplicate should return 409)"""
        print("\n🔍 Testing Room Rate Uniqueness...")
        
        if not self.property_id:
            self.results.add_test("Room Rate Uniqueness - No Property ID", False, "Property ID not available")
            return
            
        try:
            # Try to create duplicate economy room
            rate_data = {
                "room_type_code": "economy",
                "room_type_name": "Another Economy Room",
                "base_price_per_night": 900,
                "max_guests": 2
            }
            
            async with self.session.post(
                f"{BASE_URL}/v2/ai-sales/tenants/{TENANT_SLUG}/properties/{self.property_id}/room-rates",
                json=rate_data,
                headers=self.get_headers()
            ) as response:
                if response.status == 409:
                    self.results.add_test("Room Rate Uniqueness - 409 Response", True, "Correctly returned 409 for duplicate")
                else:
                    self.results.add_test("Room Rate Uniqueness - 409 Response", False, f"Expected 409, got {response.status}")
                    
        except Exception as e:
            self.results.add_test("Room Rate Uniqueness Error", False, str(e))
    
    async def test_discount_rules(self):
        """Test 4: Discount Rules endpoint"""
        print("\n🔍 Testing Discount Rules...")
        
        if not self.property_id:
            self.results.add_test("Discount Rules - No Property ID", False, "Property ID not available")
            return
            
        try:
            async with self.session.get(
                f"{BASE_URL}/v2/ai-sales/tenants/{TENANT_SLUG}/properties/{self.property_id}/discount-rules",
                headers=self.get_headers()
            ) as response:
                if response.status != 200:
                    self.results.add_test("Discount Rules - Status", False, f"Expected 200, got {response.status}")
                    return
                
                rules = await response.json()
                
                # Check for expected discount rules
                max_discount = rules.get("max_discount_percent", 0)
                min_nights = rules.get("min_nights_for_discount", 0)
                
                if max_discount >= 10:
                    self.results.add_test("Discount Rules - Max Discount", True, f"Max discount: {max_discount}%")
                else:
                    self.results.add_test("Discount Rules - Max Discount", False, f"Expected >=10%, got {max_discount}%")
                
                if min_nights >= 3:
                    self.results.add_test("Discount Rules - Min Nights", True, f"Min nights: {min_nights}")
                else:
                    self.results.add_test("Discount Rules - Min Nights", False, f"Expected >=3 nights, got {min_nights}")
                    
        except Exception as e:
            self.results.add_test("Discount Rules Error", False, str(e))
    
    async def test_policies(self):
        """Test 5: Business Policies endpoint"""
        print("\n🔍 Testing Business Policies...")
        
        if not self.property_id:
            self.results.add_test("Policies - No Property ID", False, "Property ID not available")
            return
            
        try:
            async with self.session.get(
                f"{BASE_URL}/v2/ai-sales/tenants/{TENANT_SLUG}/properties/{self.property_id}/policies",
                headers=self.get_headers()
            ) as response:
                if response.status != 200:
                    self.results.add_test("Policies - Status", False, f"Expected 200, got {response.status}")
                    return
                
                policies = await response.json()
                
                # Check for expected policies
                check_in = policies.get("check_in_time", "")
                check_out = policies.get("check_out_time", "")
                
                if "14:00" in check_in:
                    self.results.add_test("Policies - Check-in Time", True, f"Check-in: {check_in}")
                else:
                    self.results.add_test("Policies - Check-in Time", False, f"Expected 14:00, got {check_in}")
                
                if "12:00" in check_out:
                    self.results.add_test("Policies - Check-out Time", True, f"Check-out: {check_out}")
                else:
                    self.results.add_test("Policies - Check-out Time", False, f"Expected 12:00, got {check_out}")
                    
        except Exception as e:
            self.results.add_test("Policies Error", False, str(e))
    
    async def test_ai_stats(self):
        """Test 6: AI Stats endpoint"""
        print("\n🔍 Testing AI Stats...")
        try:
            async with self.session.get(
                f"{BASE_URL}/v2/ai-sales/tenants/{TENANT_SLUG}/stats",
                headers=self.get_headers()
            ) as response:
                if response.status != 200:
                    self.results.add_test("AI Stats - Status", False, f"Expected 200, got {response.status}")
                    return
                
                stats = await response.json()
                
                # Check for expected stats
                ai_replies_used = stats.get("ai_replies_used", 0)
                ai_replies_limit = stats.get("ai_replies_limit", 0)
                
                if ai_replies_used > 0:
                    self.results.add_test("AI Stats - Replies Used", True, f"AI replies used: {ai_replies_used}")
                else:
                    self.results.add_test("AI Stats - Replies Used", False, f"Expected >0 replies used, got {ai_replies_used}")
                
                if ai_replies_limit > 0:
                    self.results.add_test("AI Stats - Replies Limit", True, f"AI replies limit: {ai_replies_limit}")
                else:
                    self.results.add_test("AI Stats - Replies Limit", False, f"Expected >0 limit, got {ai_replies_limit}")
                
                # Check other stats exist
                required_fields = ["ai_offers_created", "ai_offers_paid", "active_sessions", "month"]
                for field in required_fields:
                    if field in stats:
                        self.results.add_test(f"AI Stats - {field.title()}", True, f"{field}: {stats[field]}")
                    else:
                        self.results.add_test(f"AI Stats - {field.title()}", False, f"Missing field: {field}")
                        
        except Exception as e:
            self.results.add_test("AI Stats Error", False, str(e))
    
    async def test_webchat_ai_flow(self):
        """Test 7: Webchat AI Flow (start conversation + send message)"""
        print("\n🔍 Testing Webchat AI Flow...")
        
        conv_id = None
        
        # Step 1: Start webchat conversation
        try:
            start_data = {
                "tenantSlug": TENANT_SLUG,
                "visitorName": "Test"
            }
            
            async with self.session.post(
                f"{BASE_URL}/v2/inbox/webchat/start",
                json=start_data
            ) as response:
                if response.status == 200:
                    conv_data = await response.json()
                    conv_id = conv_data.get("conversationId")
                    self.results.add_test("Webchat Start - Success", True, f"Conversation ID: {conv_id}")
                else:
                    self.results.add_test("Webchat Start - Status", False, f"Expected 200, got {response.status}")
                    return
                    
        except Exception as e:
            self.results.add_test("Webchat Start Error", False, str(e))
            return
        
        if not conv_id:
            self.results.add_test("Webchat Start - No Conversation ID", False, "No conversation ID returned")
            return
        
        # Step 2: Send message and expect AI reply
        try:
            message_data = {
                "text": "Merhaba, oda fiyatlariniz nedir?",
                "senderName": "Test"
            }
            
            async with self.session.post(
                f"{BASE_URL}/v2/inbox/webchat/{conv_id}/messages",
                json=message_data
            ) as response:
                if response.status == 200:
                    msg_result = await response.json()
                    
                    # Check if AI reply is present
                    if "ai_reply" in msg_result:
                        ai_reply = msg_result["ai_reply"]
                        self.results.add_test("Webchat AI Reply - Present", True, "AI reply received")
                        
                        # Check AI reply structure
                        if "ai_text" in ai_reply and "tool_calls" in ai_reply:
                            self.results.add_test("Webchat AI Reply - Structure", True, f"AI text length: {len(ai_reply.get('ai_text', ''))}")
                        else:
                            self.results.add_test("Webchat AI Reply - Structure", False, f"Missing fields in AI reply: {ai_reply.keys()}")
                    else:
                        self.results.add_test("Webchat AI Reply - Present", False, "No ai_reply in response")
                        
                else:
                    self.results.add_test("Webchat Message - Status", False, f"Expected 200, got {response.status}")
                    
        except Exception as e:
            self.results.add_test("Webchat Message Error", False, str(e))
    
    async def test_get_messages(self):
        """Test 8: GET messages endpoint"""
        print("\n🔍 Testing GET Messages...")
        
        # Create a conversation first
        conv_id = None
        try:
            start_data = {
                "tenantSlug": TENANT_SLUG,
                "visitorName": "MessageTest"
            }
            
            async with self.session.post(
                f"{BASE_URL}/v2/inbox/webchat/start",
                json=start_data
            ) as response:
                if response.status == 200:
                    conv_data = await response.json()
                    conv_id = conv_data.get("conversationId")
                    
        except Exception as e:
            self.results.add_test("GET Messages - Setup Error", False, str(e))
            return
        
        if not conv_id:
            self.results.add_test("GET Messages - No Conversation", False, "Could not create test conversation")
            return
        
        # Send a message first
        try:
            message_data = {
                "text": "Test message for GET endpoint",
                "senderName": "MessageTest"
            }
            
            await self.session.post(
                f"{BASE_URL}/v2/inbox/webchat/{conv_id}/messages",
                json=message_data
            )
            
            # Small delay to ensure message is processed
            await asyncio.sleep(1)
            
        except Exception as e:
            self.results.add_test("GET Messages - Send Message Error", False, str(e))
            return
        
        # Now test GET messages
        try:
            async with self.session.get(
                f"{BASE_URL}/v2/inbox/webchat/{conv_id}/messages"
            ) as response:
                if response.status == 200:
                    messages = await response.json()
                    
                    if isinstance(messages, list):
                        self.results.add_test("GET Messages - Format", True, f"Received {len(messages)} messages")
                        
                        # Check for AI replies in messages
                        ai_messages = [msg for msg in messages if msg.get("meta", {}).get("ai", False)]
                        if ai_messages:
                            self.results.add_test("GET Messages - AI Messages", True, f"Found {len(ai_messages)} AI messages")
                        else:
                            self.results.add_test("GET Messages - AI Messages", False, "No AI messages found")
                    else:
                        self.results.add_test("GET Messages - Format", False, f"Expected list, got {type(messages)}")
                        
                else:
                    self.results.add_test("GET Messages - Status", False, f"Expected 200, got {response.status}")
                    
        except Exception as e:
            self.results.add_test("GET Messages Error", False, str(e))

    async def run_all_tests(self):
        """Run all Sprint 7 tests"""
        print("🚀 Starting Sprint 7 AI Sales Engine Test Suite...")
        
        if not await self.setup():
            return
        
        try:
            # Run all tests in order
            await self.test_ai_sales_settings()
            await self.test_room_rates()
            await self.test_create_room_rate()
            await self.test_discount_rules()
            await self.test_policies()
            await self.test_ai_stats()
            await self.test_webchat_ai_flow()
            await self.test_get_messages()
            await self.test_room_rate_uniqueness()
            
        finally:
            await self.cleanup()
        
        # Print results
        self.results.print_summary()
        return self.results

async def main():
    """Main test runner"""
    tester = Sprint7Tester()
    results = await tester.run_all_tests()
    
    # Exit with proper code
    if results.failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())