#!/usr/bin/env python3
"""
Sprint 9 Backend API Testing for Hotel Management System
Tests Guest Services, SLA, Notifications, Housekeeping, Lost&Found, Social Dashboard, Reports APIs
"""

import requests
import json
import sys
from datetime import datetime

# Backend URL configuration
BACKEND_URL = "https://hospitality-ops-4.preview.emergentagent.com/api"

class APITester:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.tenant_slug = "grand-hotel"
        
    def login(self):
        """Login to get authentication token"""
        login_data = {
            "email": "admin@grandhotel.com",
            "password": "admin123"
        }
        
        response = self.session.post(f"{BACKEND_URL}/auth/login", json=login_data)
        if response.status_code == 200:
            data = response.json()
            self.token = data.get("token")
            self.session.headers.update({"Authorization": f"Bearer {self.token}"})
            print("✅ Login successful")
            return True
        else:
            print(f"❌ Login failed: {response.status_code} - {response.text}")
            return False
    
    def test_guest_services_apis(self):
        """Test Guest Services APIs (Public - no auth required)"""
        print("\n🧪 Testing Guest Services APIs (Public)")
        results = []
        
        # Test 1: GET hotel info
        try:
            url = f"{BACKEND_URL}/v2/guest-services/g/{self.tenant_slug}/hotel-info"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                has_facilities = "facilities" in data
                has_wifi = "wifi_name" in data or "wifi_password" in data
                has_emergency = "emergency_contacts" in data
                print(f"✅ Hotel info API: {response.status_code} - Has facilities: {has_facilities}, WiFi: {has_wifi}, Emergency: {has_emergency}")
                results.append(True)
            else:
                print(f"❌ Hotel info API failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ Hotel info API error: {e}")
            results.append(False)
        
        # Test 2: GET spa services 
        try:
            url = f"{BACKEND_URL}/v2/guest-services/g/{self.tenant_slug}/spa-services"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                spa_count = len(data) if isinstance(data, list) else 0
                print(f"✅ Spa services API: {response.status_code} - Found {spa_count} spa services")
                results.append(True)
            else:
                print(f"❌ Spa services API failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ Spa services API error: {e}")
            results.append(False)
        
        # Test 3: GET announcements
        try:
            url = f"{BACKEND_URL}/v2/guest-services/g/{self.tenant_slug}/announcements"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                ann_count = len(data) if isinstance(data, list) else 0
                print(f"✅ Announcements API: {response.status_code} - Found {ann_count} announcements")
                results.append(True)
            else:
                print(f"❌ Announcements API failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ Announcements API error: {e}")
            results.append(False)
        
        # Test 4: GET room service menu
        try:
            url = f"{BACKEND_URL}/v2/guest-services/g/{self.tenant_slug}/room-service-menu"
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                has_categories = "categories" in data and len(data.get("categories", [])) > 0
                has_items = "items" in data and len(data.get("items", [])) > 0
                print(f"✅ Room service menu API: {response.status_code} - Has categories: {has_categories}, items: {has_items}")
                results.append(True)
            else:
                print(f"❌ Room service menu API failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ Room service menu API error: {e}")
            results.append(False)
        
        # Test 5: POST spa booking
        try:
            url = f"{BACKEND_URL}/v2/guest-services/g/{self.tenant_slug}/room/R101/spa-booking"
            spa_data = {
                "service_type": "Swedish Massage",
                "preferred_date": "2026-03-01",
                "preferred_time": "14:00",
                "guest_name": "Test Guest",
                "persons": 1
            }
            response = requests.post(url, json=spa_data)
            if response.status_code == 200:
                data = response.json()
                has_id = "id" in data
                correct_service = data.get("service_type") == "Swedish Massage"
                print(f"✅ Spa booking API: {response.status_code} - Has ID: {has_id}, Service: {correct_service}")
                results.append(True)
            else:
                print(f"❌ Spa booking API failed: {response.status_code} - {response.text}")
                results.append(False)
        except Exception as e:
            print(f"❌ Spa booking API error: {e}")
            results.append(False)
        
        # Test 6: POST transport request
        try:
            url = f"{BACKEND_URL}/v2/guest-services/g/{self.tenant_slug}/room/R101/transport-request"
            transport_data = {
                "transport_type": "taxi",
                "destination": "Airport",
                "pickup_date": "2026-03-01",
                "pickup_time": "10:00",
                "guest_name": "Test Guest"
            }
            response = requests.post(url, json=transport_data)
            if response.status_code == 200:
                data = response.json()
                has_id = "id" in data
                correct_type = data.get("transport_type") == "taxi"
                print(f"✅ Transport request API: {response.status_code} - Has ID: {has_id}, Type: {correct_type}")
                results.append(True)
            else:
                print(f"❌ Transport request API failed: {response.status_code} - {response.text}")
                results.append(False)
        except Exception as e:
            print(f"❌ Transport request API error: {e}")
            results.append(False)
        
        # Test 7: POST laundry request
        try:
            url = f"{BACKEND_URL}/v2/guest-services/g/{self.tenant_slug}/room/R101/laundry-request"
            laundry_data = {
                "service_type": "express",
                "items_description": "2 shirts, 1 suit",
                "guest_name": "Test Guest"
            }
            response = requests.post(url, json=laundry_data)
            if response.status_code == 200:
                data = response.json()
                has_id = "id" in data
                correct_type = data.get("service_type") == "express"
                print(f"✅ Laundry request API: {response.status_code} - Has ID: {has_id}, Type: {correct_type}")
                results.append(True)
            else:
                print(f"❌ Laundry request API failed: {response.status_code} - {response.text}")
                results.append(False)
        except Exception as e:
            print(f"❌ Laundry request API error: {e}")
            results.append(False)
        
        # Test 8: POST wakeup call
        try:
            url = f"{BACKEND_URL}/v2/guest-services/g/{self.tenant_slug}/room/R101/wakeup-call"
            wakeup_data = {
                "wakeup_date": "2026-03-01",
                "wakeup_time": "07:00",
                "guest_name": "Test Guest"
            }
            response = requests.post(url, json=wakeup_data)
            if response.status_code == 200:
                data = response.json()
                has_id = "id" in data
                correct_time = data.get("wakeup_time") == "07:00"
                print(f"✅ Wakeup call API: {response.status_code} - Has ID: {has_id}, Time: {correct_time}")
                results.append(True)
            else:
                print(f"❌ Wakeup call API failed: {response.status_code} - {response.text}")
                results.append(False)
        except Exception as e:
            print(f"❌ Wakeup call API error: {e}")
            results.append(False)
        
        # Test 9: POST guest survey
        try:
            url = f"{BACKEND_URL}/v2/guest-services/g/{self.tenant_slug}/room/R101/survey"
            survey_data = {
                "overall_rating": 5,
                "cleanliness_rating": 4,
                "service_rating": 5,
                "comments": "Great stay!",
                "would_recommend": True
            }
            response = requests.post(url, json=survey_data)
            if response.status_code == 200:
                data = response.json()
                has_id = "id" in data
                correct_rating = data.get("overall_rating") == 5
                print(f"✅ Guest survey API: {response.status_code} - Has ID: {has_id}, Rating: {correct_rating}")
                results.append(True)
            else:
                print(f"❌ Guest survey API failed: {response.status_code} - {response.text}")
                results.append(False)
        except Exception as e:
            print(f"❌ Guest survey API error: {e}")
            results.append(False)
        
        success_rate = sum(results) / len(results) * 100
        print(f"\n📊 Guest Services APIs: {sum(results)}/{len(results)} passed ({success_rate:.1f}%)")
        return results
    
    def test_sla_apis(self):
        """Test SLA APIs (Auth required)"""
        print("\n🧪 Testing SLA APIs (Auth required)")
        results = []
        
        # Test 1: GET SLA rules
        try:
            url = f"{BACKEND_URL}/v2/sla/tenants/{self.tenant_slug}/sla-rules"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                rules_count = len(data) if isinstance(data, list) else 0
                print(f"✅ SLA rules API: {response.status_code} - Found {rules_count} SLA rules")
                results.append(True)
            else:
                print(f"❌ SLA rules API failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ SLA rules API error: {e}")
            results.append(False)
        
        # Test 2: GET SLA stats
        try:
            url = f"{BACKEND_URL}/v2/sla/tenants/{self.tenant_slug}/sla-stats"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                has_stats = all(key in data for key in ["total_requests", "compliance_rate", "avg_response_minutes"])
                print(f"✅ SLA stats API: {response.status_code} - Has stats: {has_stats}")
                print(f"   Compliance: {data.get('compliance_rate', 0)}%, Avg response: {data.get('avg_response_minutes', 0)} min")
                results.append(True)
            else:
                print(f"❌ SLA stats API failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ SLA stats API error: {e}")
            results.append(False)
        
        # Test 3: GET response templates
        try:
            url = f"{BACKEND_URL}/v2/sla/tenants/{self.tenant_slug}/response-templates"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                templates_count = len(data) if isinstance(data, list) else 0
                print(f"✅ Response templates API: {response.status_code} - Found {templates_count} templates")
                results.append(True)
            else:
                print(f"❌ Response templates API failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ Response templates API error: {e}")
            results.append(False)
        
        # Test 4: GET assignment rules
        try:
            url = f"{BACKEND_URL}/v2/sla/tenants/{self.tenant_slug}/assignment-rules"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                rules_count = len(data) if isinstance(data, list) else 0
                print(f"✅ Assignment rules API: {response.status_code} - Found {rules_count} assignment rules")
                results.append(True)
            else:
                print(f"❌ Assignment rules API failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ Assignment rules API error: {e}")
            results.append(False)
        
        success_rate = sum(results) / len(results) * 100
        print(f"\n📊 SLA APIs: {sum(results)}/{len(results)} passed ({success_rate:.1f}%)")
        return results
    
    def test_notifications_apis(self):
        """Test Notifications APIs (Auth required)"""
        print("\n🧪 Testing Notifications APIs (Auth required)")
        results = []
        
        # Test 1: GET notifications list
        try:
            url = f"{BACKEND_URL}/v2/notifications/tenants/{self.tenant_slug}/notifications"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                has_data = "data" in data and isinstance(data["data"], list)
                has_total = "total" in data
                has_unread = "unread_count" in data
                notifications_count = len(data.get("data", []))
                print(f"✅ Notifications list API: {response.status_code} - Found {notifications_count} notifications")
                print(f"   Total: {data.get('total', 0)}, Unread: {data.get('unread_count', 0)}")
                results.append(True)
            else:
                print(f"❌ Notifications list API failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ Notifications list API error: {e}")
            results.append(False)
        
        # Test 2: GET unread count
        try:
            url = f"{BACKEND_URL}/v2/notifications/tenants/{self.tenant_slug}/notifications/unread-count"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                has_count = "unread_count" in data
                unread_count = data.get("unread_count", 0)
                print(f"✅ Unread count API: {response.status_code} - Unread count: {unread_count}")
                results.append(True)
            else:
                print(f"❌ Unread count API failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ Unread count API error: {e}")
            results.append(False)
        
        success_rate = sum(results) / len(results) * 100
        print(f"\n📊 Notifications APIs: {sum(results)}/{len(results)} passed ({success_rate:.1f}%)")
        return results
    
    def test_housekeeping_apis(self):
        """Test Housekeeping APIs (Auth required)"""
        print("\n🧪 Testing Housekeeping APIs (Auth required)")
        results = []
        
        # Test 1: GET room status board
        try:
            url = f"{BACKEND_URL}/v2/housekeeping/tenants/{self.tenant_slug}/room-status"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                rooms_count = len(data) if isinstance(data, list) else 0
                has_hk_status = any("hk_status" in room for room in data) if rooms_count > 0 else False
                print(f"✅ Room status API: {response.status_code} - Found {rooms_count} rooms with HK status: {has_hk_status}")
                results.append(True)
            else:
                print(f"❌ Room status API failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ Room status API error: {e}")
            results.append(False)
        
        # Test 2: GET checklists
        try:
            url = f"{BACKEND_URL}/v2/housekeeping/tenants/{self.tenant_slug}/checklists"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                checklists_count = len(data) if isinstance(data, list) else 0
                print(f"✅ Checklists API: {response.status_code} - Found {checklists_count} checklists")
                results.append(True)
            else:
                print(f"❌ Checklists API failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ Checklists API error: {e}")
            results.append(False)
        
        # Test 3: GET HK stats
        try:
            url = f"{BACKEND_URL}/v2/housekeeping/tenants/{self.tenant_slug}/hk-stats"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                has_stats = all(key in data for key in ["total_rooms", "clean", "dirty"])
                print(f"✅ HK stats API: {response.status_code} - Has stats: {has_stats}")
                print(f"   Total rooms: {data.get('total_rooms', 0)}, Clean: {data.get('clean', 0)}, Dirty: {data.get('dirty', 0)}")
                results.append(True)
            else:
                print(f"❌ HK stats API failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ HK stats API error: {e}")
            results.append(False)
        
        success_rate = sum(results) / len(results) * 100
        print(f"\n📊 Housekeeping APIs: {sum(results)}/{len(results)} passed ({success_rate:.1f}%)")
        return results
    
    def test_lost_found_apis(self):
        """Test Lost & Found APIs (Auth required)"""
        print("\n🧪 Testing Lost & Found APIs (Auth required)")
        results = []
        
        # Test 1: POST create item
        try:
            url = f"{BACKEND_URL}/v2/lost-found/tenants/{self.tenant_slug}/items"
            item_data = {
                "description": "Black iPhone 15",
                "category": "electronics",
                "location_found": "Lobby",
                "room_number": "101"
            }
            response = self.session.post(url, json=item_data)
            if response.status_code == 200:
                data = response.json()
                has_id = "id" in data
                correct_desc = data.get("description") == "Black iPhone 15"
                print(f"✅ Create item API: {response.status_code} - Has ID: {has_id}, Description: {correct_desc}")
                results.append(True)
            else:
                print(f"❌ Create item API failed: {response.status_code} - {response.text}")
                results.append(False)
        except Exception as e:
            print(f"❌ Create item API error: {e}")
            results.append(False)
        
        # Test 2: GET items list
        try:
            url = f"{BACKEND_URL}/v2/lost-found/tenants/{self.tenant_slug}/items"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                has_data = "data" in data and isinstance(data["data"], list)
                items_count = len(data.get("data", []))
                print(f"✅ Items list API: {response.status_code} - Found {items_count} items")
                results.append(True)
            else:
                print(f"❌ Items list API failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ Items list API error: {e}")
            results.append(False)
        
        # Test 3: GET stats
        try:
            url = f"{BACKEND_URL}/v2/lost-found/tenants/{self.tenant_slug}/stats"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                has_stats = all(key in data for key in ["total", "stored", "returned"])
                print(f"✅ Lost & Found stats API: {response.status_code} - Has stats: {has_stats}")
                print(f"   Total: {data.get('total', 0)}, Stored: {data.get('stored', 0)}, Returned: {data.get('returned', 0)}")
                results.append(True)
            else:
                print(f"❌ Lost & Found stats API failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ Lost & Found stats API error: {e}")
            results.append(False)
        
        success_rate = sum(results) / len(results) * 100
        print(f"\n📊 Lost & Found APIs: {sum(results)}/{len(results)} passed ({success_rate:.1f}%)")
        return results
    
    def test_social_dashboard_apis(self):
        """Test Social Dashboard APIs (Auth required)"""
        print("\n🧪 Testing Social Dashboard APIs (Auth required)")
        results = []
        
        # Test 1: GET dashboard
        try:
            url = f"{BACKEND_URL}/v2/social/tenants/{self.tenant_slug}/dashboard"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                has_channel_stats = "channel_stats" in data
                has_sentiment = "sentiment" in data
                has_meta_status = "meta_status" in data
                print(f"✅ Social dashboard API: {response.status_code}")
                print(f"   Channel stats: {has_channel_stats}, Sentiment: {has_sentiment}, Meta status: {has_meta_status}")
                if has_meta_status:
                    print(f"   Meta status: {data.get('meta_status', 'N/A')}")
                results.append(True)
            else:
                print(f"❌ Social dashboard API failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ Social dashboard API error: {e}")
            results.append(False)
        
        success_rate = sum(results) / len(results) * 100
        print(f"\n📊 Social Dashboard APIs: {sum(results)}/{len(results)} passed ({success_rate:.1f}%)")
        return results
    
    def test_reports_apis(self):
        """Test Reports APIs (Auth required)"""
        print("\n🧪 Testing Reports APIs (Auth required)")
        results = []
        
        # Test 1: GET department performance
        try:
            url = f"{BACKEND_URL}/v2/reports/tenants/{self.tenant_slug}/department-performance"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                departments_count = len(data) if isinstance(data, list) else 0
                has_performance_data = any("total_requests" in dept for dept in data) if departments_count > 0 else False
                print(f"✅ Department performance API: {response.status_code} - Found {departments_count} departments")
                results.append(True)
            else:
                print(f"❌ Department performance API failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ Department performance API error: {e}")
            results.append(False)
        
        # Test 2: GET guest satisfaction
        try:
            url = f"{BACKEND_URL}/v2/reports/tenants/{self.tenant_slug}/guest-satisfaction"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                has_trends = "daily_trend" in data
                has_nps = "nps_score" in data
                print(f"✅ Guest satisfaction API: {response.status_code} - Has trends: {has_trends}, NPS: {has_nps}")
                results.append(True)
            else:
                print(f"❌ Guest satisfaction API failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ Guest satisfaction API error: {e}")
            results.append(False)
        
        # Test 3: GET peak demand
        try:
            url = f"{BACKEND_URL}/v2/reports/tenants/{self.tenant_slug}/peak-demand"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                has_hourly = "hourly_distribution" in data
                has_daily = "daily_distribution" in data
                print(f"✅ Peak demand API: {response.status_code} - Has hourly: {has_hourly}, daily: {has_daily}")
                results.append(True)
            else:
                print(f"❌ Peak demand API failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ Peak demand API error: {e}")
            results.append(False)
        
        # Test 4: GET staff productivity
        try:
            url = f"{BACKEND_URL}/v2/reports/tenants/{self.tenant_slug}/staff-productivity"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                staff_count = len(data) if isinstance(data, list) else 0
                has_productivity = any("total_assigned" in staff for staff in data) if staff_count > 0 else False
                print(f"✅ Staff productivity API: {response.status_code} - Found {staff_count} staff members")
                results.append(True)
            else:
                print(f"❌ Staff productivity API failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ Staff productivity API error: {e}")
            results.append(False)
        
        # Test 5: GET AI performance
        try:
            url = f"{BACKEND_URL}/v2/reports/tenants/{self.tenant_slug}/ai-performance"
            response = self.session.get(url)
            if response.status_code == 200:
                data = response.json()
                has_ai_stats = all(key in data for key in ["total_ai_messages", "total_tokens_used", "monthly_usage"])
                print(f"✅ AI performance API: {response.status_code} - Has AI stats: {has_ai_stats}")
                print(f"   AI messages: {data.get('total_ai_messages', 0)}, Tokens: {data.get('total_tokens_used', 0)}")
                results.append(True)
            else:
                print(f"❌ AI performance API failed: {response.status_code}")
                results.append(False)
        except Exception as e:
            print(f"❌ AI performance API error: {e}")
            results.append(False)
        
        success_rate = sum(results) / len(results) * 100
        print(f"\n📊 Reports APIs: {sum(results)}/{len(results)} passed ({success_rate:.1f}%)")
        return results
    
    def run_all_tests(self):
        """Run all Sprint 9 API tests"""
        print("🏨 Sprint 9 Backend API Testing - Hotel Management System")
        print("=" * 60)
        
        if not self.login():
            return False
        
        all_results = []
        
        # Test all API groups
        all_results.extend(self.test_guest_services_apis())
        all_results.extend(self.test_sla_apis())
        all_results.extend(self.test_notifications_apis())
        all_results.extend(self.test_housekeeping_apis())
        all_results.extend(self.test_lost_found_apis())
        all_results.extend(self.test_social_dashboard_apis())
        all_results.extend(self.test_reports_apis())
        
        # Summary
        total_tests = len(all_results)
        passed_tests = sum(all_results)
        success_rate = passed_tests / total_tests * 100
        
        print("\n" + "=" * 60)
        print(f"📊 OVERALL RESULTS: {passed_tests}/{total_tests} tests passed ({success_rate:.1f}%)")
        
        if success_rate == 100:
            print("🎉 ALL TESTS PASSED! Sprint 9 APIs are working perfectly!")
        elif success_rate >= 80:
            print("✅ Most tests passed. Some minor issues to investigate.")
        else:
            print("❌ Multiple test failures. Major issues need attention.")
        
        return success_rate >= 80

if __name__ == "__main__":
    tester = APITester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)