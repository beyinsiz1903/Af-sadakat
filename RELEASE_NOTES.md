# Sprint 5 Release Notes
## Version 5.0.0 - Multi-Property + Offers/Reservations V2 + Mock Payments

### New Features

#### A) Multi-Property Support
- **Properties CRUD**: Tenants can manage multiple properties (e.g., Main Building, Annex)
- **Property Switcher**: Dropdown in the top bar to switch between properties
- **Property-scoped data**: Rooms, tables, offers, and reservations can be scoped to properties
- **Seed data**: 2 properties pre-loaded (Grand Hotel Istanbul - Main, Annex)

#### B) Offers V2 (Sales Flow)
- **Full lifecycle**: DRAFT -> SENT -> PAID/EXPIRED/CANCELLED
- **Create offers** with guest details, room type, dates, price
- **Send offers** (sets 48h expiry)
- **Payment links**: Generate payment link URLs for guest checkout
- **Auto-expiration**: Background task expires SENT offers past their expires_at
- **Status filtering**: Filter offers by status in the UI
- **Stats cards**: Offers Sent, Paid, Reservations, Conversion Rate

#### C) Mock Payments V2
- **Payment public page** at `/pay/:paymentLinkId` - guest checkout without auth
- **Idempotent webhooks**: `POST /webhook/mock/succeed` is safe to call multiple times
- **Checkout flow**: Initiates payment -> succeeds -> creates reservation
- **Confirmation codes**: Human-readable codes (RES-XXXXXX)
- **Rate limiting**: 30 requests/min per IP on public payment endpoints

#### D) Reservations V2
- **List/Detail**: View all reservations with confirmation codes
- **Cancel**: Admin/Manager only can cancel reservations
- **CSV Export**: Download reservations as CSV

#### E) Inbox-to-Sale Automation
- **"Create Offer" button** in inbox conversation view
- **Modal**: Select room type, dates, price directly from conversation
- **Source tracking**: Offers created from inbox tagged with `source: INBOX`
- **Contact linking**: Auto-creates/links contact from conversation
- **After creation**: Send offer, create payment link, copy URL - all from modal

#### F) Go-Live Hardening
- **Enhanced health endpoint**: Returns MongoDB connectivity status + version
- **Rate limiting**: Public payment endpoints limited to 30/min per IP
- **Idempotency**: Payment succeed webhook is fully idempotent
- **Validation**: Date range, positive price, slug uniqueness
- **Audit logging**: All admin actions logged (offer created, sent, payment succeeded, reservation created/cancelled)
- **Offer expiration**: Background task runs every 60s

### How to Demo

1. **Login**: `admin@grandhotel.com` / `admin123`
2. **Property Switcher**: Click the property name in the top bar to switch between Main and Annex
3. **Properties Page**: `/properties` - view, create, edit, activate/deactivate properties
4. **Offers Flow**:
   - Go to `/offers`
   - Click "Create Offer" -> fill details -> submit
   - Click "Send Offer" -> offer moves to SENT status
   - Click "Create Payment Link" -> URL is generated and copied
   - Click "Simulate Payment" -> reservation is created
   - Switch to Reservations tab to see confirmation code
5. **Payment Page**:
   - Copy a payment link URL from an offer
   - Open it in a new browser/incognito tab (no login needed)
   - Click "Pay Now (Mock)" -> confirmation code shown
6. **Inbox Offer**:
   - Go to `/inbox` -> select a conversation
   - Click "Create Offer" button in header
   - Fill details and submit
   - Send offer and create payment link from the success dialog
7. **Audit Log**: `/audit` - see all logged actions

### API Endpoints

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v2/properties/tenants/{slug}/properties` | GET/POST | Yes | List/Create properties |
| `/api/v2/properties/tenants/{slug}/properties/{id}` | GET/PATCH | Yes | Get/Update property |
| `/api/v2/offers/tenants/{slug}/offers` | GET/POST | Yes | List/Create offers |
| `/api/v2/offers/tenants/{slug}/offers/{id}/send` | POST | Yes | Send offer |
| `/api/v2/offers/tenants/{slug}/offers/{id}/create-payment-link` | POST | Yes | Create payment link |
| `/api/v2/payments/pay/{linkId}` | GET | No | Payment page data |
| `/api/v2/payments/pay/{linkId}/checkout` | POST | No | Start payment |
| `/api/v2/payments/webhook/mock/succeed` | POST | No | Mock payment success |
| `/api/v2/reservations/tenants/{slug}/reservations` | GET | Yes | List reservations |
| `/api/v2/reservations/tenants/{slug}/reservations/export/csv` | GET | Yes | Export CSV |
| `/api/v2/inbox/tenants/{slug}/conversations/{id}/create-offer` | POST | Yes | Create offer from inbox |

### Known Issues / TODOs
- Property-scoped filtering on rooms/tables pages is available via backend but not yet wired to X-Property-Id header in frontend API calls
- Real payment gateway integration planned for next sprint (currently mock only)
- Guest QR URL property slug support (backward compatible with existing QRs)
- Email/SMS notification for offer sent/payment confirmed not yet implemented
