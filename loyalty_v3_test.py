#!/usr/bin/env python3
"""
Loyalty Engine V3 & Loyalty Analytics V3 Testing
Testing all new loyalty engine and analytics endpoints as specified in the review request.
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
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=req_headers)
        else:
            print(f"❌ Unsupported method: {method}")
            return None
            
        print(f"{method} {endpoint} -> {response.status_code}")
        
        if expected_status and response.status_code != expected_status:
            print(f"❌ Expected {expected_status}, got {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return None
            
        if response.status_code >= 400:
            print(f"❌ Error {response.status_code}: {response.text[:500]}")
            return None
            
        try:
            return response.json()
        except:
            return {"status": "ok", "status_code": response.status_code}
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None

def authenticate():
    """Login to get auth token"""
    global auth_token
    
    print("🔐 Authenticating...")
    result = make_request("POST", "/auth/login", {
        "email": LOGIN_EMAIL,
        "password": LOGIN_PASSWORD
    })
    
    if not result or "token" not in result:
        print("❌ Authentication failed")
        return False
        
    auth_token = result["token"]
    print("✅ Authentication successful")
    return True

def test_loyalty_overview():
    """Test 2: GET /api/v2/loyalty-engine/tenants/grand-hotel/overview"""
    print("\n📊 Testing Loyalty Overview Dashboard...")
    
    result = make_request("GET", "/v2/loyalty-engine/tenants/grand-hotel/overview")
    
    if not result:
        print("❌ Loyalty overview failed")
        return False
    
    # Check required fields
    required_fields = ["total_members", "points_in_circulation", "tier_distribution", 
                      "total_referrals", "total_campaigns", "point_rules_count", "rewards_count"]
    
    missing = [f for f in required_fields if f not in result]
    if missing:
        print(f"❌ Missing fields: {missing}")
        return False
    
    print(f"✅ Total members: {result['total_members']}")
    print(f"✅ Points in circulation: {result['points_in_circulation']}")
    print(f"✅ Total referrals: {result['total_referrals']}")
    print(f"✅ Total campaigns: {result['total_campaigns']}")
    print(f"✅ Point rules count: {result['point_rules_count']}")
    print(f"✅ Rewards count: {result['rewards_count']}")
    
    # Store member info for later use in digital card test
    global loyalty_members
    loyalty_members = result
    
    print("✅ Loyalty overview dashboard working correctly")
    return True

def test_point_rules():
    """Test 3: GET /api/v2/loyalty-engine/tenants/grand-hotel/point-rules"""
    print("\n🎯 Testing Point Rules...")
    
    result = make_request("GET", "/v2/loyalty-engine/tenants/grand-hotel/point-rules")
    
    if not result:
        print("❌ Point rules failed")
        return False
    
    data = result.get("data", [])
    total = result.get("total", 0)
    
    if total < 8:
        print(f"❌ Expected at least 8 rules, got {total}")
        return False
    
    # Check rule types
    rule_types = set()
    for rule in data:
        rule_type = rule.get("rule_type", "")
        rule_types.add(rule_type)
        
        # Verify rule structure
        required_fields = ["name", "rule_type", "condition", "points"]
        missing = [f for f in required_fields if f not in rule]
        if missing:
            print(f"❌ Rule {rule.get('name')} missing fields: {missing}")
            return False
    
    expected_types = {"accommodation", "spend", "activity", "custom"}
    if not expected_types.issubset(rule_types):
        print(f"❌ Missing rule types. Expected: {expected_types}, Got: {rule_types}")
        return False
    
    print(f"✅ Found {total} point rules with types: {list(rule_types)}")
    
    # Show sample rules
    for rule in data[:3]:
        print(f"   - {rule['name']}: {rule['rule_type']} ({rule['points']} points)")
    
    print("✅ Point rules API working correctly")
    return True

def test_tiers():
    """Test 4: GET /api/v2/loyalty-engine/tenants/grand-hotel/tiers"""
    print("\n🏆 Testing Tier Configuration...")
    
    result = make_request("GET", "/v2/loyalty-engine/tenants/grand-hotel/tiers")
    
    if not result:
        print("❌ Tiers API failed")
        return False
    
    tiers = result.get("tiers", [])
    
    if len(tiers) != 4:
        print(f"❌ Expected 4 tiers, got {len(tiers)}")
        return False
    
    expected_names = {"Bronz", "Gumus", "Altin", "Platin"}
    tier_names = {tier.get("name") for tier in tiers}
    
    if expected_names != tier_names:
        print(f"❌ Expected tiers: {expected_names}, Got: {tier_names}")
        return False
    
    # Verify tier structure
    for tier in tiers:
        required_fields = ["name", "slug", "min_points", "color", "benefits", "multiplier"]
        missing = [f for f in required_fields if f not in tier]
        if missing:
            print(f"❌ Tier {tier.get('name')} missing fields: {missing}")
            return False
    
    print(f"✅ Found 4 tiers: {list(tier_names)}")
    
    # Show tier details
    for tier in sorted(tiers, key=lambda t: t.get("min_points", 0)):
        print(f"   - {tier['name']}: {tier['min_points']} points, {tier['multiplier']}x multiplier")
    
    print("✅ Tier configuration API working correctly")
    return True

def test_tier_evaluation():
    """Test 5: POST /api/v2/loyalty-engine/tenants/grand-hotel/tiers/evaluate"""
    print("\n⚖️ Testing Tier Evaluation...")
    
    result = make_request("POST", "/v2/loyalty-engine/tenants/grand-hotel/tiers/evaluate")
    
    if not result:
        print("❌ Tier evaluation failed")
        return False
    
    # Check response structure
    required_fields = ["evaluated", "upgraded", "downgraded"]
    missing = [f for f in required_fields if f not in result]
    if missing:
        print(f"❌ Missing evaluation fields: {missing}")
        return False
    
    print(f"✅ Evaluated {result['evaluated']} members")
    print(f"✅ Upgraded: {result['upgraded']}")
    print(f"✅ Downgraded: {result['downgraded']}")
    
    print("✅ Tier evaluation working correctly")
    return True

def test_rewards_enhanced():
    """Test 6: GET /api/v2/loyalty-engine/tenants/grand-hotel/rewards-enhanced"""
    print("\n🎁 Testing Enhanced Rewards Catalog...")
    
    result = make_request("GET", "/v2/loyalty-engine/tenants/grand-hotel/rewards-enhanced")
    
    if not result:
        print("❌ Enhanced rewards failed")
        return False
    
    data = result.get("data", [])
    total = result.get("total", 0)
    
    if total < 9:
        print(f"❌ Expected at least 9 rewards, got {total}")
        return False
    
    # Check for partner and seasonal rewards
    has_partner = False
    has_seasonal = False
    categories = set()
    
    for reward in data:
        if reward.get("is_partner"):
            has_partner = True
        if reward.get("is_seasonal"):
            has_seasonal = True
        categories.add(reward.get("category", ""))
        
        # Verify reward structure
        required_fields = ["name", "points_cost", "category", "min_tier"]
        missing = [f for f in required_fields if f not in reward]
        if missing:
            print(f"❌ Reward {reward.get('name')} missing fields: {missing}")
            return False
    
    if not has_partner:
        print("❌ No partner rewards found")
        return False
    
    if not has_seasonal:
        print("❌ No seasonal rewards found")
        return False
    
    print(f"✅ Found {total} rewards with partner and seasonal options")
    print(f"✅ Categories: {list(categories)}")
    
    # Show sample rewards
    for reward in data[:3]:
        partner_text = "(Partner)" if reward.get("is_partner") else ""
        seasonal_text = "(Seasonal)" if reward.get("is_seasonal") else ""
        print(f"   - {reward['name']}: {reward['points_cost']} points {partner_text}{seasonal_text}")
    
    print("✅ Enhanced rewards catalog working correctly")
    return True

def test_campaigns():
    """Test 7: GET /api/v2/loyalty-engine/tenants/grand-hotel/campaigns"""
    print("\n📢 Testing Loyalty Campaigns...")
    
    result = make_request("GET", "/v2/loyalty-engine/tenants/grand-hotel/campaigns")
    
    if not result:
        print("❌ Campaigns API failed")
        return False
    
    data = result.get("data", [])
    total = result.get("total", 0)
    
    if total < 4:
        print(f"❌ Expected at least 4 campaigns, got {total}")
        return False
    
    # Check campaign types
    campaign_types = set()
    for campaign in data:
        campaign_type = campaign.get("campaign_type", "")
        campaign_types.add(campaign_type)
        
        # Verify campaign structure
        required_fields = ["name", "campaign_type", "status", "target_segment"]
        missing = [f for f in required_fields if f not in campaign]
        if missing:
            print(f"❌ Campaign {campaign.get('name')} missing fields: {missing}")
            return False
    
    print(f"✅ Found {total} campaigns")
    print(f"✅ Campaign types: {list(campaign_types)}")
    
    # Show sample campaigns
    for campaign in data[:3]:
        print(f"   - {campaign['name']}: {campaign['campaign_type']} ({campaign.get('status', 'unknown')})")
    
    print("✅ Campaigns API working correctly")
    return True

def test_referral_stats():
    """Test 8: GET /api/v2/loyalty-engine/tenants/grand-hotel/referral/stats"""
    print("\n👥 Testing Referral Stats...")
    
    result = make_request("GET", "/v2/loyalty-engine/tenants/grand-hotel/referral/stats")
    
    if not result:
        print("❌ Referral stats failed")
        return False
    
    # Check required fields
    required_fields = ["total_referrals", "successful", "pending", "total_points_given", 
                      "top_referrers", "config"]
    missing = [f for f in required_fields if f not in result]
    if missing:
        print(f"❌ Missing referral stats fields: {missing}")
        return False
    
    print(f"✅ Total referrals: {result['total_referrals']}")
    print(f"✅ Successful: {result['successful']}")
    print(f"✅ Pending: {result['pending']}")
    print(f"✅ Total points given: {result['total_points_given']}")
    print(f"✅ Top referrers: {len(result['top_referrers'])}")
    
    # Check config structure
    config = result.get("config", {})
    config_fields = ["enabled", "referrer_points", "referee_points"]
    missing_config = [f for f in config_fields if f not in config]
    if missing_config:
        print(f"❌ Missing config fields: {missing_config}")
        return False
    
    print(f"✅ Referral config: {config['referrer_points']} points for referrer, {config['referee_points']} for referee")
    
    print("✅ Referral stats API working correctly")
    return True

def test_referral_list():
    """Test 9: GET /api/v2/loyalty-engine/tenants/grand-hotel/referral/list"""
    print("\n📋 Testing Referral List...")
    
    result = make_request("GET", "/v2/loyalty-engine/tenants/grand-hotel/referral/list")
    
    if not result:
        print("❌ Referral list failed")
        return False
    
    # Check response structure
    required_fields = ["data", "total", "page"]
    missing = [f for f in required_fields if f not in result]
    if missing:
        print(f"❌ Missing referral list fields: {missing}")
        return False
    
    data = result.get("data", [])
    total = result.get("total", 0)
    
    print(f"✅ Found {total} referral entries")
    
    # If we have referrals, check structure
    if data:
        referral = data[0]
        ref_fields = ["referrer_contact_id", "referee_contact_id", "status", "referrer_name", "referee_name"]
        missing_ref = [f for f in ref_fields if f not in referral]
        if missing_ref:
            print(f"❌ Missing referral fields: {missing_ref}")
            return False
        
        print(f"   - {referral['referrer_name']} -> {referral['referee_name']} ({referral['status']})")
    
    print("✅ Referral list API working correctly")
    return True

def test_communication_prefs():
    """Test 10: GET /api/v2/loyalty-engine/tenants/grand-hotel/communication-prefs"""
    print("\n📨 Testing Communication Preferences...")
    
    result = make_request("GET", "/v2/loyalty-engine/tenants/grand-hotel/communication-prefs")
    
    if not result:
        print("❌ Communication prefs failed")
        return False
    
    # Check required fields
    required_fields = ["email_enabled", "sms_enabled", "whatsapp_enabled", "push_enabled", 
                      "inapp_enabled", "birthday_campaign", "anniversary_campaign"]
    missing = [f for f in required_fields if f not in result]
    if missing:
        print(f"❌ Missing communication prefs fields: {missing}")
        return False
    
    print(f"✅ Email enabled: {result['email_enabled']}")
    print(f"✅ SMS enabled: {result['sms_enabled']}")
    print(f"✅ WhatsApp enabled: {result['whatsapp_enabled']}")
    print(f"✅ Push enabled: {result['push_enabled']}")
    print(f"✅ In-app enabled: {result['inapp_enabled']}")
    print(f"✅ Birthday campaigns: {result['birthday_campaign']}")
    print(f"✅ Anniversary campaigns: {result['anniversary_campaign']}")
    
    print("✅ Communication preferences API working correctly")
    return True

def test_rfm_analysis():
    """Test 11: GET /api/v2/loyalty-analytics/tenants/grand-hotel/rfm"""
    print("\n📈 Testing RFM Analysis...")
    
    result = make_request("GET", "/v2/loyalty-analytics/tenants/grand-hotel/rfm")
    
    if not result:
        print("❌ RFM analysis failed")
        return False
    
    # Check required fields
    required_fields = ["data", "total", "segment_distribution", "avg_rfm"]
    missing = [f for f in required_fields if f not in result]
    if missing:
        print(f"❌ Missing RFM fields: {missing}")
        return False
    
    data = result.get("data", [])
    segment_dist = result.get("segment_distribution", {})
    
    print(f"✅ Analyzed {len(data)} members")
    print(f"✅ Segment distribution: {segment_dist}")
    
    # If we have data, check member structure
    if data:
        member = data[0]
        member_fields = ["contact_id", "name", "r_score", "f_score", "m_score", "segment"]
        missing_member = [f for f in member_fields if f not in member]
        if missing_member:
            print(f"❌ Missing member fields: {missing_member}")
            return False
        
        print(f"   Sample: {member['name']} - RFM({member['r_score']},{member['f_score']},{member['m_score']}) -> {member['segment']}")
    
    print("✅ RFM analysis working correctly")
    return True

def test_clv_analysis():
    """Test 12: GET /api/v2/loyalty-analytics/tenants/grand-hotel/clv"""
    print("\n💰 Testing CLV Analysis...")
    
    result = make_request("GET", "/v2/loyalty-analytics/tenants/grand-hotel/clv")
    
    if not result:
        print("❌ CLV analysis failed")
        return False
    
    # Check required fields
    required_fields = ["data", "total", "avg_clv", "total_clv"]
    missing = [f for f in required_fields if f not in result]
    if missing:
        print(f"❌ Missing CLV fields: {missing}")
        return False
    
    data = result.get("data", [])
    avg_clv = result.get("avg_clv", 0)
    total_clv = result.get("total_clv", 0)
    
    print(f"✅ Analyzed {len(data)} members")
    print(f"✅ Average CLV: {avg_clv}")
    print(f"✅ Total CLV: {total_clv}")
    
    # If we have data, check member structure
    if data:
        member = data[0]
        member_fields = ["contact_id", "name", "clv", "risk", "lifespan_months"]
        missing_member = [f for f in member_fields if f not in member]
        if missing_member:
            print(f"❌ Missing CLV member fields: {missing_member}")
            return False
        
        print(f"   Highest CLV: {member['name']} - {member['clv']} ({member['risk']} risk)")
    
    print("✅ CLV analysis working correctly")
    return True

def test_churn_analysis():
    """Test 13: GET /api/v2/loyalty-analytics/tenants/grand-hotel/churn"""
    print("\n⚠️ Testing Churn Analysis...")
    
    result = make_request("GET", "/v2/loyalty-analytics/tenants/grand-hotel/churn")
    
    if not result:
        print("❌ Churn analysis failed")
        return False
    
    # Check required fields
    required_fields = ["data", "total", "risk_distribution", "avg_churn_score"]
    missing = [f for f in required_fields if f not in result]
    if missing:
        print(f"❌ Missing churn fields: {missing}")
        return False
    
    data = result.get("data", [])
    risk_dist = result.get("risk_distribution", {})
    avg_churn = result.get("avg_churn_score", 0)
    
    print(f"✅ Analyzed {len(data)} members")
    print(f"✅ Risk distribution: {risk_dist}")
    print(f"✅ Average churn score: {avg_churn}")
    
    # If we have data, check member structure
    if data:
        member = data[0]
        member_fields = ["contact_id", "name", "churn_score", "risk_level", "recommended_action"]
        missing_member = [f for f in member_fields if f not in member]
        if missing_member:
            print(f"❌ Missing churn member fields: {missing_member}")
            return False
        
        print(f"   Highest risk: {member['name']} - {member['churn_score']} score ({member['risk_level']})")
    
    print("✅ Churn analysis working correctly")
    return True

def test_cohort_analysis():
    """Test 14: GET /api/v2/loyalty-analytics/tenants/grand-hotel/cohort"""
    print("\n📊 Testing Cohort Analysis...")
    
    result = make_request("GET", "/v2/loyalty-analytics/tenants/grand-hotel/cohort")
    
    if not result:
        print("❌ Cohort analysis failed")
        return False
    
    # Check required fields
    required_fields = ["data", "months"]
    missing = [f for f in required_fields if f not in result]
    if missing:
        print(f"❌ Missing cohort fields: {missing}")
        return False
    
    data = result.get("data", [])
    months = result.get("months", 0)
    
    print(f"✅ Analyzed {months} months of cohort data")
    print(f"✅ Found {len(data)} cohort entries")
    
    # If we have data, check cohort structure
    if data:
        cohort = data[0]
        cohort_fields = ["month", "new_members", "active_members", "returning_members", "retention_rate"]
        missing_cohort = [f for f in cohort_fields if f not in cohort]
        if missing_cohort:
            print(f"❌ Missing cohort fields: {missing_cohort}")
            return False
        
        print(f"   {cohort['month']}: {cohort['new_members']} new, {cohort['returning_members']} returning ({cohort['retention_rate']}% retention)")
    
    print("✅ Cohort analysis working correctly")
    return True

def test_roi_measurement():
    """Test 15: GET /api/v2/loyalty-analytics/tenants/grand-hotel/roi"""
    print("\n💎 Testing ROI Measurement...")
    
    result = make_request("GET", "/v2/loyalty-analytics/tenants/grand-hotel/roi")
    
    if not result:
        print("❌ ROI measurement failed")
        return False
    
    # Check required fields
    required_fields = ["total_members", "total_points_earned", "total_points_redeemed", 
                      "program_cost_try", "estimated_revenue_try", "roi_percentage", "redemption_rate"]
    missing = [f for f in required_fields if f not in result]
    if missing:
        print(f"❌ Missing ROI fields: {missing}")
        return False
    
    print(f"✅ Total members: {result['total_members']}")
    print(f"✅ Points earned: {result['total_points_earned']}")
    print(f"✅ Points redeemed: {result['total_points_redeemed']}")
    print(f"✅ Program cost: {result['program_cost_try']} TRY")
    print(f"✅ Estimated revenue: {result['estimated_revenue_try']} TRY")
    print(f"✅ ROI: {result['roi_percentage']}%")
    print(f"✅ Redemption rate: {result['redemption_rate']}%")
    
    print("✅ ROI measurement working correctly")
    return True

def test_ai_segmentation():
    """Test 16: GET /api/v2/loyalty-analytics/tenants/grand-hotel/segments"""
    print("\n🤖 Testing AI Segmentation...")
    
    result = make_request("GET", "/v2/loyalty-analytics/tenants/grand-hotel/segments")
    
    if not result:
        print("❌ AI segmentation failed")
        return False
    
    # Check required fields
    required_fields = ["segments", "member_segments", "personalized_offers", "total_members"]
    missing = [f for f in required_fields if f not in result]
    if missing:
        print(f"❌ Missing AI segmentation fields: {missing}")
        return False
    
    segments = result.get("segments", {})
    member_segments = result.get("member_segments", [])
    offers = result.get("personalized_offers", {})
    
    # Check for expected 5 segments
    expected_segments = {"Sampiyon", "Sadik", "Yukselen", "Risk Altinda", "Kayip"}
    found_segments = set(segments.keys())
    
    if not expected_segments.issubset(found_segments):
        print(f"❌ Missing segments. Expected: {expected_segments}, Found: {found_segments}")
        return False
    
    print(f"✅ Found {len(segments)} segments")
    for seg_name, seg_data in segments.items():
        print(f"   - {seg_name}: {seg_data['count']} members, {seg_data['total_points']} points")
    
    print(f"✅ Member segments: {len(member_segments)} members classified")
    print(f"✅ Personalized offers: {len(offers)} segment offers")
    
    print("✅ AI segmentation working correctly")
    return True

def test_loyalty_dashboard():
    """Test 17: GET /api/v2/loyalty-analytics/tenants/grand-hotel/dashboard"""
    print("\n📋 Testing Loyalty Dashboard...")
    
    result = make_request("GET", "/v2/loyalty-analytics/tenants/grand-hotel/dashboard")
    
    if not result:
        print("❌ Loyalty dashboard failed")
        return False
    
    # Check required fields
    required_fields = ["period", "kpis", "daily_activity"]
    missing = [f for f in required_fields if f not in result]
    if missing:
        print(f"❌ Missing dashboard fields: {missing}")
        return False
    
    kpis = result.get("kpis", {})
    daily_activity = result.get("daily_activity", [])
    
    # Check KPI structure
    kpi_fields = ["total_members", "active_members", "activity_rate", "points_earned", 
                 "points_spent", "new_enrollments", "redemptions"]
    missing_kpis = [f for f in kpi_fields if f not in kpis]
    if missing_kpis:
        print(f"❌ Missing KPI fields: {missing_kpis}")
        return False
    
    print(f"✅ Period: {result['period']}")
    print(f"✅ Total members: {kpis['total_members']}")
    print(f"✅ Active members: {kpis['active_members']}")
    print(f"✅ Activity rate: {kpis['activity_rate']}%")
    print(f"✅ Points earned: {kpis['points_earned']}")
    print(f"✅ Points spent: {kpis['points_spent']}")
    print(f"✅ Daily activity entries: {len(daily_activity)}")
    
    print("✅ Loyalty dashboard working correctly")
    return True

def test_digital_card():
    """Test 18: GET /api/v2/loyalty-engine/tenants/grand-hotel/members/{contact_id}/digital-card"""
    print("\n💳 Testing Digital Card with QR Code...")
    
    # First, get loyalty members from overview to find a contact_id
    overview = make_request("GET", "/v2/loyalty-engine/tenants/grand-hotel/overview")
    if not overview:
        print("❌ Could not get overview to find contact_id")
        return False
    
    # Try to find a contact_id from existing loyalty accounts
    # If we don't have any, we'll create one
    contact_id = None
    
    # Try to get member from loyalty accounts collection
    # For testing, let's use a known contact ID or create one
    test_contact_id = "test-digital-card-user"
    
    # First try to create/ensure loyalty account exists
    loyalty_create = make_request("POST", "/v2/loyalty/tenants/grand-hotel/enroll", {
        "contact_id": test_contact_id
    })
    
    if loyalty_create:
        contact_id = test_contact_id
        print(f"✅ Using contact_id: {contact_id}")
    else:
        print("❌ Could not create test loyalty account")
        return False
    
    # Now test the digital card endpoint
    result = make_request("GET", f"/v2/loyalty-engine/tenants/grand-hotel/members/{contact_id}/digital-card")
    
    if not result:
        print("❌ Digital card API failed")
        return False
    
    # Check required fields
    required_fields = ["member_id", "contact_id", "member_name", "points_balance", 
                      "tier_name", "tier_slug", "tier_color", "qr_code_base64", "next_tier"]
    missing = [f for f in required_fields if f not in result]
    if missing:
        print(f"❌ Missing digital card fields: {missing}")
        return False
    
    # Verify QR code is not empty
    qr_code = result.get("qr_code_base64", "")
    if not qr_code or len(qr_code) < 100:  # QR codes are typically much longer
        print(f"❌ QR code appears to be empty or invalid (length: {len(qr_code)})")
        return False
    
    print(f"✅ Member: {result['member_name']}")
    print(f"✅ Points: {result['points_balance']}")
    print(f"✅ Tier: {result['tier_name']} ({result['tier_slug']})")
    print(f"✅ QR Code: {len(qr_code)} characters (valid)")
    
    next_tier = result.get("next_tier", {})
    if next_tier.get("next_tier"):
        print(f"✅ Next tier: {next_tier['next_tier']} ({next_tier['points_needed']} points needed)")
    else:
        print("✅ Already at highest tier")
    
    print("✅ Digital card with QR code working correctly")
    return True

def run_tests():
    """Run all Loyalty Engine V3 and Analytics V3 tests in order"""
    print("🚀 Starting Loyalty Engine V3 & Analytics V3 Testing")
    print(f"Base URL: {BASE_URL}")
    print("Testing endpoints IN ORDER as specified:")
    print("=" * 70)
    
    # Authenticate first (Test 1)
    if not authenticate():
        print("❌ Cannot proceed without authentication")
        return False
    
    # Define test functions in order
    tests = [
        ("Loyalty Overview Dashboard", test_loyalty_overview),
        ("Point Rules API", test_point_rules),
        ("Tier Configuration", test_tiers),
        ("Tier Evaluation", test_tier_evaluation),
        ("Enhanced Rewards Catalog", test_rewards_enhanced),
        ("Campaigns API", test_campaigns),
        ("Referral Stats", test_referral_stats),
        ("Referral List", test_referral_list),
        ("Communication Preferences", test_communication_prefs),
        ("RFM Analysis", test_rfm_analysis),
        ("CLV Analysis", test_clv_analysis),
        ("Churn Analysis", test_churn_analysis),
        ("Cohort Analysis", test_cohort_analysis),
        ("ROI Measurement", test_roi_measurement),
        ("AI Segmentation", test_ai_segmentation),
        ("Loyalty Dashboard", test_loyalty_dashboard),
        ("Digital Card with QR", test_digital_card),
    ]
    
    success_count = 0
    total_tests = len(tests)
    
    # Run tests in order
    for i, (test_name, test_func) in enumerate(tests, 2):  # Start from 2 since login is test 1
        print(f"\n{'='*10} Test {i}: {test_name} {'='*10}")
        if test_func():
            success_count += 1
        else:
            print(f"❌ Test {i} failed: {test_name}")
    
    print("\n" + "=" * 70)
    print(f"🏁 Testing Complete: {success_count}/{total_tests} tests passed")
    
    if success_count == total_tests:
        print("🎉 ALL LOYALTY ENGINE V3 & ANALYTICS V3 TESTS PASSED!")
        print("✅ Both routers are fully operational and production-ready")
        return True
    else:
        failed_count = total_tests - success_count
        print(f"❌ {failed_count} tests failed")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)