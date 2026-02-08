# Release Notes v6.0.0 - Pilot Hardening + Production Stabilization

## Overview
Sprint 6 focuses exclusively on stability, security, observability, and pilot readiness.
No new business features were added. All Sprint 1-5 features are preserved.

## Changes

### 1. Observability & Logging
- **Request ID Middleware**: Every HTTP request gets a unique `X-Request-Id` header
- **Structured JSON Logging**: All requests logged with `request_id`, `method`, `path`, `status`, `duration_ms`, `tenant_id`, `property_id`
- **Global Exception Handler**: Unhandled exceptions return clean JSON errors; stack traces logged internally only
- **Health Endpoint v6**: `GET /api/health` returns:
  ```json
  {
    "status": "ok",
    "version": "6.0.0",
    "uptime_seconds": 123.4,
    "services": { "mongodb": true, "redis": true }
  }
  ```

### 2. Property Header Enforcement
- **X-Property-Id Header**: Frontend axios interceptor automatically injects from localStorage
- **Property Resolution**: Backend validates property belongs to tenant; falls back to default property
- **Property Change Event**: `window.dispatchEvent('property-changed')` on switch for refetch

### 3. Confirmation Code Hardening
- **New Format**: `PREFIX-YYYYMM-XXXXXX` (e.g., `GHI-202602-A7KF29`)
- **Property Prefix**: First 3 chars of property slug (uppercase)
- **Unique Index**: Enforced via MongoDB unique index
- **Retry Logic**: Up to 5 retries on collision, then appends extra random chars

### 4. Payment Safety
- **Atomic Idempotency**: Uses MongoDB atomic `update_one` with `status != SUCCEEDED` guard
- **Race Condition Prevention**: Two simultaneous webhook calls cannot create duplicate reservations
- **Amount Validation**: Logs warning if payment amount differs from offer price
- **Status Validation**: Logs warning if offer is EXPIRED/CANCELLED when payment succeeds

### 5. Notification Engine (Mock)
- **notification_service.py**: Provider interface for future email/SMS integration
- **MockNotificationProvider**: Logs structured JSON to console
- **Template Types**: OFFER_SENT, PAYMENT_SUCCEEDED, RESERVATION_CONFIRMED, REQUEST_CREATED, ORDER_COMPLETED
- **DB Records**: All notifications stored in `notifications` collection
- **Audit Logged**: Every notification creates an audit log entry

### 6. Offer Expiration Robustness
- **Atomic Updates**: Each offer expired individually with `status: SENT` guard
- **Contact Events**: OFFER_EXPIRED event created for contact timeline
- **WebSocket Broadcast**: `offer.expired` event sent to connected clients
- **No Double-Expiration**: Atomic check prevents processing already-expired offers

### 7. Rate Limiting
- **Public Payment Endpoints**: 30 requests/min per IP
  - `GET /api/v2/payments/pay/:id`
  - `POST /api/v2/payments/pay/:id/checkout`
  - `POST /api/v2/payments/webhook/mock/succeed`
  - `POST /api/v2/payments/webhook/mock/fail`
- **Centralized Rate Limiter**: `core/middleware.py::rate_limit_ip()`

### 8. CLI Data Export
- **Command**: `python manage.py export --tenant grand-hotel`
- **Exports**: contacts.csv, reservations.csv, offers.csv, loyalty_members.csv
- **Tenant Scoped**: All exports filtered by tenant_id
- **Output**: `/tmp/omnihub_export_{slug}_{timestamp}/`

### 9. PII Masking
- **mask_pii()**: Utility masks emails and phone numbers in log strings
- **Notification Audit**: Email/phone partially masked in audit log details

## How to Verify

1. **Health**: `curl /api/health` - check version 6.0.0, uptime, services
2. **Request ID**: Check `X-Request-Id` header in any response
3. **Confirmation Code**: Create offer -> payment -> check code format `XXX-YYYYMM-XXXXXX`
4. **Idempotency**: Call mock/succeed twice -> second returns `idempotent: true`
5. **Notifications**: Check audit logs for `NOTIFICATION_*` entries after payment
6. **Export**: `cd /app/backend && python manage.py export --tenant grand-hotel`

## Known Issues
- Property-scoped filtering in V2 routers uses header when present; backend falls back to default
- Real notification delivery (SMTP/SMS) requires provider integration (placeholder ready)
- Redis shown as `true` in health but not actively used (future caching layer)
