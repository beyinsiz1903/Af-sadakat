#!/usr/bin/env python3
"""
Focused test for Sprint 3 V2 APIs
"""
import requests
import json

def test_v2_apis():
    base_url = "https://points-platform-2.preview.emergentagent.com/api"
    
    # Get fresh token
    print("🔐 Getting authentication token...")
    login_response = requests.post(f"{base_url}/auth/login", 
                                   json={"email": "admin@grandhotel.com", "password": "admin123"})
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return False
    
    token = login_response.json()['token']
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    print(f"✅ Token acquired: {token[:20]}...")
    
    tests_passed = 0
    tests_total = 0
    
    # Test V2 Inbox APIs
    print("\n📥 Testing V2 Inbox APIs...")
    
    tests_total += 1
    conv_response = requests.get(f"{base_url}/v2/inbox/tenants/grand-hotel/conversations", headers=headers)
    if conv_response.status_code == 200:
        tests_passed += 1
        conv_data = conv_response.json()
        convs = conv_data.get('data', [])
        print(f"✅ Conversations: {len(convs)} found, total: {conv_data.get('total', 0)}")
        
        # Test conversation detail if we have conversations
        if convs:
            conv_id = convs[0]['id']
            tests_total += 1
            detail_response = requests.get(f"{base_url}/v2/inbox/tenants/grand-hotel/conversations/{conv_id}", headers=headers)
            if detail_response.status_code == 200:
                tests_passed += 1
                print(f"✅ Conversation detail for {conv_id}")
                
                # Test AI suggest
                tests_total += 1
                ai_response = requests.post(f"{base_url}/v2/inbox/tenants/grand-hotel/conversations/{conv_id}/ai-suggest", headers=headers)
                if ai_response.status_code == 200:
                    tests_passed += 1
                    ai_data = ai_response.json()
                    print(f"✅ AI suggestion: {ai_data.get('suggestion', '')[:50]}...")
                else:
                    print(f"❌ AI suggest failed: {ai_response.status_code} - {ai_response.text}")
            else:
                print(f"❌ Conversation detail failed: {detail_response.status_code}")
    else:
        print(f"❌ Conversations failed: {conv_response.status_code} - {conv_response.text}")
    
    # Test connector pull
    tests_total += 1
    pull_response = requests.post(f"{base_url}/v2/inbox/tenants/grand-hotel/connectors/pull-now", headers=headers)
    if pull_response.status_code == 200:
        tests_passed += 1
        pull_data = pull_response.json()
        print(f"✅ Connector pull: {pull_data.get('messages_created', 0)} messages, {pull_data.get('reviews_created', 0)} reviews")
    else:
        print(f"❌ Connector pull failed: {pull_response.status_code} - {pull_response.text}")
    
    # Test V2 Reviews APIs
    print("\n⭐ Testing V2 Reviews APIs...")
    
    tests_total += 1
    reviews_response = requests.get(f"{base_url}/v2/reviews/tenants/grand-hotel", headers=headers)
    if reviews_response.status_code == 200:
        tests_passed += 1
        reviews_data = reviews_response.json()
        reviews = reviews_data.get('data', [])
        summary = reviews_data.get('summary', {})
        print(f"✅ Reviews: {len(reviews)} found, sentiment: {summary.get('positive', 0)} POS, {summary.get('neutral', 0)} NEU, {summary.get('negative', 0)} NEG")
        
        # Test review AI suggest if we have reviews
        if reviews:
            review_id = reviews[0]['id']
            tests_total += 1
            review_ai_response = requests.post(f"{base_url}/v2/reviews/tenants/grand-hotel/{review_id}/ai-suggest", headers=headers)
            if review_ai_response.status_code == 200:
                tests_passed += 1
                review_ai_data = review_ai_response.json()
                print(f"✅ Review AI suggestion: {review_ai_data.get('suggestion', '')[:50]}...")
            else:
                print(f"❌ Review AI suggest failed: {review_ai_response.status_code} - {review_ai_response.text}")
    else:
        print(f"❌ Reviews failed: {reviews_response.status_code} - {reviews_response.text}")
    
    # Test WebChat APIs
    print("\n💬 Testing WebChat APIs...")
    
    tests_total += 1
    widget_response = requests.get(f"{base_url}/v2/inbox/webchat/widget.js?tenantSlug=grand-hotel", 
                                   headers={'Accept': 'application/javascript'})
    if widget_response.status_code == 200:
        tests_passed += 1
        print(f"✅ Widget JS generated ({len(widget_response.text)} chars)")
    else:
        print(f"❌ Widget JS failed: {widget_response.status_code}")
    
    tests_total += 1
    webchat_start = requests.post(f"{base_url}/v2/inbox/webchat/start", 
                                  json={"tenantSlug": "grand-hotel", "visitorName": "Test User"})
    if webchat_start.status_code == 200:
        tests_passed += 1
        webchat_data = webchat_start.json()
        conv_id = webchat_data.get('conversationId')
        print(f"✅ WebChat started: {conv_id}")
        
        # Send test message
        tests_total += 1
        msg_response = requests.post(f"{base_url}/v2/inbox/webchat/{conv_id}/messages", 
                                     json={"text": "Hello from V2 test", "senderName": "Test User"})
        if msg_response.status_code == 200:
            tests_passed += 1
            print(f"✅ WebChat message sent")
        else:
            print(f"❌ WebChat message failed: {msg_response.status_code}")
    else:
        print(f"❌ WebChat start failed: {webchat_start.status_code}")
    
    print(f"\n📊 V2 API Test Results: {tests_passed}/{tests_total} passed ({(tests_passed/tests_total*100):.1f}%)")
    return tests_passed == tests_total

if __name__ == "__main__":
    success = test_v2_apis()
    exit(0 if success else 1)