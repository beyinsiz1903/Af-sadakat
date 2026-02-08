# Sprint 5 Pilot Go-Live Checklist

## Pre-Launch

### Infrastructure
- [ ] DNS configured for production domain
- [ ] SSL/TLS certificates installed and auto-renewing
- [ ] MongoDB replica set configured with backups enabled
- [ ] Environment variables set (MONGO_URL, JWT_SECRET, PUBLIC_BASE_URL, etc.)
- [ ] CORS_ORIGINS restricted to production domains only
- [ ] Rate limiter configuration verified

### Tenant Setup
- [ ] Create production tenant via `/api/auth/register`
- [ ] Configure tenant settings (hotel_enabled, restaurant_enabled, plan)
- [ ] Create properties for the tenant
- [ ] Set up departments and service categories
- [ ] Create rooms and tables with secure QR codes
- [ ] Set up menu if restaurant is enabled
- [ ] Enable loyalty rules if desired

### QR Code Printing
- [ ] Generate room QR codes: `GET /api/v2/hotel/rooms/print.pdf?ids=...`
- [ ] Generate table QR codes (similar endpoint)
- [ ] Print and place QR codes in rooms/tables
- [ ] Test scanning with guest phone -> verify room/table panel loads

### Connector Stubs
- [ ] Enable WEBCHAT connector (built-in)
- [ ] Configure WhatsApp stub (via Connectors page)
- [ ] Configure Instagram stub (via Connectors page)
- [ ] Test message flow through each channel

### User Accounts
- [ ] Create staff accounts with appropriate roles (agent, manager, admin)
- [ ] Test login for each role
- [ ] Verify role-based access (agents can create offers, only admin/manager can cancel reservations)

## Launch Day

### Smoke Tests
- [ ] Login works
- [ ] Dashboard loads with stats
- [ ] Property switcher works
- [ ] Create and send an offer
- [ ] Payment link generation works
- [ ] Mock payment -> reservation creation works
- [ ] Guest QR scan -> room panel works
- [ ] Inbox conversations load
- [ ] Create offer from inbox works
- [ ] Audit log captures actions

### Monitoring
- [ ] Check `/api/health` returns `{"status": "ok"}`
- [ ] Monitor backend logs for errors
- [ ] Verify WebSocket connections work for real-time updates
- [ ] Check offer expiration task is running (offers auto-expire after 48h)

## Data Backup & Export
- [ ] MongoDB dump configured: `mongodump --uri=$MONGO_URL`
- [ ] Reservation CSV export: `/api/v2/reservations/tenants/{slug}/reservations/export/csv`
- [ ] CRM contacts export: `/api/v2/crm/tenants/{slug}/contacts/export`
- [ ] Guest data export (GDPR): `/api/tenants/{slug}/compliance/export/{contactId}`

## Post-Launch
- [ ] Monitor conversion rates (Offers -> Paid)
- [ ] Review audit logs for unusual activity
- [ ] Gather feedback from front desk staff
- [ ] Plan real payment gateway integration (Stripe/iyzico)
- [ ] Plan email/SMS notifications for offer/reservation events
