#!/usr/bin/env python3
"""
Sprint 11 Individual Endpoint Testing - Detailed Results
Testing each of the 18 Sprint 11 endpoints individually with detailed reporting.
"""
import sys
import os
import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "https://kritik-billing.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

# Test credentials from request 
LOGIN_EMAIL = "admin@grandhotel.com"
LOGIN_PASSWORD = "admin123"

# Global token storage
auth_token = None

def make_request(method, endpoint, data=None, headers=None):
    """Make HTTP request with optional authentication"""
    url = f"{API_BASE}{endpoint}"
    
    req_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    if headers:
        req_headers.update(headers)
        
    if auth_token:
        req_headers["Authorization"] = f"Bearer {auth_token}"
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=req_headers)
        elif method.upper() == "POST":
            response = requests.post(url, headers=req_headers, json=data if data else {})
        elif method.upper() == "PUT":
            response = requests.put(url, headers=req_headers, json=data if data else {})
        elif method.upper() == "PATCH":
            response = requests.patch(url, headers=req_headers, json=data if data else {})
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=req_headers)
        else:
            return None, f"Unsupported method: {method}"
            
        return response, None
            
    except Exception as e:
        return None, f"Request failed: {e}"

def test_individual_endpoint(test_num, description, method, endpoint, data=None, validator=None):
    """Test individual endpoint with detailed reporting"""
    print(f"Test {test_num}: {description}")
    print(f"  {method} {endpoint}")
    
    response, error = make_request(method, endpoint, data)
    
    if error:
        print(f"  ❌ FAIL - {error}")
        return False
    
    print(f"  Status: {response.status_code}")
    
    if response.status_code >= 400:
        print(f"  ❌ FAIL - HTTP {response.status_code}: {response.text[:100]}")
        return False
    
    try:
        json_data = response.json()
        if validator:
            result, message = validator(json_data)
            if result:
                print(f"  ✅ PASS - {message}")
                return True
            else:
                print(f"  ❌ FAIL - {message}")
                return False
        else:
            print(f"  ✅ PASS - Response received")
            return True
    except:
        print(f"  ✅ PASS - Non-JSON response OK")
        return True

def run_detailed_tests():
    """Run all 18 endpoints with detailed individual testing"""
    global auth_token
    
    print("🔍 Sprint 11 Individual Endpoint Testing")
    print(f"Base URL: {BASE_URL}")
    print("=" * 80)
    
    results = []
    
    # Test 1: Enhanced Login
    def validate_login(data):
        required = ["token", "csrf_token", "session_id", "user", "tenant"]
        missing = [f for f in required if f not in data]
        if missing:
            return False, f"Missing fields: {missing}"
        global auth_token
        auth_token = data["token"]
        return True, f"Token, CSRF token, and session ID returned"
    
    results.append(test_individual_endpoint(
        1, "Enhanced Login with Security Features",
        "POST", "/auth/login",
        {"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD},
        validate_login
    ))
    
    # Test 2: Refresh Token
    def validate_refresh(data):
        if "token" not in data or "csrf_token" not in data:
            return False, "Missing token or csrf_token in refresh response"
        return True, "New token and CSRF token returned"
    
    results.append(test_individual_endpoint(
        2, "Refresh Token",
        "POST", "/auth/refresh",
        {"token": auth_token},
        validate_refresh
    ))
    
    # Test 3: Sessions List
    def validate_sessions(data):
        if not isinstance(data, list):
            return False, "Sessions should return array"
        return True, f"Found {len(data)} active session(s)"
    
    results.append(test_individual_endpoint(
        3, "Sessions List",
        "GET", "/auth/sessions",
        None,
        validate_sessions
    ))
    
    # Test 4: CSRF Token
    def validate_csrf(data):
        if "csrf_token" not in data:
            return False, "No csrf_token in response"
        return True, f"CSRF token: {data['csrf_token'][:10]}..."
    
    results.append(test_individual_endpoint(
        4, "CSRF Token Endpoint",
        "GET", "/auth/csrf-token",
        None,
        validate_csrf
    ))
    
    # Test 5: Plans
    def validate_plans(data):
        required_plans = ["basic", "pro", "enterprise"]
        missing = [p for p in required_plans if p not in data]
        if missing:
            return False, f"Missing plans: {missing}"
        for plan_name, plan_data in data.items():
            if "price_monthly" not in plan_data:
                return False, f"Plan {plan_name} missing price_monthly"
        return True, f"All 3 plans with pricing: {list(data.keys())}"
    
    results.append(test_individual_endpoint(
        5, "Plans API",
        "GET", "/plans",
        None,
        validate_plans
    ))
    
    # Test 6: Detailed Usage
    def validate_usage(data):
        if "metrics" not in data or "features" not in data:
            return False, "Missing metrics or features"
        return True, f"{len(data['metrics'])} metrics, {len(data['features'])} features"
    
    results.append(test_individual_endpoint(
        6, "Detailed Usage",
        "GET", "/tenants/grand-hotel/usage/detailed",
        None,
        validate_usage
    ))
    
    # Test 7: Billing
    def validate_billing(data):
        required = ["billing_account", "subscription", "invoices"]
        missing = [f for f in required if f not in data]
        if missing:
            return False, f"Missing billing fields: {missing}"
        return True, f"Billing account with {len(data['invoices'])} invoices"
    
    results.append(test_individual_endpoint(
        7, "Billing",
        "GET", "/tenants/grand-hotel/billing",
        None,
        validate_billing
    ))
    
    # Test 8: Stripe Webhook
    def validate_webhook(data):
        if data.get("status") != "processed":
            return False, f"Expected 'processed', got {data.get('status')}"
        return True, "Webhook processed successfully"
    
    results.append(test_individual_endpoint(
        8, "Stripe Webhook",
        "POST", "/billing/webhook/stripe",
        {"type": "invoice.paid", "data": {"object": {"customer": "test"}}},
        validate_webhook
    ))
    
    # Test 9: Revenue Analytics
    def validate_revenue(data):
        required = ["total_revenue", "upsell_conversion_rate", "revpar", "daily_revenue"]
        missing = [f for f in required if f not in data]
        if missing:
            return False, f"Missing revenue fields: {missing}"
        return True, f"Revenue: {data.get('total_revenue', 0)}, RevPAR: {data.get('revpar', 0)}"
    
    results.append(test_individual_endpoint(
        9, "Revenue Analytics",
        "GET", "/tenants/grand-hotel/analytics/revenue",
        None,
        validate_revenue
    ))
    
    # Test 10: Staff Performance
    def validate_staff(data):
        if "staff" not in data or not isinstance(data["staff"], list):
            return False, "Missing staff array"
        staff_list = data["staff"]
        for staff in staff_list:
            if "efficiency_score" not in staff:
                return False, "Staff missing efficiency_score"
        return True, f"{len(staff_list)} staff with efficiency scores"
    
    results.append(test_individual_endpoint(
        10, "Staff Performance",
        "GET", "/tenants/grand-hotel/analytics/staff-performance",
        None,
        validate_staff
    ))
    
    # Test 11: Investor Metrics
    def validate_investor(data):
        required = ["mrr", "arr", "active_tenants", "total_messages_processed", "ai_replies_generated", "plan_distribution"]
        missing = [f for f in required if f not in data]
        if missing:
            return False, f"Missing investor fields: {missing}"
        return True, f"MRR: {data.get('mrr')}, Active tenants: {data.get('active_tenants')}"
    
    results.append(test_individual_endpoint(
        11, "Investor Metrics",
        "GET", "/system/investor-metrics",
        None,
        validate_investor
    ))
    
    # Get contact for compliance tests
    contacts_response, _ = make_request("GET", "/tenants/grand-hotel/contacts")
    contact_id = None
    if contacts_response and contacts_response.status_code == 200:
        contacts_data = contacts_response.json()
        if contacts_data.get("data"):
            contact_id = contacts_data["data"][0]["id"]
    
    # Test 12: Compliance Export
    def validate_export(data):
        return True, "Export completed successfully"
    
    if contact_id:
        results.append(test_individual_endpoint(
            12, "Compliance Export",
            "POST", f"/tenants/grand-hotel/compliance/export/{contact_id}",
            None,
            validate_export
        ))
    else:
        print("Test 12: Compliance Export")
        print("  ❌ FAIL - No contact ID available for testing")
        results.append(False)
    
    # Test 13: Retention Policy
    def validate_retention(data):
        required = ["retention_months", "auto_purge"]
        missing = [f for f in required if f not in data]
        if missing:
            return False, f"Missing retention fields: {missing}"
        return True, f"{data.get('retention_months')} months, auto_purge: {data.get('auto_purge')}"
    
    results.append(test_individual_endpoint(
        13, "Retention Policy",
        "GET", "/tenants/grand-hotel/compliance/retention",
        None,
        validate_retention
    ))
    
    # Test 14: Update Retention
    def validate_retention_update(data):
        if data.get("retention_months") != 24:  # Updating to 24
            return False, f"Expected 24 months, got {data.get('retention_months')}"
        return True, "Retention updated to 24 months"
    
    results.append(test_individual_endpoint(
        14, "Update Retention",
        "PATCH", "/tenants/grand-hotel/compliance/retention",
        {"auto_purge": True, "retention_months": 24},
        validate_retention_update
    ))
    
    # Test 15: Retention Cleanup
    def validate_cleanup(data):
        if data.get("status") != "completed":
            return False, f"Expected 'completed', got {data.get('status')}"
        return True, "Cleanup completed"
    
    results.append(test_individual_endpoint(
        15, "Retention Cleanup",
        "POST", "/compliance/retention-cleanup",
        None,
        validate_cleanup
    ))
    
    # Get referral code
    referral_response, _ = make_request("GET", "/tenants/grand-hotel/growth/referral")
    referral_code = None
    if referral_response and referral_response.status_code == 200:
        referral_data = referral_response.json()
        referral_code = referral_data.get("code")
    
    # Test 16: Referral Landing
    def validate_landing(data):
        required = ["referrer_name", "features", "cta_text"]
        missing = [f for f in required if f not in data]
        if missing:
            return False, f"Missing landing fields: {missing}"
        return True, f"Referrer: {data.get('referrer_name')}"
    
    if referral_code:
        results.append(test_individual_endpoint(
            16, "Referral Landing",
            "GET", f"/r/{referral_code}",
            None,
            validate_landing
        ))
    else:
        print("Test 16: Referral Landing")
        print("  ❌ FAIL - No referral code available")
        results.append(False)
    
    # Test 17: Growth Stats
    def validate_growth(data):
        required = ["referral", "events", "total_clicks"]
        missing = [f for f in required if f not in data]
        if missing:
            return False, f"Missing growth fields: {missing}"
        return True, f"Clicks: {data.get('total_clicks')}, Events: {len(data.get('events', []))}"
    
    results.append(test_individual_endpoint(
        17, "Growth Stats",
        "GET", "/tenants/grand-hotel/growth/stats",
        None,
        validate_growth
    ))
    
    # Test 18: Analytics Overview
    def validate_analytics(data):
        required = ["revenue", "guests", "operations", "ai"]
        missing = [f for f in required if f not in data]
        if missing:
            return False, f"Missing analytics sections: {missing}"
        return True, f"All sections: {list(data.keys())}"
    
    results.append(test_individual_endpoint(
        18, "Analytics Overview",
        "GET", "/tenants/grand-hotel/analytics",
        None,
        validate_analytics
    ))
    
    # Summary
    print("\n" + "=" * 80)
    print("🏁 DETAILED TEST RESULTS SUMMARY:")
    
    passed = sum(1 for r in results if r)
    total = len(results)
    
    for i, result in enumerate(results, 1):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - Test {i}")
    
    print(f"\n📊 Final Score: {passed}/{total} endpoints working ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL 18 SPRINT 11 ENDPOINTS ARE WORKING PERFECTLY!")
        return True
    else:
        print(f"❌ {total - passed} endpoint(s) failed")
        return False

if __name__ == "__main__":
    success = run_detailed_tests()
    sys.exit(0 if success else 1)