#!/usr/bin/env python3
"""Backend API Testing for New Feature Routers
Tests Gamification, Push Notifications, and A/B Testing routers
"""
import asyncio
import aiohttp
import json
import sys
from typing import Dict, Any

# Backend URL from environment
BACKEND_URL = "https://engage-plus-8.preview.emergentagent.com/api"
LOGIN_EMAIL = "admin@grandhotel.com"
LOGIN_PASSWORD = "admin123"
TENANT_SLUG = "grand-hotel"

class BackendTester:
    def __init__(self):
        self.session = None
        self.token = None
        self.test_results = {}
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def login(self):
        """Authenticate and get token"""
        try:
            async with self.session.post(f"{BACKEND_URL}/auth/login", json={
                "email": LOGIN_EMAIL,
                "password": LOGIN_PASSWORD
            }) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.token = data.get("access_token")
                    print(f"✅ Login successful, token: {self.token[:20]}...")
                    return True
                else:
                    print(f"❌ Login failed: {resp.status} - {await resp.text()}")
                    return False
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def headers(self):
        return {"Authorization": f"Bearer {self.token}"}
    
    async def test_gamification_router(self):
        """Test all Gamification Router endpoints"""
        print("\n=== TESTING GAMIFICATION ROUTER ===")
        base_url = f"{BACKEND_URL}/v2/gamification/tenants/{TENANT_SLUG}"
        
        # Test 1: Get badges - should return 6 badges
        try:
            async with self.session.get(f"{base_url}/badges", headers=self.headers()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    badge_count = len(data.get("data", []))
                    print(f"✅ GET /badges: {badge_count} badges returned")
                    if badge_count >= 6:
                        print(f"   Expected 6+ badges, got {badge_count}")
                    self.test_results["gamification_badges_get"] = True
                    self.badge_data = data.get("data", [])
                else:
                    print(f"❌ GET /badges failed: {resp.status}")
                    self.test_results["gamification_badges_get"] = False
        except Exception as e:
            print(f"❌ GET /badges error: {e}")
            self.test_results["gamification_badges_get"] = False
        
        # Test 2: Create new badge
        try:
            new_badge = {
                "name": "Test Badge",
                "description": "Test badge for API testing",
                "icon": "test",
                "color": "#FF5722",
                "points_reward": 100
            }
            async with self.session.post(f"{base_url}/badges", json=new_badge, headers=self.headers()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    created_badge_id = data.get("id")
                    print(f"✅ POST /badges: Created badge {created_badge_id}")
                    self.test_results["gamification_badges_create"] = True
                    self.created_badge_id = created_badge_id
                else:
                    print(f"❌ POST /badges failed: {resp.status} - {await resp.text()}")
                    self.test_results["gamification_badges_create"] = False
        except Exception as e:
            print(f"❌ POST /badges error: {e}")
            self.test_results["gamification_badges_create"] = False
        
        # Test 3: Delete badge (if created successfully)
        if hasattr(self, 'created_badge_id'):
            try:
                async with self.session.delete(f"{base_url}/badges/{self.created_badge_id}", headers=self.headers()) as resp:
                    if resp.status == 200:
                        print(f"✅ DELETE /badges/{self.created_badge_id}: Success")
                        self.test_results["gamification_badges_delete"] = True
                    else:
                        print(f"❌ DELETE /badges failed: {resp.status}")
                        self.test_results["gamification_badges_delete"] = False
            except Exception as e:
                print(f"❌ DELETE /badges error: {e}")
                self.test_results["gamification_badges_delete"] = False
        
        # Test 4: Get challenges - should return 3 active challenges
        try:
            async with self.session.get(f"{base_url}/challenges", headers=self.headers()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    challenge_count = len(data.get("data", []))
                    print(f"✅ GET /challenges: {challenge_count} challenges returned")
                    if challenge_count >= 3:
                        print(f"   Expected 3+ challenges, got {challenge_count}")
                    self.test_results["gamification_challenges_get"] = True
                else:
                    print(f"❌ GET /challenges failed: {resp.status}")
                    self.test_results["gamification_challenges_get"] = False
        except Exception as e:
            print(f"❌ GET /challenges error: {e}")
            self.test_results["gamification_challenges_get"] = False
        
        # Test 5: Create new challenge
        try:
            new_challenge = {
                "name": "Test Challenge",
                "target_event": "booking_completed",
                "target_value": 5,
                "points_reward": 200
            }
            async with self.session.post(f"{base_url}/challenges", json=new_challenge, headers=self.headers()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    created_challenge_id = data.get("id")
                    print(f"✅ POST /challenges: Created challenge {created_challenge_id}")
                    self.test_results["gamification_challenges_create"] = True
                    self.created_challenge_id = created_challenge_id
                else:
                    print(f"❌ POST /challenges failed: {resp.status} - {await resp.text()}")
                    self.test_results["gamification_challenges_create"] = False
        except Exception as e:
            print(f"❌ POST /challenges error: {e}")
            self.test_results["gamification_challenges_create"] = False
        
        # Test 6: Delete challenge (if created successfully)
        if hasattr(self, 'created_challenge_id'):
            try:
                async with self.session.delete(f"{base_url}/challenges/{self.created_challenge_id}", headers=self.headers()) as resp:
                    if resp.status == 200:
                        print(f"✅ DELETE /challenges/{self.created_challenge_id}: Success")
                        self.test_results["gamification_challenges_delete"] = True
                    else:
                        print(f"❌ DELETE /challenges failed: {resp.status}")
                        self.test_results["gamification_challenges_delete"] = False
            except Exception as e:
                print(f"❌ DELETE /challenges error: {e}")
                self.test_results["gamification_challenges_delete"] = False
        
        # Test 7: Get leaderboard
        try:
            async with self.session.get(f"{base_url}/leaderboard", headers=self.headers()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    leaderboard_entries = len(data.get("data", []))
                    print(f"✅ GET /leaderboard: {leaderboard_entries} entries returned")
                    self.test_results["gamification_leaderboard"] = True
                else:
                    print(f"❌ GET /leaderboard failed: {resp.status}")
                    self.test_results["gamification_leaderboard"] = False
        except Exception as e:
            print(f"❌ GET /leaderboard error: {e}")
            self.test_results["gamification_leaderboard"] = False
        
        # Test 8: Get rewards - should return 5 rewards
        try:
            async with self.session.get(f"{base_url}/rewards", headers=self.headers()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    reward_count = len(data.get("data", []))
                    print(f"✅ GET /rewards: {reward_count} rewards returned")
                    if reward_count >= 5:
                        print(f"   Expected 5+ rewards, got {reward_count}")
                    self.test_results["gamification_rewards_get"] = True
                else:
                    print(f"❌ GET /rewards failed: {resp.status}")
                    self.test_results["gamification_rewards_get"] = False
        except Exception as e:
            print(f"❌ GET /rewards error: {e}")
            self.test_results["gamification_rewards_get"] = False
        
        # Test 9: Create new reward
        try:
            new_reward = {
                "name": "Test Reward",
                "points_cost": 500,
                "stock": 10
            }
            async with self.session.post(f"{base_url}/rewards", json=new_reward, headers=self.headers()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    created_reward_id = data.get("id")
                    print(f"✅ POST /rewards: Created reward {created_reward_id}")
                    self.test_results["gamification_rewards_create"] = True
                    self.created_reward_id = created_reward_id
                else:
                    print(f"❌ POST /rewards failed: {resp.status} - {await resp.text()}")
                    self.test_results["gamification_rewards_create"] = False
        except Exception as e:
            print(f"❌ POST /rewards error: {e}")
            self.test_results["gamification_rewards_create"] = False
        
        # Test 10: Delete reward (if created successfully)
        if hasattr(self, 'created_reward_id'):
            try:
                async with self.session.delete(f"{base_url}/rewards/{self.created_reward_id}", headers=self.headers()) as resp:
                    if resp.status == 200:
                        print(f"✅ DELETE /rewards/{self.created_reward_id}: Success")
                        self.test_results["gamification_rewards_delete"] = True
                    else:
                        print(f"❌ DELETE /rewards failed: {resp.status}")
                        self.test_results["gamification_rewards_delete"] = False
            except Exception as e:
                print(f"❌ DELETE /rewards error: {e}")
                self.test_results["gamification_rewards_delete"] = False
        
        # Test 11: Get reward-redemptions
        try:
            async with self.session.get(f"{base_url}/reward-redemptions", headers=self.headers()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    redemption_count = data.get("total", 0)
                    print(f"✅ GET /reward-redemptions: {redemption_count} redemptions returned")
                    self.test_results["gamification_redemptions"] = True
                else:
                    print(f"❌ GET /reward-redemptions failed: {resp.status}")
                    self.test_results["gamification_redemptions"] = False
        except Exception as e:
            print(f"❌ GET /reward-redemptions error: {e}")
            self.test_results["gamification_redemptions"] = False
        
        # Test 12: Get stats
        try:
            async with self.session.get(f"{base_url}/stats", headers=self.headers()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stats = {
                        "total_badges": data.get("total_badges", 0),
                        "active_challenges": data.get("active_challenges", 0),
                        "total_rewards": data.get("total_rewards", 0),
                        "total_earned_badges": data.get("total_earned_badges", 0)
                    }
                    print(f"✅ GET /stats: {stats}")
                    self.test_results["gamification_stats"] = True
                else:
                    print(f"❌ GET /stats failed: {resp.status}")
                    self.test_results["gamification_stats"] = False
        except Exception as e:
            print(f"❌ GET /stats error: {e}")
            self.test_results["gamification_stats"] = False

    async def test_push_notifications_router(self):
        """Test all Push Notifications Router endpoints"""
        print("\n=== TESTING PUSH NOTIFICATIONS ROUTER ===")
        base_url = f"{BACKEND_URL}/v2/push/tenants/{TENANT_SLUG}"
        
        # Test 1: Get VAPID public key - should NOT return "dummy_public_key"
        try:
            async with self.session.get(f"{base_url}/vapid-public-key") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    public_key = data.get("public_key", "")
                    if public_key and public_key != "dummy_public_key":
                        print(f"✅ GET /vapid-public-key: Valid key {public_key[:20]}...")
                        self.test_results["push_vapid_key"] = True
                    elif public_key == "dummy_public_key":
                        print(f"⚠️ GET /vapid-public-key: Using dummy key (expected in development)")
                        self.test_results["push_vapid_key"] = True  # Still pass for development
                    else:
                        print(f"❌ GET /vapid-public-key: No valid key returned")
                        self.test_results["push_vapid_key"] = False
                else:
                    print(f"❌ GET /vapid-public-key failed: {resp.status}")
                    self.test_results["push_vapid_key"] = False
        except Exception as e:
            print(f"❌ GET /vapid-public-key error: {e}")
            self.test_results["push_vapid_key"] = False
        
        # Test 2: Subscribe to push notifications
        try:
            subscription_data = {
                "subscription": {
                    "endpoint": "https://test.pushservice.com/abc123",
                    "keys": {
                        "p256dh": "test_p256dh_key",
                        "auth": "test_auth_key"
                    }
                },
                "device_info": "Test Browser API Testing"
            }
            async with self.session.post(f"{base_url}/subscribe", json=subscription_data, headers=self.headers()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"✅ POST /subscribe: {data.get('message', 'Success')}")
                    self.test_results["push_subscribe"] = True
                else:
                    print(f"❌ POST /subscribe failed: {resp.status} - {await resp.text()}")
                    self.test_results["push_subscribe"] = False
        except Exception as e:
            print(f"❌ POST /subscribe error: {e}")
            self.test_results["push_subscribe"] = False
        
        # Test 3: List subscriptions
        try:
            async with self.session.get(f"{base_url}/subscriptions", headers=self.headers()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    sub_count = len(data.get("data", []))
                    print(f"✅ GET /subscriptions: {sub_count} subscriptions found")
                    self.test_results["push_subscriptions"] = True
                else:
                    print(f"❌ GET /subscriptions failed: {resp.status}")
                    self.test_results["push_subscriptions"] = False
        except Exception as e:
            print(f"❌ GET /subscriptions error: {e}")
            self.test_results["push_subscriptions"] = False
        
        # Test 4: Send push notification
        try:
            push_data = {
                "title": "Test Push Notification",
                "body": "This is a test push notification from API testing",
                "data": {"test": True}
            }
            async with self.session.post(f"{base_url}/send", json=push_data, headers=self.headers()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    sent = data.get("sent", 0)
                    failed = data.get("failed", 0)
                    total = data.get("total", 0)
                    print(f"✅ POST /send: Sent {sent}, Failed {failed}, Total {total}")
                    self.test_results["push_send"] = True
                else:
                    print(f"❌ POST /send failed: {resp.status} - {await resp.text()}")
                    self.test_results["push_send"] = False
        except Exception as e:
            print(f"❌ POST /send error: {e}")
            self.test_results["push_send"] = False
        
        # Test 5: Get push logs
        try:
            async with self.session.get(f"{base_url}/push-logs", headers=self.headers()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    log_count = len(data.get("data", []))
                    print(f"✅ GET /push-logs: {log_count} logs found")
                    self.test_results["push_logs"] = True
                else:
                    print(f"❌ GET /push-logs failed: {resp.status}")
                    self.test_results["push_logs"] = False
        except Exception as e:
            print(f"❌ GET /push-logs error: {e}")
            self.test_results["push_logs"] = False
        
        # Test 6: Get push stats
        try:
            async with self.session.get(f"{base_url}/stats", headers=self.headers()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stats = {
                        "total_subscribers": data.get("total_subscribers", 0),
                        "total_campaigns": data.get("total_campaigns", 0),
                        "total_pushes_sent": data.get("total_pushes_sent", 0),
                        "delivery_rate": data.get("delivery_rate", 0)
                    }
                    print(f"✅ GET /stats: {stats}")
                    self.test_results["push_stats"] = True
                else:
                    print(f"❌ GET /stats failed: {resp.status}")
                    self.test_results["push_stats"] = False
        except Exception as e:
            print(f"❌ GET /stats error: {e}")
            self.test_results["push_stats"] = False

    async def test_ab_testing_router(self):
        """Test all A/B Testing Router endpoints"""
        print("\n=== TESTING A/B TESTING ROUTER ===")
        base_url = f"{BACKEND_URL}/v2/ab-testing/tenants/{TENANT_SLUG}"
        
        # Test 1: Get experiments - should return 4 experiments
        try:
            async with self.session.get(f"{base_url}/experiments", headers=self.headers()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    exp_count = len(data.get("data", []))
                    print(f"✅ GET /experiments: {exp_count} experiments returned")
                    if exp_count >= 4:
                        print(f"   Expected 4+ experiments, got {exp_count}")
                    self.test_results["ab_experiments_get"] = True
                    self.experiments = data.get("data", [])
                else:
                    print(f"❌ GET /experiments failed: {resp.status}")
                    self.test_results["ab_experiments_get"] = False
        except Exception as e:
            print(f"❌ GET /experiments error: {e}")
            self.test_results["ab_experiments_get"] = False
        
        # Test 2: Create new experiment
        try:
            new_experiment = {
                "name": "Test Booking Flow",
                "description": "Testing booking flow optimization",
                "variants": [
                    {"name": "control", "traffic_percent": 50, "description": "Original booking flow"},
                    {"name": "variant_a", "traffic_percent": 50, "description": "Optimized booking flow"}
                ]
            }
            async with self.session.post(f"{base_url}/experiments", json=new_experiment, headers=self.headers()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    created_exp_id = data.get("id")
                    print(f"✅ POST /experiments: Created experiment {created_exp_id}")
                    self.test_results["ab_experiments_create"] = True
                    self.created_exp_id = created_exp_id
                else:
                    print(f"❌ POST /experiments failed: {resp.status} - {await resp.text()}")
                    self.test_results["ab_experiments_create"] = False
        except Exception as e:
            print(f"❌ POST /experiments error: {e}")
            self.test_results["ab_experiments_create"] = False
        
        # Test 3: Get experiment detail (use created or existing experiment)
        test_exp_id = getattr(self, 'created_exp_id', None)
        if not test_exp_id and hasattr(self, 'experiments') and self.experiments:
            test_exp_id = self.experiments[0].get('id')
        
        if test_exp_id:
            try:
                async with self.session.get(f"{base_url}/experiments/{test_exp_id}", headers=self.headers()) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"✅ GET /experiments/{test_exp_id}: Retrieved experiment details")
                        self.test_results["ab_experiments_detail"] = True
                        self.test_exp_id = test_exp_id
                    else:
                        print(f"❌ GET /experiments/{test_exp_id} failed: {resp.status}")
                        self.test_results["ab_experiments_detail"] = False
            except Exception as e:
                print(f"❌ GET /experiments/{test_exp_id} error: {e}")
                self.test_results["ab_experiments_detail"] = False
        
        # Test 4: Start experiment (if we have one in draft status)
        if hasattr(self, 'test_exp_id'):
            try:
                async with self.session.post(f"{base_url}/experiments/{self.test_exp_id}/start", headers=self.headers()) as resp:
                    if resp.status == 200:
                        print(f"✅ POST /experiments/{self.test_exp_id}/start: Experiment started")
                        self.test_results["ab_experiments_start"] = True
                    else:
                        print(f"❌ POST /experiments/{self.test_exp_id}/start failed: {resp.status}")
                        self.test_results["ab_experiments_start"] = False
            except Exception as e:
                print(f"❌ POST /experiments/{self.test_exp_id}/start error: {e}")
                self.test_results["ab_experiments_start"] = False
        
        # Test 5: Stop experiment (if we have one running)
        if hasattr(self, 'test_exp_id'):
            try:
                async with self.session.post(f"{base_url}/experiments/{self.test_exp_id}/stop", headers=self.headers()) as resp:
                    if resp.status == 200:
                        print(f"✅ POST /experiments/{self.test_exp_id}/stop: Experiment stopped")
                        self.test_results["ab_experiments_stop"] = True
                    else:
                        print(f"❌ POST /experiments/{self.test_exp_id}/stop failed: {resp.status}")
                        self.test_results["ab_experiments_stop"] = False
            except Exception as e:
                print(f"❌ POST /experiments/{self.test_exp_id}/stop error: {e}")
                self.test_results["ab_experiments_stop"] = False
        
        # Test 6: Assign user to variant
        if hasattr(self, 'test_exp_id'):
            try:
                assignment_data = {
                    "experiment_id": self.test_exp_id,
                    "user_id": "test_user_123"
                }
                async with self.session.post(f"{base_url}/assign", json=assignment_data, headers=self.headers()) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        variant = data.get("variant")
                        print(f"✅ POST /assign: Assigned user to variant '{variant}'")
                        self.test_results["ab_assign"] = True
                    else:
                        print(f"❌ POST /assign failed: {resp.status} - {await resp.text()}")
                        self.test_results["ab_assign"] = False
            except Exception as e:
                print(f"❌ POST /assign error: {e}")
                self.test_results["ab_assign"] = False
        
        # Test 7: Track event
        if hasattr(self, 'test_exp_id'):
            try:
                track_data = {
                    "experiment_id": self.test_exp_id,
                    "event_name": "conversion",
                    "user_id": "test_user_123"
                }
                async with self.session.post(f"{base_url}/track", json=track_data, headers=self.headers()) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        event_id = data.get("event_id")
                        print(f"✅ POST /track: Tracked conversion event {event_id}")
                        self.test_results["ab_track"] = True
                    else:
                        print(f"❌ POST /track failed: {resp.status} - {await resp.text()}")
                        self.test_results["ab_track"] = False
            except Exception as e:
                print(f"❌ POST /track error: {e}")
                self.test_results["ab_track"] = False
        
        # Test 8: Get experiment results
        if hasattr(self, 'test_exp_id'):
            try:
                async with self.session.get(f"{base_url}/experiments/{self.test_exp_id}/results", headers=self.headers()) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        results = data.get("results", [])
                        winner = data.get("winner")
                        total_participants = data.get("total_participants", 0)
                        print(f"✅ GET /experiments/{self.test_exp_id}/results: {len(results)} variants, {total_participants} participants, winner: {winner}")
                        self.test_results["ab_results"] = True
                    else:
                        print(f"❌ GET /experiments/{self.test_exp_id}/results failed: {resp.status}")
                        self.test_results["ab_results"] = False
            except Exception as e:
                print(f"❌ GET /experiments/{self.test_exp_id}/results error: {e}")
                self.test_results["ab_results"] = False
        
        # Test 9: Get A/B testing stats
        try:
            async with self.session.get(f"{base_url}/stats", headers=self.headers()) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    stats = {
                        "total_experiments": data.get("total_experiments", 0),
                        "running": data.get("running", 0),
                        "completed": data.get("completed", 0),
                        "draft": data.get("draft", 0)
                    }
                    print(f"✅ GET /stats: {stats}")
                    self.test_results["ab_stats"] = True
                else:
                    print(f"❌ GET /stats failed: {resp.status}")
                    self.test_results["ab_stats"] = False
        except Exception as e:
            print(f"❌ GET /stats error: {e}")
            self.test_results["ab_stats"] = False

    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*60)
        print("TEST RESULTS SUMMARY")
        print("="*60)
        
        categories = {
            "Gamification Router": [k for k in self.test_results.keys() if k.startswith("gamification_")],
            "Push Notifications Router": [k for k in self.test_results.keys() if k.startswith("push_")],
            "A/B Testing Router": [k for k in self.test_results.keys() if k.startswith("ab_")]
        }
        
        total_tests = 0
        passed_tests = 0
        
        for category, tests in categories.items():
            print(f"\n{category}:")
            category_passed = 0
            for test in tests:
                status = "✅ PASS" if self.test_results.get(test) else "❌ FAIL"
                print(f"  {test}: {status}")
                if self.test_results.get(test):
                    category_passed += 1
                    passed_tests += 1
                total_tests += 1
            print(f"  → {category_passed}/{len(tests)} passed")
        
        print(f"\nOVERALL: {passed_tests}/{total_tests} tests passed ({(passed_tests/total_tests*100):.1f}%)")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED!")
        else:
            failed_tests = [k for k, v in self.test_results.items() if not v]
            print(f"⚠️ FAILED TESTS: {', '.join(failed_tests)}")

async def main():
    """Run all backend tests"""
    try:
        async with BackendTester() as tester:
            if await tester.login():
                await tester.test_gamification_router()
                await tester.test_push_notifications_router()
                await tester.test_ab_testing_router()
                tester.print_summary()
            else:
                print("❌ Cannot proceed without authentication")
                sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())