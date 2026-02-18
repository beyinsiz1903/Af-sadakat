#!/usr/bin/env python3
"""
Sprint 5 V2 Endpoints Comprehensive Test Suite
Tests Properties V2, Offers V2, Payments V2, Reservations V2, and Inbox create-offer endpoints
"""
import requests
import json
import time
from datetime import datetime, date, timedelta

class Sprint5V2Tester:
    def __init__(self):
        self.base_url = "https://hospitality-ops-4.preview.emergentagent.com/api"
        self.token = None
        self.tenant_slug = "grand-hotel"
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.test_data = {}  # Store created objects for later tests
        
    def log(self, message):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        
    def log_separator(self, title):
        self.log("\n" + "=" * 60)
        self.log(f"  {title}")
        self.log("=" * 60)

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None, no_auth=False):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        test_headers = {'Content-Type': 'application/json'}
        
        # Add auth header unless explicitly disabled (for public endpoints)
        if self.token and not no_auth:
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
                    json_response = response.json() if response.text else {}
                    return success, json_response
                except:
                    # For CSV or binary responses
                    return success, {"content": response.text}
            else:
                self.log(f"❌ {name} - Expected {expected_status}, got {response.status_code}")
                try:
                    error_response = response.json() if response.text else {"detail": "No response body"}
                    self.log(f"   Error: {error_response}")
                except:
                    self.log(f"   Response: {response.text[:200]}")
                self.failed_tests.append(f"{name}: {response.status_code} (expected {expected_status})")
                return False, {}

        except Exception as e:
            self.log(f"❌ {name} - Exception: {str(e)}")
            self.failed_tests.append(f"{name}: {str(e)}")
            return False, {}

    def setup_authentication(self):
        """Login and get auth token"""
        self.log_separator("AUTHENTICATION SETUP")
        success, response = self.run_test(
            "Admin Login",
            "POST",
            "auth/login", 
            200,
            {"email": "admin@grandhotel.com", "password": "admin123"},
            no_auth=True
        )
        if success and 'token' in response:
            self.token = response['token']
            self.log(f"✅ Authentication successful. Token: {self.token[:30]}...")
            return True
        else:
            self.log("❌ Authentication failed - cannot proceed with tests")
            return False

    def test_properties_v2(self):
        """Test Properties V2 CRUD operations"""
        self.log_separator("PROPERTIES V2 CRUD TESTS")
        
        # 1. List properties (should return 2 seeded properties)
        success, properties_response = self.run_test(
            "List Properties V2",
            "GET",
            f"v2/properties/tenants/{self.tenant_slug}/properties",
            200
        )
        if success:
            properties = properties_response if isinstance(properties_response, list) else []
            self.log(f"   Found {len(properties)} properties")
            if len(properties) >= 2:
                self.log("✅ Expected seeded properties found")
                # Store first property for later tests
                if properties:
                    self.test_data['existing_property_id'] = properties[0].get('id')
            else:
                self.log("⚠️  Less than 2 properties found - check seeding")

        # 2. Create new property
        new_property_data = {
            "name": "Test Property",
            "slug": "test-prop", 
            "address": "Test Address, Istanbul",
            "phone": "+90 212 555 0123",
            "email": "test@testproperty.com"
        }
        success, created_property = self.run_test(
            "Create Property V2",
            "POST",
            f"v2/properties/tenants/{self.tenant_slug}/properties",
            200,
            new_property_data
        )
        if success and created_property.get('id'):
            property_id = created_property['id']
            self.test_data['created_property_id'] = property_id
            self.log(f"✅ Property created with ID: {property_id}")

        # 3. Get specific property
        if 'created_property_id' in self.test_data:
            success, property_detail = self.run_test(
                "Get Property V2",
                "GET", 
                f"v2/properties/tenants/{self.tenant_slug}/properties/{self.test_data['created_property_id']}",
                200
            )
            if success:
                self.log(f"✅ Property details retrieved: {property_detail.get('name')}")

        # 4. Update property
        if 'created_property_id' in self.test_data:
            update_data = {"name": "Updated Test Property"}
            success, updated_property = self.run_test(
                "Update Property V2",
                "PATCH",
                f"v2/properties/tenants/{self.tenant_slug}/properties/{self.test_data['created_property_id']}",
                200,
                update_data
            )
            if success:
                self.log(f"✅ Property updated to: {updated_property.get('name')}")

        # 5. Deactivate property
        if 'created_property_id' in self.test_data:
            success, deactivated = self.run_test(
                "Deactivate Property V2",
                "POST",
                f"v2/properties/tenants/{self.tenant_slug}/properties/{self.test_data['created_property_id']}/deactivate",
                200
            )
            if success:
                self.log(f"✅ Property deactivated: {not deactivated.get('is_active', True)}")

        # 6. Reactivate property  
        if 'created_property_id' in self.test_data:
            success, reactivated = self.run_test(
                "Activate Property V2",
                "POST",
                f"v2/properties/tenants/{self.tenant_slug}/properties/{self.test_data['created_property_id']}/activate",
                200
            )
            if success:
                self.log(f"✅ Property reactivated: {reactivated.get('is_active', False)}")

        # 7. Test slug uniqueness (should return 409)
        duplicate_slug_data = {
            "name": "Another Test Property",
            "slug": "test-prop",  # Same slug as before
            "address": "Another Address"
        }
        success, error_response = self.run_test(
            "Test Slug Uniqueness (409 Expected)",
            "POST",
            f"v2/properties/tenants/{self.tenant_slug}/properties",
            409,
            duplicate_slug_data
        )
        if success:
            self.log("✅ Slug uniqueness properly enforced")

    def test_offers_v2(self):
        """Test Offers V2 CRUD and workflow operations"""
        self.log_separator("OFFERS V2 CRUD & WORKFLOW TESTS")
        
        # 1. List offers (should return 4 seeded offers)
        success, offers_response = self.run_test(
            "List Offers V2",
            "GET",
            f"v2/offers/tenants/{self.tenant_slug}/offers",
            200
        )
        if success:
            offers = offers_response.get('data', [])
            total = offers_response.get('total', 0)
            self.log(f"   Found {len(offers)}/{total} offers")
            if len(offers) >= 4:
                self.log("✅ Expected seeded offers found")
            else:
                self.log("⚠️  Less than 4 offers found - check seeding")

        # 2. Test status filtering
        success, sent_offers = self.run_test(
            "Filter Offers by Status (SENT)",
            "GET",
            f"v2/offers/tenants/{self.tenant_slug}/offers?status=SENT",
            200
        )
        if success:
            offers = sent_offers.get('data', [])
            sent_count = sum(1 for o in offers if o.get('status') == 'SENT')
            self.log(f"✅ Status filter working: {sent_count} SENT offers found")

        # 3. Create new offer
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        day_after = (date.today() + timedelta(days=3)).isoformat()
        
        offer_data = {
            "guest_name": "Test Guest",
            "price_total": 1000.0,
            "currency": "TRY",
            "room_type": "standard", 
            "check_in": tomorrow,
            "check_out": day_after,
            "guests_count": 2,
            "notes": "Test offer created via API"
        }
        success, created_offer = self.run_test(
            "Create Offer V2",
            "POST",
            f"v2/offers/tenants/{self.tenant_slug}/offers",
            200,
            offer_data
        )
        if success and created_offer.get('id'):
            offer_id = created_offer['id']
            self.test_data['created_offer_id'] = offer_id
            self.log(f"✅ Offer created with ID: {offer_id}")
            self.log(f"   Status: {created_offer.get('status', 'Unknown')}")

        # 4. Send the offer (DRAFT -> SENT)
        if 'created_offer_id' in self.test_data:
            success, sent_offer = self.run_test(
                "Send Offer V2",
                "POST",
                f"v2/offers/tenants/{self.tenant_slug}/offers/{self.test_data['created_offer_id']}/send",
                200
            )
            if success:
                self.log(f"✅ Offer sent: {sent_offer.get('status')} (expires: {sent_offer.get('expires_at', '')[:16]})")

        # 5. Create payment link
        if 'created_offer_id' in self.test_data:
            success, payment_link = self.run_test(
                "Create Payment Link V2",
                "POST",
                f"v2/offers/tenants/{self.tenant_slug}/offers/{self.test_data['created_offer_id']}/create-payment-link",
                200
            )
            if success and payment_link.get('id'):
                self.test_data['payment_link_id'] = payment_link['id']
                self.log(f"✅ Payment link created: {payment_link.get('url', '')}")

        # 6. Test validation - negative price should fail
        bad_offer_data = {
            "guest_name": "Bad Test",
            "price_total": -100,  # Negative price
            "currency": "TRY",
            "room_type": "standard",
            "check_in": tomorrow,
            "check_out": day_after
        }
        success, error = self.run_test(
            "Negative Price Validation (400 Expected)",
            "POST",
            f"v2/offers/tenants/{self.tenant_slug}/offers",
            400,
            bad_offer_data
        )
        if success:
            self.log("✅ Price validation working")

        # 7. Test date validation - check_out before check_in should fail
        bad_dates_data = {
            "guest_name": "Bad Dates Test",
            "price_total": 500,
            "currency": "TRY", 
            "room_type": "standard",
            "check_in": day_after,  # After check_out
            "check_out": tomorrow   # Before check_in
        }
        success, error = self.run_test(
            "Date Validation (400 Expected)",
            "POST",
            f"v2/offers/tenants/{self.tenant_slug}/offers",
            400,
            bad_dates_data
        )
        if success:
            self.log("✅ Date validation working")

        # 8. Cancel an offer
        if 'created_offer_id' in self.test_data:
            success, cancelled_offer = self.run_test(
                "Cancel Offer V2",
                "POST",
                f"v2/offers/tenants/{self.tenant_slug}/offers/{self.test_data['created_offer_id']}/cancel",
                200
            )
            if success:
                self.log(f"✅ Offer cancelled: {cancelled_offer.get('status')}")

    def test_payments_v2(self):
        """Test Payments V2 mock system with idempotency"""
        self.log_separator("PAYMENTS V2 MOCK SYSTEM TESTS")
        
        # Find a PENDING payment link from seeded data for testing
        success, offers_response = self.run_test(
            "Get Offers to Find Payment Link",
            "GET",
            f"v2/offers/tenants/{self.tenant_slug}/offers",
            200
        )
        
        payment_link_id = None
        if success:
            offers = offers_response.get('data', [])
            for offer in offers:
                if offer.get('payment_link_id'):
                    payment_link_id = offer['payment_link_id']
                    break
        
        # If no existing payment link, create one
        if not payment_link_id and 'created_offer_id' in self.test_data:
            # First create a new offer for payment testing
            tomorrow = (date.today() + timedelta(days=1)).isoformat()
            day_after = (date.today() + timedelta(days=3)).isoformat()
            
            payment_offer_data = {
                "guest_name": "Payment Test Guest",
                "price_total": 750.0,
                "currency": "TRY",
                "room_type": "deluxe",
                "check_in": tomorrow,
                "check_out": day_after,
                "guests_count": 1,
                "notes": "Offer for payment testing"
            }
            success, payment_offer = self.run_test(
                "Create Offer for Payment Test",
                "POST",
                f"v2/offers/tenants/{self.tenant_slug}/offers",
                200,
                payment_offer_data
            )
            if success and payment_offer.get('id'):
                self.test_data['payment_offer_id'] = payment_offer['id']
                
                # Create payment link
                success, payment_link = self.run_test(
                    "Create Payment Link for Test",
                    "POST",
                    f"v2/offers/tenants/{self.tenant_slug}/offers/{payment_offer['id']}/create-payment-link",
                    200
                )
                if success:
                    payment_link_id = payment_link.get('id')
        
        if not payment_link_id:
            self.log("⚠️  No payment link available for testing - using placeholder")
            payment_link_id = "test-payment-link-id"

        self.log(f"   Using payment link ID: {payment_link_id}")

        # 1. Get payment page data (public endpoint)
        success, payment_data = self.run_test(
            "Get Payment Page Data V2",
            "GET",
            f"v2/payments/pay/{payment_link_id}",
            200,
            no_auth=True
        )
        if success:
            self.log(f"✅ Payment page data: {payment_data.get('status', 'Unknown status')}")
            if 'offer' in payment_data:
                offer = payment_data['offer']
                self.log(f"   Offer: {offer.get('room_type', '')} - {offer.get('currency', '')} {offer.get('price_total', 0)}")

        # 2. Checkout (initiate payment)
        success, checkout_result = self.run_test(
            "Checkout Payment V2",
            "POST",
            f"v2/payments/pay/{payment_link_id}/checkout",
            200,
            no_auth=True
        )
        if success:
            self.log(f"✅ Checkout initiated: {checkout_result.get('status', 'Unknown')}")
            if 'payment_id' in checkout_result:
                self.test_data['payment_id'] = checkout_result['payment_id']

        # 3. Mock successful payment
        success, success_result = self.run_test(
            "Mock Payment Success V2",
            "POST",
            "v2/payments/webhook/mock/succeed",
            200,
            {"paymentLinkId": payment_link_id},
            no_auth=True
        )
        if success:
            self.log(f"✅ Payment succeeded: {success_result.get('status', 'Unknown')}")
            if 'reservation' in success_result:
                reservation = success_result['reservation']
                self.test_data['created_reservation_id'] = reservation.get('id')
                self.log(f"   Reservation created: {reservation.get('confirmation_code', 'No code')}")

        # 4. Test idempotency - call success again with same paymentLinkId
        success, idempotent_result = self.run_test(
            "Test Payment Idempotency V2",
            "POST",
            "v2/payments/webhook/mock/succeed",
            200,
            {"paymentLinkId": payment_link_id},
            no_auth=True
        )
        if success:
            is_idempotent = idempotent_result.get('idempotent', False)
            if is_idempotent:
                self.log("✅ Idempotency working - returned existing reservation")
            else:
                self.log("⚠️  Idempotency may not be working properly")

        # 5. Test payment failure (using a different payment link if available)
        # Create another offer for failure test
        tomorrow = (date.today() + timedelta(days=2)).isoformat()
        day_after = (date.today() + timedelta(days=4)).isoformat()
        
        fail_offer_data = {
            "guest_name": "Failure Test Guest",
            "price_total": 250.0,
            "currency": "TRY",
            "room_type": "standard",
            "check_in": tomorrow,
            "check_out": day_after,
            "guests_count": 1,
            "notes": "Offer for failure testing"
        }
        success, fail_offer = self.run_test(
            "Create Offer for Failure Test",
            "POST",
            f"v2/offers/tenants/{self.tenant_slug}/offers",
            200,
            fail_offer_data
        )
        if success and fail_offer.get('id'):
            # Create payment link for failure test
            success, fail_payment_link = self.run_test(
                "Create Payment Link for Failure Test",
                "POST",
                f"v2/offers/tenants/{self.tenant_slug}/offers/{fail_offer['id']}/create-payment-link",
                200
            )
            if success:
                fail_payment_link_id = fail_payment_link.get('id')
                
                # Test payment failure
                success, failure_result = self.run_test(
                    "Mock Payment Failure V2",
                    "POST",
                    "v2/payments/webhook/mock/fail",
                    200,
                    {"paymentLinkId": fail_payment_link_id},
                    no_auth=True
                )
                if success:
                    self.log(f"✅ Payment failure handled: {failure_result.get('status', 'Unknown')}")

    def test_reservations_v2(self):
        """Test Reservations V2 operations"""
        self.log_separator("RESERVATIONS V2 TESTS")
        
        # 1. List reservations (should have 2+ from seeding)
        success, reservations_response = self.run_test(
            "List Reservations V2",
            "GET",
            f"v2/reservations/tenants/{self.tenant_slug}/reservations",
            200
        )
        if success:
            reservations = reservations_response.get('data', [])
            total = reservations_response.get('total', 0)
            self.log(f"   Found {len(reservations)}/{total} reservations")
            if len(reservations) >= 2:
                self.log("✅ Expected seeded reservations found")
                # Store first reservation for detail test
                if reservations:
                    self.test_data['existing_reservation_id'] = reservations[0].get('id')

        # 2. Get specific reservation detail
        if 'existing_reservation_id' in self.test_data:
            success, reservation_detail = self.run_test(
                "Get Reservation Detail V2",
                "GET",
                f"v2/reservations/tenants/{self.tenant_slug}/reservations/{self.test_data['existing_reservation_id']}",
                200
            )
            if success:
                self.log(f"✅ Reservation details: {reservation_detail.get('confirmation_code', 'No code')}")
                self.log(f"   Guest: {reservation_detail.get('guest_name', 'No name')}")
                self.log(f"   Status: {reservation_detail.get('status', 'Unknown')}")

        # 3. Test reservation cancellation (admin only)
        if 'existing_reservation_id' in self.test_data:
            success, cancelled_reservation = self.run_test(
                "Cancel Reservation V2",
                "POST",
                f"v2/reservations/tenants/{self.tenant_slug}/reservations/{self.test_data['existing_reservation_id']}/cancel",
                200
            )
            if success:
                self.log(f"✅ Reservation cancelled: {cancelled_reservation.get('status')}")

        # 4. Export reservations to CSV
        success, csv_response = self.run_test(
            "Export Reservations CSV V2",
            "GET",
            f"v2/reservations/tenants/{self.tenant_slug}/reservations/export/csv",
            200
        )
        if success:
            csv_content = csv_response.get('content', '')
            lines = csv_content.split('\n') if csv_content else []
            self.log(f"✅ CSV export: {len(lines)} lines (including header)")
            if lines and 'Confirmation Code' in lines[0]:
                self.log("   CSV header format correct")

    def test_inbox_create_offer(self):
        """Test Inbox create-offer endpoint"""
        self.log_separator("INBOX CREATE-OFFER TESTS")
        
        # First, get or create a conversation for testing
        success, conversations_response = self.run_test(
            "List Conversations for Inbox Test",
            "GET",
            f"v2/inbox/tenants/{self.tenant_slug}/conversations",
            200
        )
        
        conversation_id = None
        if success:
            conversations = conversations_response.get('data', [])
            if conversations:
                conversation_id = conversations[0]['id']
            
        # If no conversations, try the old API
        if not conversation_id:
            success, old_convs = self.run_test(
                "List Old API Conversations",
                "GET",
                f"tenants/{self.tenant_slug}/conversations",
                200
            )
            if success and old_convs:
                conversation_id = old_convs[0]['id']

        if not conversation_id:
            self.log("⚠️  No conversations found for inbox test - creating mock test")
            conversation_id = "test-conversation-id"

        self.log(f"   Using conversation ID: {conversation_id}")

        # Test create offer from inbox conversation
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        day_after = (date.today() + timedelta(days=3)).isoformat()
        
        inbox_offer_data = {
            "guest_name": "Inbox Test Guest",
            "guest_email": "inbox@test.com",
            "guest_phone": "+905551234999",
            "price_total": 850.0,
            "currency": "TRY",
            "room_type": "deluxe",
            "check_in": tomorrow,
            "check_out": day_after,
            "guests_count": 2,
            "notes": "Offer created from inbox conversation"
        }
        
        success, inbox_offer_result = self.run_test(
            "Create Offer from Inbox V2",
            "POST",
            f"v2/inbox/tenants/{self.tenant_slug}/conversations/{conversation_id}/create-offer",
            200,
            inbox_offer_data
        )
        if success:
            offer = inbox_offer_result.get('offer', {})
            contact_id = inbox_offer_result.get('contact_id', '')
            self.log(f"✅ Offer created from inbox: {offer.get('id', 'No ID')}")
            self.log(f"   Contact created/linked: {contact_id}")
            self.log(f"   Source: {offer.get('source', 'Unknown')}")
            
            if offer.get('id'):
                self.test_data['inbox_offer_id'] = offer['id']

    def test_full_flow(self):
        """Test complete end-to-end flow: Create offer -> Send -> Payment -> Reservation"""
        self.log_separator("FULL END-TO-END FLOW TEST")
        
        # 1. Create offer
        tomorrow = (date.today() + timedelta(days=5)).isoformat()
        day_after = (date.today() + timedelta(days=7)).isoformat()
        
        flow_offer_data = {
            "guest_name": "Flow Test Guest",
            "guest_email": "flowtest@example.com",
            "guest_phone": "+905559876543",
            "price_total": 1200.0,
            "currency": "TRY",
            "room_type": "suite", 
            "check_in": tomorrow,
            "check_out": day_after,
            "guests_count": 2,
            "notes": "End-to-end flow test offer"
        }
        
        success, flow_offer = self.run_test(
            "Flow: Create Offer",
            "POST",
            f"v2/offers/tenants/{self.tenant_slug}/offers",
            200,
            flow_offer_data
        )
        if not success or not flow_offer.get('id'):
            self.log("❌ Flow test stopped - could not create offer")
            return
            
        flow_offer_id = flow_offer['id']
        self.log(f"✅ Flow offer created: {flow_offer_id}")

        # 2. Send offer
        success, sent_offer = self.run_test(
            "Flow: Send Offer",
            "POST",
            f"v2/offers/tenants/{self.tenant_slug}/offers/{flow_offer_id}/send",
            200
        )
        if not success:
            self.log("❌ Flow test stopped - could not send offer")
            return
        self.log(f"✅ Flow offer sent: {sent_offer.get('status')}")

        # 3. Create payment link
        success, flow_payment_link = self.run_test(
            "Flow: Create Payment Link",
            "POST",
            f"v2/offers/tenants/{self.tenant_slug}/offers/{flow_offer_id}/create-payment-link",
            200
        )
        if not success or not flow_payment_link.get('id'):
            self.log("❌ Flow test stopped - could not create payment link")
            return
            
        flow_payment_link_id = flow_payment_link['id']
        self.log(f"✅ Flow payment link created: {flow_payment_link_id}")

        # 4. Mock successful payment
        success, flow_success_result = self.run_test(
            "Flow: Mock Payment Success",
            "POST",
            "v2/payments/webhook/mock/succeed",
            200,
            {"paymentLinkId": flow_payment_link_id},
            no_auth=True
        )
        if not success:
            self.log("❌ Flow test stopped - payment failed")
            return
            
        self.log(f"✅ Flow payment succeeded: {flow_success_result.get('status')}")

        # 5. Verify reservation was created
        if 'reservation' in flow_success_result:
            reservation = flow_success_result['reservation']
            confirmation_code = reservation.get('confirmation_code', 'No code')
            self.log(f"✅ Flow reservation created: {confirmation_code}")
            self.log(f"   Guest: {reservation.get('guest_name', 'No name')}")
            self.log(f"   Room: {reservation.get('room_type', 'No type')}")
            self.log(f"   Total: {reservation.get('currency', '')} {reservation.get('price_total', 0)}")
            
            # Store for final verification
            self.test_data['flow_reservation_id'] = reservation.get('id')
            
            # 6. Verify reservation appears in reservations list
            success, final_reservations = self.run_test(
                "Flow: Verify Reservation in List",
                "GET",
                f"v2/reservations/tenants/{self.tenant_slug}/reservations",
                200
            )
            if success:
                reservations = final_reservations.get('data', [])
                flow_reservation = next((r for r in reservations if r.get('confirmation_code') == confirmation_code), None)
                if flow_reservation:
                    self.log(f"✅ Flow reservation verified in list: {flow_reservation.get('status')}")
                else:
                    self.log("⚠️  Flow reservation not found in list - possible sync issue")
                    
            self.log("🎉 FULL END-TO-END FLOW COMPLETED SUCCESSFULLY!")
        else:
            self.log("❌ Flow test incomplete - no reservation returned")

    def run_all_tests(self):
        """Execute all Sprint 5 V2 endpoint tests"""
        self.log("🚀 Starting Sprint 5 V2 Endpoints Comprehensive Testing")
        self.log("Testing: Properties V2, Offers V2, Payments V2, Reservations V2, Inbox create-offer")
        self.log("=" * 80)
        
        # Setup authentication first
        if not self.setup_authentication():
            self.log("💥 Authentication failed - cannot proceed with tests")
            return False

        # Run test suites
        try:
            self.test_properties_v2()
            self.test_offers_v2()
            self.test_payments_v2() 
            self.test_reservations_v2()
            self.test_inbox_create_offer()
            self.test_full_flow()
        except Exception as e:
            self.log(f"💥 Test execution error: {str(e)}")
            self.failed_tests.append(f"Test execution error: {str(e)}")

        # Print final results
        self.log("\n" + "=" * 80)
        self.log("📊 SPRINT 5 V2 TEST RESULTS")
        self.log("=" * 80)
        self.log(f"📈 Tests Run: {self.tests_run}")
        self.log(f"✅ Tests Passed: {self.tests_passed}")
        self.log(f"❌ Tests Failed: {len(self.failed_tests)}")
        
        if self.tests_run > 0:
            success_rate = (self.tests_passed / self.tests_run) * 100
            self.log(f"📊 Success Rate: {success_rate:.1f}%")
        
        if self.failed_tests:
            self.log(f"\n💥 FAILED TESTS ({len(self.failed_tests)}):")
            for i, failed in enumerate(self.failed_tests, 1):
                self.log(f"   {i}. {failed}")
        else:
            self.log(f"\n🎉 ALL TESTS PASSED! Sprint 5 V2 endpoints are working correctly.")
        
        # Return True if all tests passed
        return len(self.failed_tests) == 0

def main():
    """Main test execution"""
    tester = Sprint5V2Tester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ Sprint 5 V2 endpoints testing completed successfully!")
        return 0
    else:
        print(f"\n❌ Sprint 5 V2 endpoints testing completed with {len(tester.failed_tests)} failures.")
        return 1

if __name__ == "__main__":
    exit(main())