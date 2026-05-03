# Omni Inbox Hub

A comprehensive multi-tenant SaaS platform for the hospitality and service industries (hotels, restaurants, clinics). Provides a centralized dashboard for managing guest requests, room service, reservations, loyalty programs, and AI-driven guest communication.

## Architecture

- **Frontend**: React 19 + Tailwind CSS + Shadcn UI, built with CRACO (Create React App), runs on port 5000
- **Backend**: FastAPI (Python) with async MongoDB (motor), runs on port 8000
- **Database**: MongoDB Atlas (cloud, configured via `MONGO_URL`)
- **AI/ML**: OpenAI, Google Generative AI, LiteLLM for AI replies

## Project Structure

```
/
├── frontend/          # React SPA (CRACO-based)
│   ├── src/
│   │   ├── pages/     # Feature pages (Dashboard, Inbox, AI Sales, etc.)
│   │   │   └── guest/ # Guest portal (GuestRoomPanel + components/ + dialogs/ + GuestContext + constants)
│   │   ├── components/ # UI components (Shadcn/Radix UI)
│   │   └── lib/       # API client, WebSocket, Zustand store
│   └── plugins/       # Custom webpack plugins (visual-edits, health-check)
├── backend/           # FastAPI backend
│   ├── server.py      # Main entry point (~730 lines, websocket + auth + tenants + only 1 legacy route remaining; T007 Faz 1+2 complete)
│   │                  # Extracted modules: rooms, orders, contacts, analytics, demo-seed, guest-resolve,
│   │                  # legacy_restaurant (tables/menu), legacy_qr, legacy_engagement (reviews/connectors/offers/payments-mock), legacy_misc (comments/kb/reservations/contacts-intel/audit-logs)
│   ├── routers/       # Modular API routers (auth, tenants, billing, system, hotel, restaurant, inbox, etc.)
│   ├── services/      # Business logic + external provider integrations
│   ├── connectors/    # Third-party platform connectors
│   └── core/          # Config, middleware, tenant guards
├── data/db/           # MongoDB data directory
├── start.sh           # Startup script (MongoDB + backend + frontend)
└── tests/             # Pytest test suites
```

## Environment Variables

- `MONGO_URL`: MongoDB Atlas connection URL (mongodb+srv://...) — **REQUIRED**, no local fallback
- `DB_NAME`: MongoDB database name (default: `omni_inbox_hub`, currently `syroce-sadakat`)
- `JWT_SECRET`: JWT signing secret
- `OPENAI_API_KEY`: Optional - for AI reply features
- `REACT_APP_BACKEND_URL`: Backend URL for frontend (set to `http://localhost:8000` in dev)

## Running the Application

```bash
bash start.sh
```

This starts:
1. MongoDB on port 27017
2. FastAPI backend on port 8000
3. React frontend on port 5000

## Performance Optimizations (May 2026)

Audit-driven N+1 elimination across hot analytics paths. All preserve original semantics; verified by architect review.

| Endpoint | Before | After | Technique |
|---|---:|---:|---|
| `/api/tenants/{slug}/stats` | ~1.5s | 1.0s | `asyncio.gather` (11 parallel queries) |
| `/api/tenants/{slug}/stats/enhanced` | 6.5s | 1.0s | `asyncio.gather` (32 parallel queries) |
| `/api/v2/reports/.../department-performance` | 7.8s | 0.8s | Single `$group` aggregation w/ pre-parsed dates |
| `/api/v2/loyalty-analytics/.../cohort` | 5.1s | 0.76s | Two parallel aggregations + `$substr` month grouping |
| `/api/v2/loyalty-analytics/.../rfm` | 2.8s | 0.76s | Single ledger aggregation + bulk contact fetch |
| `/api/v2/social/.../dashboard` | 5.5s | 0.76s | 6 parallel grouped aggregations |
| `/api/v2/social/.../analytics` | ~3.5s | 0.76s | 4 parallel queries with date-bucket pipelines |

**Floor:** ~700ms = MongoDB Atlas RTT (Syroce cluster). Lower requires Redis layer.

**Indexes added** (`backend/server.py:create_indexes`):
- `guest_requests`: `(tenant_id, created_at)`, `(tenant_id, department_code, created_at)`, `(tenant_id, rating)` sparse
- `loyalty_accounts`: `(tenant_id, enrolled_at)`
- `spa_bookings`, `restaurant_reservations`, `transport_requests`, `laundry_requests`, `notifications`, `lost_found`: all `(tenant_id, status)`
- `guest_surveys`: `(tenant_id, created_at)`

**Frontend fixes:** Silent `try/catch` blocks in `OnboardingPage.js`, `GuestRoomPanel.js` (×2), `GuestTablePanel.js`, `LoyaltyTab.js` now log via `console.error`.

### Cache Layer (`backend/core/cache.py`)

In-process async TTL cache with single-flight de-duplication. Drop-in compatible with Redis (`get` / `setex` / `delete` / `delete_prefix`) so a future swap to `redis.asyncio` is one line. Currently used on the 7 hot endpoints above.

**Cache hit performance (combined w/ 10s user-auth cache):** all 7 hot endpoints now **3-4ms** on cache hit (originally 2.8-7.8s — up to **2,600x faster**). Auth user lookup also cached 10s in `core/tenant_guard.py:get_current_user` so authed endpoints no longer pay MongoDB RTT.

**Security:** `/cache-stats` and `/cache-clear` require `owner|admin|superadmin` role. Single-flight uses `BaseException` so cancelled tasks never hang waiters.

**Round 2 cached endpoints (added):**
- `/inbox/conversations` — 3.25s → **256ms** (12.7x). N+1 collapsed: per-conv last_msg/count was 90 round-trips → single `$group` aggregation; contacts batch-fetched. 30s TTL.
- `/sla/sla-stats` — 1.52s → **146ms** (10.4x). 500-doc Python loop replaced with `$dateFromString`+`$avg` pipeline; 4 queries parallel via `asyncio.gather`. 60s TTL.
- `/notifications` — 1.01s → **257ms** (4x). 3 sequential queries → `asyncio.gather`. 15s TTL.

**TTL strategy:**
- Live dashboard stats: 30s
- Reports / social: 60s
- Inbox/notifications: 15-30s (write-heavy)
- Loyalty analytics (cohort, rfm): 120s

**Ops endpoints:**
- `GET /api/system/cache-stats` → `{hits, misses, hit_rate, size}`
- `POST /api/system/cache-clear` (auth required) → manual flush

**Note:** Single-process in-memory. For multi-worker production, set `REDIS_URL` and swap the backing store in `core/cache.py` (interface already matches `redis.asyncio`).

## Key Features

- **Multi-tenant**: Isolated per tenant via `tenant_id`. **TenantIsolationMiddleware** (`backend/core/middleware.py`) enforces fail-closed cross-tenant guard on all `/api/.../tenants/{slug}/...` routes — JWT `tenant_id` claim must match resolved slug. 60s TTL slug→tenant_id cache with negative caching. Public/guest paths (`/api/g/`, `/api/auth/`, `/api/v2/payments/pay/`, webhooks, etc.) are skipped.
- **Property Scoping**: Multiple properties under one tenant via `X-Property-Id` header
- **AI Sales Engine**: Automated guest inquiry handling and upsell suggestions
- **Unified Inbox**: Meta (WhatsApp/Facebook) and other channel integrations
- **Loyalty Program**: Points, tiers, gamification (LoyaltyTab with OTP-based join)
- **Real-time**: WebSocket updates per tenant channel
- **Digital Check-in**: Pre-arrival form with ID upload
- **Express Check-out**: Folio review + confirmation + rating
- **Room Reservation**: Guest portal availability check + booking
- **i18n**: 8 languages (EN/TR/AR/DE/RU/FR/ES/ZH) via `frontend/src/lib/i18n.js`
- **Payments**: Dual-mode Stripe (real when STRIPE_SECRET_KEY set, stub otherwise)
- **PMS Integration**: Adapter pattern for Opera/Mews/Cloudbeds (`routers/pms_integration.py`)
- **File Storage**: Dual-mode S3/local (`routers/storage.py`)
- **Guest Portal**: QR-code-based room/table access for guests
- **Personalized Welcome**: Room-specific guest greeting ("Welcome, Ahmed!") based on current occupant
- **Room Folio**: Guests can view all in-stay charges (room service, minibar, spa, laundry, transport) via QR panel
- **Guest Services**: 14+ service categories including spa booking, transport, laundry, wake-up calls, restaurant reservations
- **Guest Push Notifications**: Web Push notifications when request status changes (TR/EN) — "Çamaşırlarınız hazır", "Siparişiniz yola çıktı" — with per-category preference toggles. In-app notification panel with unread badges. Hooked into all admin status update endpoints (requests, orders, spa, transport, laundry, wake-up calls).
