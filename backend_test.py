#!/usr/bin/env python3
"""
Sprint 11 Backend Testing - Security, Billing, Analytics, Compliance
Testing all 18 new Sprint 11 backend endpoints as requested.
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

def make_request(method, endpoint, data=None, headers=None, expected_status=None):
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
            print(f"❌ Unsupported method: {method}")
            return None
            
        print(f"{method} {endpoint} -> {response.status_code}")
        
        if expected_status and response.status_code != expected_status:
            print(f"❌ Expected {expected_status}, got {response.status_code}")
            print(f"Response: {response.text[:200]}")
            return None
            
        if response.status_code >= 400:
            print(f"❌ Error {response.status_code}: {response.text[:200]}")
            return None
            
        try:
            return response.json()
        except:
            return {"status": "ok", "status_code": response.status_code}
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None

def test_security_endpoints():
    """Test Enhanced Security Endpoints (1-4)"""
    global auth_token
    print("\n🔐 Testing Enhanced Security Endpoints...")
    
    # Test 1: Enhanced Login (should return token + csrf_token + session_id)
    print("Test 1: Enhanced Login with Security Features")
    result = make_request("POST", "/auth/login", {
        "email": LOGIN_EMAIL,
        "password": LOGIN_PASSWORD
    })
    
    if not result:
        print("❌ Enhanced login failed")
        return False
    
    required_fields = ["token", "csrf_token", "session_id"]
    missing = [f for f in required_fields if f not in result]
    if missing:
        print(f"❌ Missing security fields: {missing}")
        return False
    
    auth_token = result["token"]
    print(f"✅ Enhanced login successful with token, csrf_token: {result['csrf_token'][:10]}..., session_id: {result['session_id'][:8]}...")
    
    # Test 2: Refresh Token
    print("Test 2: Refresh Token")
    refresh_result = make_request("POST", "/auth/refresh", {
        "token": auth_token
    })
    
    if not refresh_result or "token" not in refresh_result or "csrf_token" not in refresh_result:
        print("❌ Refresh token failed")
        return False
    
    print(f"✅ Token refresh successful, new csrf_token: {refresh_result['csrf_token'][:10]}...")
    
    # Test 3: Sessions List
    print("Test 3: Sessions List")
    sessions_result = make_request("GET", "/auth/sessions")
    
    if not isinstance(sessions_result, list):
        print("❌ Sessions list failed")
        return False
    
    print(f"✅ Sessions list returned {len(sessions_result)} active session(s)")
    
    # Test 4: CSRF Token endpoint
    print("Test 4: CSRF Token Endpoint")
    csrf_result = make_request("GET", "/auth/csrf-token")
    
    if not csrf_result or "csrf_token" not in csrf_result:
        print("❌ CSRF token endpoint failed")
        return False
    
    print(f"✅ CSRF token endpoint working, token: {csrf_result['csrf_token'][:10]}...")
    
    return True

def test_plans_endpoint():
    """Test Plans Endpoint (5)"""
    print("\n📋 Testing Plans Endpoint...")
    
    # Test 5: Plans API
    print("Test 5: Plans API")
    result = make_request("GET", "/plans")
    
    if not result:
        print("❌ Plans API failed")
        return False
    
    # Should return object with basic/pro/enterprise keys with prices
    if not isinstance(result, dict):
        print("❌ Plans API should return object")
        return False
    
    required_plans = ["basic", "pro", "enterprise"]
    plan_names = list(result.keys())
    
    missing_plans = [p for p in required_plans if p not in plan_names]
    if missing_plans:
        print(f"❌ Missing plans: {missing_plans}")
        return False
    
    # Check for price info
    for plan_name, plan_data in result.items():
        if "price_monthly" not in plan_data:
            print(f"❌ Plan {plan_name} missing price_monthly")
            return False
    
    print(f"✅ Plans API working - found {len(result)} plans: {list(result.keys())}")
    return True

def test_usage_and_billing():
    """Test Usage and Billing Endpoints (6-8)"""
    print("\n💰 Testing Usage and Billing Endpoints...")
    
    # Test 6: Detailed Usage
    print("Test 6: Detailed Usage")
    usage_result = make_request("GET", "/tenants/grand-hotel/usage/detailed")
    
    if not usage_result:
        print("❌ Detailed usage failed")
        return False
    
    required_fields = ["metrics", "features"]
    missing = [f for f in required_fields if f not in usage_result]
    if missing:
        print(f"❌ Missing usage fields: {missing}")
        return False
    
    # Check for pct values in metrics
    metrics = usage_result.get("metrics", {})
    for metric_key, metric_data in metrics.items():
        if isinstance(metric_data, dict) and "pct" not in metric_data:
            print(f"⚠️ Metric {metric_key} missing percentage")
    
    print(f"✅ Detailed usage working - {len(metrics)} metrics, {len(usage_result.get('features', []))} features")
    
    # Test 7: Billing
    print("Test 7: Billing")
    billing_result = make_request("GET", "/tenants/grand-hotel/billing")
    
    if not billing_result:
        print("❌ Billing API failed")
        return False
    
    required_billing = ["billing_account", "subscription", "invoices"]
    missing = [f for f in required_billing if f not in billing_result]
    if missing:
        print(f"❌ Missing billing fields: {missing}")
        return False
    
    print(f"✅ Billing API working - account: {billing_result['billing_account'].get('id', 'N/A')[:8]}..., invoices: {len(billing_result.get('invoices', []))}")
    
    # Test 8: Stripe Webhook
    print("Test 8: Stripe Webhook")
    webhook_result = make_request("POST", "/billing/webhook/stripe", {
        "type": "invoice.paid",
        "data": {"object": {"customer": "test"}}
    })
    
    if not webhook_result or webhook_result.get("status") != "processed":
        print("❌ Stripe webhook failed")
        return False
    
    print("✅ Stripe webhook working - returned 'processed' status")
    return True

def test_analytics_endpoints():
    """Test Analytics Endpoints (9-11)"""
    print("\n📊 Testing Analytics Endpoints...")
    
    # Test 9: Revenue Analytics
    print("Test 9: Revenue Analytics")
    revenue_result = make_request("GET", "/tenants/grand-hotel/analytics/revenue")
    
    if not revenue_result:
        print("❌ Revenue analytics failed")
        return False
    
    required_revenue = ["total_revenue", "upsell_conversion_rate", "revpar", "daily_revenue"]
    missing = [f for f in required_revenue if f not in revenue_result]
    if missing:
        print(f"❌ Missing revenue fields: {missing}")
        return False
    
    print(f"✅ Revenue analytics working - total: {revenue_result.get('total_revenue', 0)}, revpar: {revenue_result.get('revpar', 0)}")
    
    # Test 10: Staff Performance
    print("Test 10: Staff Performance")
    staff_result = make_request("GET", "/tenants/grand-hotel/analytics/staff-performance")
    
    if not staff_result:
        print("❌ Staff performance failed")
        return False
    
    if "staff" not in staff_result or not isinstance(staff_result["staff"], list):
        print("❌ Staff performance should return staff array")
        return False
    
    # Check for efficiency_score in staff array
    staff_list = staff_result["staff"]
    if staff_list:
        for staff_member in staff_list:
            if "efficiency_score" not in staff_member:
                print("❌ Staff member missing efficiency_score")
                return False
    
    print(f"✅ Staff performance working - {len(staff_list)} staff members with efficiency scores")
    
    # Test 11: Investor Metrics
    print("Test 11: Investor Metrics")
    investor_result = make_request("GET", "/system/investor-metrics")
    
    if not investor_result:
        print("❌ Investor metrics failed")
        return False
    
    required_investor = ["mrr", "arr", "active_tenants", "total_messages_processed", "ai_replies_generated", "plan_distribution"]
    missing = [f for f in required_investor if f not in investor_result]
    if missing:
        print(f"❌ Missing investor fields: {missing}")
        return False
    
    print(f"✅ Investor metrics working - MRR: {investor_result.get('mrr', 0)}, active tenants: {investor_result.get('active_tenants', 0)}")
    return True

def test_compliance_endpoints():
    """Test Compliance Endpoints (12-15)"""
    print("\n🛡️ Testing Compliance Endpoints...")
    
    # First, get a contact ID for compliance export
    contacts_result = make_request("GET", "/tenants/grand-hotel/contacts")
    if not contacts_result or "data" not in contacts_result or not contacts_result["data"]:
        print("⚠️ No contacts found for compliance testing")
        return False
    
    contact_id = contacts_result["data"][0]["id"]
    
    # Test 12: Compliance Export
    print("Test 12: Compliance Export")
    export_result = make_request("POST", f"/tenants/grand-hotel/compliance/export/{contact_id}")
    
    if not export_result:
        print("❌ Compliance export failed")
        return False
    
    print(f"✅ Compliance export working for contact: {contact_id[:8]}...")
    
    # Test 13: Retention Policy
    print("Test 13: Retention Policy")
    retention_result = make_request("GET", "/tenants/grand-hotel/compliance/retention")
    
    if not retention_result:
        print("❌ Retention policy failed")
        return False
    
    required_retention = ["retention_months", "auto_purge"]
    missing = [f for f in required_retention if f not in retention_result]
    if missing:
        print(f"❌ Missing retention fields: {missing}")
        return False
    
    print(f"✅ Retention policy working - {retention_result.get('retention_months', 0)} months, auto_purge: {retention_result.get('auto_purge', False)}")
    
    # Test 14: Update Retention
    print("Test 14: Update Retention")
    update_result = make_request("PATCH", "/tenants/grand-hotel/compliance/retention", {
        "auto_purge": True,
        "retention_months": 12
    })
    
    if not update_result or update_result.get("retention_months") != 12:
        print("❌ Update retention failed")
        return False
    
    print("✅ Update retention working - set to 12 months with auto_purge")
    
    # Test 15: Retention Cleanup
    print("Test 15: Retention Cleanup")
    cleanup_result = make_request("POST", "/compliance/retention-cleanup")
    
    if not cleanup_result or cleanup_result.get("status") != "completed":
        print("❌ Retention cleanup failed")
        return False
    
    print("✅ Retention cleanup working - status: completed")
    return True

def test_referral_and_growth():
    """Test Referral and Growth Endpoints (16-17)"""
    print("\n🚀 Testing Referral and Growth Endpoints...")
    
    # First get referral data to get the code
    referral_result = make_request("GET", "/tenants/grand-hotel/growth/referral")
    if not referral_result or "code" not in referral_result:
        print("❌ Could not get referral code")
        return False
    
    referral_code = referral_result["code"]
    
    # Test 16: Referral Landing (use the full code, not REF- prefix)
    print("Test 16: Referral Landing")
    landing_result = make_request("GET", f"/r/{referral_code}")
    
    if not landing_result:
        print(f"❌ Referral landing failed for {referral_code}")
        return False
    
    required_landing = ["referrer_name", "features", "cta_text"]
    missing = [f for f in required_landing if f not in landing_result]
    if missing:
        print(f"❌ Missing landing fields: {missing}")
        return False
    
    print(f"✅ Referral landing working - referrer: {landing_result.get('referrer_name', 'N/A')}")
    
    # Test 17: Growth Stats
    print("Test 17: Growth Stats")
    growth_result = make_request("GET", "/tenants/grand-hotel/growth/stats")
    
    if not growth_result:
        print("❌ Growth stats failed")
        return False
    
    required_growth = ["referral", "events", "total_clicks"]
    missing = [f for f in required_growth if f not in growth_result]
    if missing:
        print(f"❌ Missing growth fields: {missing}")
        return False
    
    print(f"✅ Growth stats working - clicks: {growth_result.get('total_clicks', 0)}, signups: {growth_result.get('total_signups', 0)}")
    return True

def test_analytics_overview():
    """Test Analytics Overview Endpoint (18)"""
    print("\n📈 Testing Analytics Overview...")
    
    # Test 18: Analytics Overview
    print("Test 18: Analytics Overview")
    analytics_result = make_request("GET", "/tenants/grand-hotel/analytics")
    
    if not analytics_result:
        print("❌ Analytics overview failed")
        return False
    
    required_analytics = ["revenue", "guests", "operations", "ai"]
    missing = [f for f in required_analytics if f not in analytics_result]
    if missing:
        print(f"❌ Missing analytics sections: {missing}")
        return False
    
    print(f"✅ Analytics overview working - all sections present: {list(analytics_result.keys())}")
    return True

def run_all_tests():
    """Run all Sprint 11 endpoint tests"""
    print("🚀 Starting Sprint 11 Backend Testing")
    print(f"Base URL: {BASE_URL}")
    print("Testing 18 new endpoints from Sprint 11")
    print("=" * 60)
    
    test_results = []
    
    # Test 1-4: Security
    test_results.append(("Security Endpoints (1-4)", test_security_endpoints()))
    
    # Test 5: Plans
    test_results.append(("Plans Endpoint (5)", test_plans_endpoint()))
    
    # Test 6-8: Usage and Billing
    test_results.append(("Usage & Billing (6-8)", test_usage_and_billing()))
    
    # Test 9-11: Analytics
    test_results.append(("Analytics (9-11)", test_analytics_endpoints()))
    
    # Test 12-15: Compliance
    test_results.append(("Compliance (12-15)", test_compliance_endpoints()))
    
    # Test 16-17: Referral/Growth
    test_results.append(("Referral/Growth (16-17)", test_referral_and_growth()))
    
    # Test 18: Analytics Overview
    test_results.append(("Analytics Overview (18)", test_analytics_overview()))
    
    print("\n" + "=" * 60)
    print("🏁 Sprint 11 Testing Results:")
    
    passed_count = 0
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed_count += 1
    
    total_tests = len(test_results)
    print(f"\n📊 Summary: {passed_count}/{total_tests} test groups passed")
    
    if passed_count == total_tests:
        print("🎉 ALL SPRINT 11 ENDPOINTS WORKING!")
        return True
    else:
        print(f"❌ {total_tests - passed_count} test group(s) failed")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)