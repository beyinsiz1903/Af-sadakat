# plan.md (PHASE 5 UPDATED)

## 1) Objectives
- **Upgrade OmniHub into a production-grade SaaS**: an **AI-powered Guest Operating System for Hospitality** (Hotels + Restaurants) on the confirmed **FARM stack**:
  - **FastAPI + React + MongoDB**
  - **Redis** (scheduling, caching, rate limiting, pub/sub)
  - **WebSocket** (real-time)
- **Do not change core architecture**. **Do not remove existing features**. Only extend/harden.
- Make the platform:
  - **Security-hardened** (enterprise auth/session controls, rate limiting, audit trails)
  - **Billing-ready** (plans, subscriptions, invoices, provider interface, Stripe stub)
  - **Strictly enforced** (usage/limits per plan, metering, upgrade flow)
  - **Self-serve** (onboarding wizard, QR automation, invite team)
  - **Analytics-driven** (revenue + ops analytics, staff performance, AI efficiency)
  - **Compliance-capable** (KVKK/GDPR export/delete/anonymize, retention policy)
  - **Scalable** (indexes, cache, background jobs, WS pub/sub)
  - **Growth-enabled** (referrals, rewards, demo mode, investor metrics)
  - **Observable** (structured logs, request IDs, health/system status, metrics)

**Current Status (Phases 1–4)**
- ✅ **Phase 1 Complete** (Core POC): 44/44 tests passed.
- ✅ **Phase 2 Complete** (V1 App): 98% overall.
- ✅ **Phase 3 Complete** (RBAC + Guest Intelligence v1 + Loyalty tiers + Audit baseline).
- ✅ **Phase 4 Complete** (Sales engine: connectors stubs + reviews + offers/payments/reservations + enhanced dashboard).

**Testing Status (latest)**
- ✅ **Overall: 99%**
  - Backend: **96% (24/25 tests passed)**
  - Frontend: **100%**
  - Integration: **100%**
  - Guest panels: **100%**

---

## 2) Implementation Steps (Phased)

### Phase 1 — Core POC (Isolation) (**COMPLETE**)
**Goal:** Validate the core that can break the whole product: tenant isolation + WebSocket fanout + QR guest flows.

User stories (validated):
1. Guest can open a room QR link and submit a request without logging in.
2. Staff sees new room requests appear in real time without refreshing.
3. Guest can open a table QR link and place an order.
4. Kitchen/staff sees incoming orders in real time and can update status.
5. System guarantees no cross-tenant data leakage.

Deliverables:
- ✅ POC endpoints + WS contract
- ✅ `poc_ws_multitenant.py` with **44/44 passing**

---

### Phase 2 — V1 App Development (MVP UI + API) (**COMPLETE**)
**Goal:** Build the full working MVP around proven POC flows; ship guest + staff UIs; provide investor/customer demo readiness.

Delivered:
- ✅ Admin/staff UI (dashboard, requests, orders, rooms, tables, menu, contacts, settings)
- ✅ Guest UI (room requests, table ordering/cart, webchat)
- ✅ WebSocket real-time updates
- ✅ AI mock provider (TR/EN)
- ✅ Seed demo tenant

---

### Phase 3 — Enterprise-shaped Foundation (RBAC + Intelligence v1 + Loyalty tiers + Audit) (**COMPLETE**)
Delivered:
- ✅ RBAC roles and permission matrix foundation
- ✅ Guest Intelligence v1 (contact intelligence endpoint)
- ✅ Loyalty tiers (bronze/silver/gold/platinum)
- ✅ Audit log endpoint (baseline)

---

### Phase 4 — Sales Engine (Connectors stubs + Reviews + Offers/Payments/Reservations + Enhanced Dashboard) (**COMPLETE**)
Delivered:
- ✅ Connector framework with stubs (WA/IG/Google/TripAdvisor)
- ✅ Reviews module (sentiment + AI reply)
- ✅ Offers → payment link → simulate payment → reservation
- ✅ Enhanced dashboard stats

---

### Phase 5 — Production-Grade SaaS Upgrade (**IN SCOPE / NEXT**) 
**Goal:** Convert the product from “sellable v1” into a **production-grade SaaS** with full security hardening, plan/billing readiness, onboarding automation, deep analytics, compliance, performance/scalability, growth infrastructure, and observability.

**Implementation approach (confirmed)**
- Backend: create modular files and extend `server.py` without breaking existing routes:
  - `security.py` (refresh tokens, sessions, rate limit, brute force, CSRF, CORS)
  - `billing.py` (billing models, subscription lifecycle, invoices, provider interface)
  - `usage.py` (usage metering, enforcement, reset jobs)
  - `analytics.py` (revenue + ops analytics engine)
  - `compliance.py` (KVKK/GDPR export/delete/anonymize/retention)
  - `referral.py` (referral codes, tracking, rewards)
  - `observability.py` (structured logs, request IDs, system status, metrics)
- Frontend: add new pages and enhance existing pages:
  - Onboarding wizard
  - Billing page
  - Analytics page/widgets
  - Compliance page
  - Growth/Referral page
  - SecuritySettings page
  - Upgrade modal + plan gating UI
- Infra: keep current stack; **add Redis usage** for:
  - rate limiting
  - scheduled jobs (monthly usage reset, retention purge)
  - caching hot reads (dashboard/menu)
  - WS pub/sub scaling (future-ready)

---

## 2.1) Phase 5 Workstreams (Detailed)

### 5.1 Production Security Hardening
**Target outcomes**: account takeover resistance, predictable sessions, throttled abuse, auditable sensitive actions.

Implement:
- **Refresh token rotation** with token family invalidation
- **Device session tracking** (device_id, user_agent, ip, created_at, last_seen_at)
- **IP-based rate limiting** (global + per tenant + per route class)
- **Brute-force protection** (lockout after 5 failed logins for X minutes)
- **WebSocket auth re-validation every 15 minutes**
- **CSRF protection** (for cookie-based auth flows; keep JWT header support)
- **Strict CORS** (no `*` in production)
- **AuditLog expansion**:
  - login/logout
  - role change
  - connector update
  - billing events
  - usage limit events
- **Sensitive fields masking in logs** (email/phone/payment metadata)
- **Encryption at rest** (field-level wrapper)
  - connector credentials
  - loyalty ledger sensitive payload
  - reservation payment metadata

Add UI:
- **SecuritySettings page** (Admin-only)
  - sessions list + revoke
  - 2FA toggle placeholder (Pro)
  - IP allowlist placeholder (Enterprise)

Deliverables:
- New collections: `sessions`, `refresh_tokens`, `login_attempts`
- New endpoints: `/auth/refresh`, `/auth/logout`, `/auth/sessions`, `/auth/sessions/revoke`
- Middleware: rate limit, brute-force, request-id, masking logger
- WS: `auth_ping` + forced disconnect on invalid token

---

### 5.2 SaaS Plan Enforcement System (BASIC/PRO/ENTERPRISE)
**Target outcomes**: every monetizable resource is enforced; UI shows real-time usage and upgrade path.

Plans:
- **BASIC / PRO / ENTERPRISE**

Strict enforcement on:
- max users
- max rooms/tables
- max AI replies/month
- max contacts
- max monthly reservations
- max active offers

Behavior:
- block action when limit reached
- show **upgrade modal**
- log **usage_limit_reached** audit event

Add:
- `UsageMeter` collection (monthly)
- monthly reset job (Redis scheduler)

Deliverables:
- Central enforcement helper: `enforce_limit(tenant_id, metric, amount=1)`
- Cross-cutting enforcement points:
  - user create
  - room/table create
  - contact create/import
  - AI suggest reply
  - offer create
  - reservation create
- UI: Billing/Usage summary + upgrade modal

---

### 5.3 Billing-Ready Architecture (No real Stripe)
**Target outcomes**: subscription lifecycle modeled, provider pluggable, webhooks stubbed.

Implement models:
- `BillingAccount`
- `Subscription`
- `Invoice`
- `PaymentMethod` (stub)

Implement:
- `PaymentProvider` interface
- Expand `StripeStubProvider` (already exists)
- Webhook endpoint placeholder: `/billing/webhook/stripe`

Add UI:
- **Billing page**
  - current plan
  - usage stats
  - upgrade button (plan selection)
  - payment history (mock invoices)

Deliverables:
- Billing endpoints:
  - `/billing/account`
  - `/billing/subscription`
  - `/billing/invoices`
  - `/billing/upgrade` (stub)

---

### 5.4 Onboarding Automation Wizard (7 steps)
**Target outcomes**: self-serve setup in <10 minutes; QR ready; team invited.

Steps:
1. Business Info
2. Create Departments
3. Add Rooms OR Tables
4. Add Menu (if restaurant enabled)
5. Configure Loyalty Rules
6. Generate QR codes automatically
7. Invite team members

Persist:
- `onboarding_completed: bool`
- `onboarding_step: int`

Add UI:
- Onboarding wizard page + progress indicator
- Auto-route new tenants to onboarding until complete

Deliverables:
- `/onboarding/status`, `/onboarding/step/{n}` endpoints (optional)
- Seed templates for hotel/restaurant departments

---

### 5.5 Guest Intelligence v2
**Target outcomes**: “wow” staff insights; churn risk & satisfaction trends; response-time intelligence.

Enhance Contact model with computed fields:
- lifetime_value
- average_response_time
- loyalty_tier_progress
- predicted_churn_risk (rule-based)
- satisfaction_trend
- service_preference_vector (tag frequency)

Create UI component:
- **GuestProfileCard**
  - alerts
  - revenue from guest
  - complaint history
  - favorite items
  - risk indicator

Deliverables:
- background jobs to compute metrics incrementally
- endpoints: `/contacts/{id}/intelligence-v2`

---

### 5.6 Revenue Analytics Engine
**Target outcomes**: operational + revenue KPIs that drive retention and upsell.

Compute per tenant:
- revenue (reservations + orders)
- upsell conversion rate
- repeat guest rate
- avg resolution time
- staff performance index
- loyalty retention %
- AI reply efficiency %

Add UI:
- advanced dashboard widgets + charts
- analytics page with drilldowns

Deliverables:
- `analytics_snapshots` collection
- Redis cached dashboard stats

---

### 5.7 GDPR / KVKK Compliance
**Target outcomes**: export/delete, consent tracking, retention policy, anonymization.

Implement:
- data export endpoint (JSON bundle)
- right-to-delete endpoint
- anonymization job
- consent tracking log
- retention policy setting (purge after X months)

Add UI:
- Compliance page (settings)

Deliverables:
- `/compliance/export`
- `/compliance/forget`
- `/compliance/retention`
- `consent_logs` collection

---

### 5.8 Performance & Scalability Layer
**Target outcomes**: predictable latency and safe growth.

Implement:
- DB indexes (tenant_id + key fields)
- background job queue (Redis-based)
- Redis caching:
  - dashboard stats
  - menu
  - room list
- WS pub/sub scaling support via Redis
- pagination everywhere (no unbounded queries)

Add:
- PerformanceMetrics endpoint

Deliverables:
- `/performance/metrics`
- index migration script

---

### 5.9 Growth & Referral Engine
**Target outcomes**: organic acquisition loop with measurable rewards.

Implement:
- referral code per tenant
- referral tracking (clicks, signups)
- rewards (extra AI credits)
- public referral landing page template

Add UI:
- Growth page:
  - referral clicks
  - converted tenants
  - earned rewards

Deliverables:
- `/growth/referral`
- `/growth/stats`
- guest/public landing route `/r/{referralCode}`

---

### 5.10 Observability & Monitoring
**Target outcomes**: diagnose issues quickly; metrics for ops + investors.

Implement:
- structured logging (JSON)
- request ID tracking
- error tracking middleware
- health check endpoint (already exists; extend)
- system status endpoint
- admin system metrics page

Bonus: Sales Mode / Demo Mode
- reset demo tenant data
- fake live activity generator
- seed auto conversations
- investor metrics page:
  - MRR (stub)
  - active tenants
  - total processed messages
  - total requests handled
  - AI replies generated

Deliverables:
- `/system/status`
- `/system/metrics`
- `/demo/reset` (protected)

---

## 3) Next Actions (immediate)
1. **Phase 5 sequencing (recommended order)**
   1) Security hardening (refresh/session/rate-limit/brute-force/audit expansion)
   2) Plan enforcement + UsageMeter + reset job
   3) Billing-ready models + Billing UI
   4) Onboarding wizard (self-serve setup)
   5) Compliance endpoints + retention policy + UI
   6) Analytics engine + caching + dashboards
   7) Guest Intelligence v2 + GuestProfileCard
   8) Growth/referral engine + public landing
   9) Observability + demo mode + investor metrics
2. Add Redis to docker-compose for:
   - rate limiting
   - schedulers
   - caching
   - ws pub/sub
3. Define acceptance criteria per workstream and create a regression test matrix.

---

## 4) Success Criteria
**Phases 1–4 (already achieved):**
- ✅ Tenant isolation and real-time workflows stable.
- ✅ Guest QR panels functional (mobile).
- ✅ Sales engine narrative (reviews + offers + reservation) demonstrated.

**Phase 5 (target):**
- Security:
  - refresh rotation + device sessions + brute-force + rate limiting + WS re-validation + strict CORS + CSRF option
  - audit log coverage expanded for all sensitive actions
  - encrypted-at-rest for configured sensitive fields
- SaaS enforcement:
  - BASIC/PRO/ENTERPRISE enforced server-side
  - upgrade modal and billing page reflect accurate usage
  - UsageMeter monthly reset works via Redis scheduler
- Billing readiness:
  - subscription + invoice lifecycle modeled, Stripe webhook placeholder exists
- Onboarding:
  - wizard completion flag + progress
- Compliance:
  - export/delete/anonymize + retention settings
- Performance:
  - indexes + caching + pagination; performance metrics endpoint
- Growth:
  - referral code, tracking, rewards, landing page, growth dashboard
- Observability:
  - JSON logs + request IDs + system status + metrics page

**Testing requirements:**
- Add tests for:
  - plan enforcement
  - rate limiting
  - GDPR export/delete
  - onboarding flow
  - billing lifecycle
  - referral logic
- Maintain **>95% coverage** on new modules and no regressions in existing modules.
