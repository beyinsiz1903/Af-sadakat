#!/usr/bin/env python3
"""
Backend Test Suite for Sprint 8: Meta Integration
Testing Meta Integration Admin Router, Webhooks Router, and Provider Service
"""
import asyncio
import json
import requests
import hmac
import hashlib
from datetime import datetime

# Configuration
BACKEND_URL = "https://booking-automation-2.preview.emergentagent.com/api"
TENANT = "grand-hotel"
LOGIN_EMAIL = "admin@grandhotel.com"
LOGIN_PASSWORD = "admin123"

# Test data
TEST_APP_ID = "123456789"
TEST_APP_SECRET = "test_secret_key"  # From review request
CONFIGURE_APP_ID = "test_app_123"
CONFIGURE_APP_SECRET = "my_secret"
CONFIGURE_VERIFY_TOKEN = "test_verify_token_123"

def get_headers(token=None):
    """Get request headers with optional auth token."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers

def login():
    """Login and get auth token."""
    print("🔐 Logging in...")
    
    response = requests.post(
        f"{BACKEND_URL}/auth/login",
        json={
            "email": LOGIN_EMAIL,
            "password": LOGIN_PASSWORD
        },
        headers=get_headers(),
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        if token:
            print(f"✅ Login successful, token: {token[:20]}...")
            return token
        else:
            print(f"❌ Login failed: No token in response - {data}")
            return None
    else:
        print(f"❌ Login failed: {response.status_code} - {response.text}")
        return None

def generate_hmac_signature(payload_body, secret_key):
    """Generate HMAC SHA256 signature for webhook verification."""
    signature = hmac.new(
        secret_key.encode('utf-8'),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"

def test_meta_status_initial(token):
    """Test 1: Initial Meta Status - should show DISCONNECTED with app_id 123456789"""
    print("\n🧪 Test 1: Meta Status (Initial)")
    
    response = requests.get(
        f"{BACKEND_URL}/v2/integrations/meta/tenants/{TENANT}/status",
        headers=get_headers(token),
        timeout=30
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        status = data.get("status")
        app_id = data.get("meta_app_id")
        webhook_url = data.get("webhook_url")
        
        print(f"Status: {status}")
        print(f"App ID: {app_id}")
        print(f"Webhook URL: {webhook_url}")
        
        # Should either be NOT_CONFIGURED or DISCONNECTED
        if status in ["NOT_CONFIGURED", "DISCONNECTED"]:
            print("✅ Meta status endpoint working")
            return True
        else:
            print(f"❌ Unexpected status: {status}")
            return False
    else:
        print(f"❌ Meta status test failed: {response.status_code}")
        return False

def test_configure_meta(token):
    """Test 2: Configure Meta - POST credentials"""
    print("\n🧪 Test 2: Configure Meta")
    
    payload = {
        "meta_app_id": CONFIGURE_APP_ID,
        "meta_app_secret": CONFIGURE_APP_SECRET,
        "meta_verify_token": CONFIGURE_VERIFY_TOKEN
    }
    
    response = requests.post(
        f"{BACKEND_URL}/v2/integrations/meta/tenants/{TENANT}/configure",
        json=payload,
        headers=get_headers(token),
        timeout=30
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get("ok") and data.get("webhook_url"):
            print("✅ Meta configuration successful")
            return True
        else:
            print(f"❌ Configure response missing expected fields")
            return False
    else:
        print(f"❌ Configure Meta test failed: {response.status_code}")
        return False

def test_webhook_verify_success():
    """Test 3: Webhook Verification - Success case"""
    print("\n🧪 Test 3: Webhook Verify Success")
    
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": CONFIGURE_VERIFY_TOKEN,
        "hub.challenge": "test_challenge_abc"
    }
    
    response = requests.get(
        f"{BACKEND_URL}/v2/webhooks/meta/{TENANT}",
        params=params,
        timeout=30
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200 and response.text == "test_challenge_abc":
        print("✅ Webhook verification success working")
        return True
    else:
        print(f"❌ Webhook verify success failed")
        return False

def test_webhook_verify_fail():
    """Test 4: Webhook Verification - Fail case"""
    print("\n🧪 Test 4: Webhook Verify Fail")
    
    params = {
        "hub.mode": "subscribe",
        "hub.verify_token": "wrong_token",
        "hub.challenge": "test"
    }
    
    response = requests.get(
        f"{BACKEND_URL}/v2/webhooks/meta/{TENANT}",
        params=params,
        timeout=30
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 403:
        print("✅ Webhook verification fail working")
        return True
    else:
        print(f"❌ Webhook verify fail should return 403, got {response.status_code}")
        return False

def test_webhook_whatsapp_message():
    """Test 5: Webhook WhatsApp Message with proper HMAC signature"""
    print("\n🧪 Test 5: Webhook WhatsApp Message")
    
    # Create WhatsApp Cloud API message event
    webhook_payload = {
        "object": "whatsapp_business_account",
        "entry": [{
            "id": "123456789",
            "changes": [{
                "field": "messages",
                "value": {
                    "messaging_product": "whatsapp",
                    "metadata": {
                        "display_phone_number": "+1234567890",
                        "phone_number_id": "1234567890"
                    },
                    "contacts": [{
                        "profile": {"name": "John Doe"},
                        "wa_id": "+1234567890"
                    }],
                    "messages": [{
                        "from": "+1234567890",
                        "id": "wamid.test123",
                        "timestamp": "1644955284",
                        "text": {"body": "Hello, I need help with booking"},
                        "type": "text"
                    }]
                }
            }]
        }]
    }
    
    payload_json = json.dumps(webhook_payload)
    payload_bytes = payload_json.encode('utf-8')
    
    # Generate HMAC signature using configured app secret
    signature = generate_hmac_signature(payload_bytes, CONFIGURE_APP_SECRET)
    
    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": signature
    }
    
    response = requests.post(
        f"{BACKEND_URL}/v2/webhooks/meta/{TENANT}",
        data=payload_bytes,
        headers=headers,
        timeout=30
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    print(f"Signature used: {signature}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "ok":
            print("✅ WhatsApp webhook message processing working")
            return True
        else:
            print(f"❌ Unexpected webhook response: {data}")
            return False
    else:
        print(f"❌ WhatsApp webhook test failed: {response.status_code}")
        return False

def test_webhook_invalid_signature():
    """Test 6: Webhook with invalid signature - should return 403"""
    print("\n🧪 Test 6: Webhook Invalid Signature")
    
    webhook_payload = {
        "object": "whatsapp_business_account",
        "entry": [{"id": "123456789", "changes": []}]
    }
    
    payload_json = json.dumps(webhook_payload)
    payload_bytes = payload_json.encode('utf-8')
    
    # Use wrong signature
    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": "sha256=wrong_signature_here"
    }
    
    response = requests.post(
        f"{BACKEND_URL}/v2/webhooks/meta/{TENANT}",
        data=payload_bytes,
        headers=headers,
        timeout=30
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 403:
        print("✅ Invalid signature properly rejected")
        return True
    else:
        print(f"❌ Invalid signature should return 403, got {response.status_code}")
        return False

def test_webhook_facebook_comment():
    """Test 7: Webhook Facebook Comment - should create review"""
    print("\n🧪 Test 7: Webhook Facebook Comment")
    
    # Create Facebook feed comment event
    webhook_payload = {
        "object": "page",
        "entry": [{
            "id": "page_123456789",
            "time": 1644955284,
            "changes": [{
                "field": "feed",
                "value": {
                    "item": "comment",
                    "verb": "add",
                    "comment_id": "comment_123456",
                    "post_id": "post_123456",
                    "message": "Great hotel! Loved our stay here.",
                    "from": {
                        "name": "Jane Smith",
                        "id": "user_123456"
                    },
                    "created_time": "2022-02-15T19:21:24+0000",
                    "permalink_url": "https://facebook.com/comment/123456"
                }
            }]
        }]
    }
    
    payload_json = json.dumps(webhook_payload)
    payload_bytes = payload_json.encode('utf-8')
    
    # Generate proper HMAC signature
    signature = generate_hmac_signature(payload_bytes, CONFIGURE_APP_SECRET)
    
    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": signature
    }
    
    response = requests.post(
        f"{BACKEND_URL}/v2/webhooks/meta/{TENANT}",
        data=payload_bytes,
        headers=headers,
        timeout=30
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get("status") == "ok":
            print("✅ Facebook comment webhook processing working")
            return True
        else:
            print(f"❌ Unexpected webhook response: {data}")
            return False
    else:
        print(f"❌ Facebook comment webhook test failed: {response.status_code}")
        return False

def test_meta_status_after_events(token):
    """Test 8: Meta Status After Events - should still be working"""
    print("\n🧪 Test 8: Meta Status After Events")
    
    response = requests.get(
        f"{BACKEND_URL}/v2/integrations/meta/tenants/{TENANT}/status",
        headers=get_headers(token),
        timeout=30
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        status = data.get("status")
        app_id = data.get("meta_app_id")
        
        print(f"Status: {status}")
        print(f"App ID: {app_id}")
        
        if status == "DISCONNECTED" and app_id == CONFIGURE_APP_ID:
            print("✅ Meta status after events working correctly")
            return True
        else:
            print(f"❌ Unexpected status after events: {status}, app_id: {app_id}")
            return False
    else:
        print(f"❌ Meta status after events test failed: {response.status_code}")
        return False

def test_disconnect_meta(token):
    """Test 9: Disconnect Meta Integration"""
    print("\n🧪 Test 9: Disconnect Meta")
    
    response = requests.post(
        f"{BACKEND_URL}/v2/integrations/meta/tenants/{TENANT}/disconnect",
        json={},
        headers=get_headers(token),
        timeout=30
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        if data.get("ok"):
            print("✅ Meta disconnect working")
            return True
        else:
            print(f"❌ Disconnect response missing 'ok' field")
            return False
    else:
        print(f"❌ Meta disconnect test failed: {response.status_code}")
        return False

def run_all_tests():
    """Run all Meta Integration tests in sequence."""
    print("🚀 Starting Sprint 8 Meta Integration Backend Tests")
    print("=" * 60)
    
    # Login first
    token = login()
    if not token:
        print("❌ Cannot proceed without authentication")
        return
    
    test_results = []
    
    # Run all tests in sequence
    tests = [
        ("Meta Status (Initial)", lambda: test_meta_status_initial(token)),
        ("Configure Meta", lambda: test_configure_meta(token)),
        ("Webhook Verify Success", test_webhook_verify_success),
        ("Webhook Verify Fail", test_webhook_verify_fail),
        ("Webhook WhatsApp Message", test_webhook_whatsapp_message),
        ("Webhook Invalid Signature", test_webhook_invalid_signature),
        ("Webhook Facebook Comment", test_webhook_facebook_comment),
        ("Meta Status After Events", lambda: test_meta_status_after_events(token)),
        ("Disconnect Meta", lambda: test_disconnect_meta(token))
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {str(e)}")
            test_results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 SPRINT 8 META INTEGRATION TEST RESULTS")
    print("=" * 60)
    
    passed = 0
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print(f"\nSUMMARY: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL META INTEGRATION TESTS PASSED!")
    else:
        print("⚠️  Some tests failed. Check logs above for details.")

if __name__ == "__main__":
    run_all_tests()