# plan.md (UPDATED)

## 1) Objectives
- **Ship a production-ready, sellable v1** of an **AI-powered Guest Operating System for Hospitality** (Hotels + Restaurants) on **FARM stack (FastAPI + React + MongoDB)**.
- Keep the platform:
  - **Multi-tenant, tenant-safe by design** (no cross-tenant leakage)
  - **Real-time** (WebSocket updates for requests/orders/inbox)
  - **AI-ready** (mock AI provider now, pluggable real LLM later)
  - **Revenue-ready** (Phase 4 Sales Engine: connectors stubs + reviews + offers + mock payments)
- Upgrade from **Demo-ready** → **Production-ready** by completing:
  - Security & enterprise hardening (Auth/RBAC/Rate-limit/Audit)
  - Tenant isolation audit + centralized enforcement
  - Data protection (KVKK/GDPR)
  - CRM Guest Intelligence (“wow” differentiation)
  - Loyalty automation (revenue engine)

**Current Status**
- ✅ **Phase 1 Complete** (Core POC): 44/44 tests passed.
- ✅ **Phase 2 Complete** (V1 App): Testing agent reports **98% overall** (backend 100%, frontend 95% with minor cosmetic issues).
- ⏭️ **Phase 3 Next**: **Security + Enterprise Hardening + CRM Intelligence + Loyalty Automation + Data Protection**.
- ⏭️ **Phase 4 After Phase 3**: **Sales Engine** (Omnichannel connector stubs + Reviews module + Offers/Mock Payments + enhanced dashboard).

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

Steps (done):
- Implemented tenant creation + tenant-scoped collections.
- Implemented guest endpoints for **GuestRequest** and **Order**.
- Implemented FastAPI WebSocket tenant channel `tenant:{tenant_id}` and broadcast events.
- Wrote and executed `poc_ws_multitenant.py`.

Deliverables (done):
- ✅ POC endpoints + WS contract
- ✅ `poc_ws_multitenant.py` with **44/44 passing**

---

### Phase 2 — V1 App Development (MVP UI + API) (**COMPLETE**)
**Goal:** Build the full working MVP around proven POC flows; ship guest + staff UIs; provide investor/customer demo readiness.

User stories (implemented and tested):
1. Owner/admin can configure rooms, departments, tables, menu, loyalty rules.
2. Guest can submit a room request and track status.
3. Department staff can manage request lifecycle on kanban board.
4. Guest can browse menu and place order via QR.
5. Kitchen/staff can update order status; views update live.
6. Agent can chat with guest and use AI reply suggestions.

Backend (done):
- FastAPI + MongoDB tenant-scoped models and APIs
- JWT auth (login/register/me)
- Admin APIs: rooms, tables, menu categories/items, departments, users
- Operational APIs: requests lifecycle + SLA timestamps, orders lifecycle
- WebChat: conversation + messages
- AI mock reply API: template-based intent detection TR/EN
- Loyalty: guest join (OTP stub), accounts, ledger
- Dashboard stats endpoint
- Seed endpoint for demo tenant `grand-hotel`

Frontend (done, dark theme):
- Dark professional Intercom/Zendesk-like UI with Indigo/Emerald/Amber/Rose semantics
- Implemented pages:
  - Login/Register
  - Dashboard KPIs
  - Requests Kanban
  - Orders board
  - Rooms management (QR links)
  - Tables management
  - Menu management
  - Contacts (search + timeline)
  - Settings (features/users/departments/loyalty)
  - Inbox (WebChat + AI suggestions)
  - Guest Room Panel (no-auth)
  - Guest Table Panel (no-auth + cart)
  - Guest Chat
- WebSocket client for real-time updates

End-of-phase testing (done):
- Testing agent: **98% overall**
  - Backend: **100%**
  - Frontend: **95%** (minor cosmetic issues)
  - Guest panels: **100%**

Deliverables (done):
- ✅ Working V1 app ready for demos
- ✅ Seeded demo tenant + credentials

Known minor issues (accepted, low priority):
- Occasional WS connection warning on initial load (cosmetic)
- Occasional DOM attachment issue during nav clicks in automation (non-blocking)

---

### Phase 3 — Security + Enterprise Hardening + CRM Intelligence + Loyalty Automation (**NEXT**) 
**Goal:** Move from demo-ready to **production-ready** by implementing security, compliance, and the differentiation layer (Guest Intelligence + loyalty automation).

#### 3A) Auth & RBAC Hardening (Enterprise baseline)
**Scope**
- Add auth features:
  - Refresh token rotation
  - Device session tracking (session list + revoke)
  - IP logging and last-login metadata
  - Rate limiting **per tenant**
  - Brute-force protection (login attempt throttling / lockout)
  - Optional 2FA toggle (Pro plan) (TOTP stub acceptable now)
  - Role matrix audit log events

**RBAC expansion**
- Roles: **Owner, Admin, Manager, Agent, DepartmentStaff, KitchenStaff, FrontDesk**
- Permissions:
  - Permission matrix per module/route (API + UI)
  - Department scoping for DepartmentStaff/FrontDesk/KitchenStaff
  - Role-based UI filtering (nav items + route guards)

Deliverables
- `auth_refresh` flow, `sessions` collection
- Middleware/Dependency: `require_role()` / `require_permission()`
- Admin UI: Sessions page (basic) + 2FA toggle (Pro)

#### 3B) Tenant Isolation Audit + Centralized Enforcement
**Goal:** guarantee: **Every DB query includes tenant_id** (or is explicitly global/system).

Security tests to add:
- Cross-tenant WebSocket injection attempts
- IDOR risks (guessing entity IDs)
- Slug manipulation
- Feature flag bypass

Implementation changes:
- Centralize tenant context resolution and enforce tenant scoping:
  - Tenant context dependency that yields `{tenant_id, slug, features}`
  - Repository/data-access helpers that *require* `tenant_id`
  - Defensive checks on update/delete by `{id, tenant_id}` always

Deliverables
- Automated isolation test suite (pytest) covering the above
- A lintable pattern (or helper functions) to prevent missing tenant filters

#### 3C) Data Protection (KVKK/GDPR readiness)
**Additions**
- Consent logging (when/where/how consent was collected)
- PII masking in logs (never log phone/email in plaintext in app logs)
- Data export endpoint (Right of access): export guest-related data by contact
- Data delete endpoint (Right to be forgotten): delete/anonymize contact + linked data as per policy
- Encrypted loyalty ledger (at-rest encryption placeholder):
  - Field-level encryption approach documented + implemented as a wrapper for sensitive values

Deliverables
- `/tenants/{slug}/privacy/export` (admin) and/or `/contacts/{id}/export`
- `/tenants/{slug}/privacy/forget` (admin) and/or `/contacts/{id}/forget`
- Audit trail entries for exports/deletions

#### 3D) CRM Guest Intelligence Layer (Differentiator)
**Data model changes (Contact)**
Add computed/derived fields:
- `visit_count`
- `avg_rating`
- `total_spend`
- `complaint_ratio`
- `last_sentiment`
- `preferred_language`
- `preferred_room_type`
- `favorite_menu_items` (top-N)

Computation approach
- Incremental updates on events (request done, order served, message received)
- Backfill job for historical recomputation
- Simple sentiment: rule-based classifier for now (Phase 3), pluggable LLM later

UI/UX
- Staff “Guest Summary Card”:
  - Alerts like: “⚠ Previously complained about AC issue in R203”
  - Key stats: spend, visits, last rating, last complaint
  - Suggested actions (templates)

Deliverables
- Contact intelligence update pipeline
- Guest Summary Card in:
  - Requests detail
  - Orders detail
  - Inbox conversation view

#### 3E) Loyalty Automation (Revenue Engine)
Enhancements
- Auto-earn points on:
  - Completed request
  - Served/completed order
  - (Reservation created — if Phase 4 reservation exists, add hook)
- Tier system:
  - Bronze → Silver → Gold → Platinum
  - Tier auto-upgrade rules
  - Tier benefits configuration per tenant
- Gamification UI:
  - Progress bar: “250 points left to Gold”

Deliverables
- Tier rules + benefits config UI
- Idempotent points awarding (no duplicate ledger entries)
- Guest view badge (optional) and staff view summary

**End-of-phase testing (Phase 3)**
- E2E: multi-tenant + multi-role test matrix
- Security regression suite:
  - Tenant isolation checks
  - Auth session revocation
  - Rate-limit behavior
  - Export/delete flows

---

### Phase 4 — Sales Engine (Connectors Stubs + Reviews + Offers/Mock Payments) (**AFTER PHASE 3**) 
**Goal:** convert platform from operational tool → **revenue engine** and investor-ready product story.

#### 4A) Connector Framework + Stubs
- Implement connector interfaces + fake polling jobs:
  - `WhatsAppConnectorStub`
  - `InstagramDMConnectorStub`
  - `GoogleReviewsConnectorStub`
  - `TripAdvisorConnectorStub`
- Add `ConnectorCredential` model:
  - Per tenant
  - Encrypted JSON placeholder
- Admin UI:
  - “Connect WhatsApp (Coming Soon)”
  - “Connect Instagram (Coming Soon)”
  - “Connect Google Reviews (Coming Soon)”

Deliverables
- Polling cron/async job stub that generates deterministic fake data per tenant
- Unified inbox shows stub messages with channel labels

#### 4B) Reviews Module
Backend
- `Review` model + `ReviewReply`
- Sentiment badge (rule-based initially)
- AI reply suggestions for reviews
- Manual reply publish (stub)

Frontend
- Reviews list view with filters + sentiment badges
- Review detail page with:
  - AI suggested reply
  - Templates
  - “Publish reply” (stub)

Deliverables
- Reviews module integrated into left nav (role gated)

#### 4C) Offers + Mock Payments + Reservations
Backend
- `Offer` model (dates, room type, price, inclusions)
- `PaymentLink` model + `StripeStubProvider`
- Mock payment success endpoint
- `Reservation` creation on payment success

Frontend
- Offer builder UI (from Inbox and/or Offers page)
- Generate payment link UI
- Simulate payment UI
- Reservations dashboard

End-to-end flow
- Create Offer → Generate Payment Link → Simulate Payment → Create Reservation

#### 4D) Enhanced Dashboard (Sales/Revenue)
- Revenue charts (mock data from orders + payments)
- Review sentiment summary
- Loyalty program KPIs:
  - enrolled guests
  - points issued
  - tier distribution

**End-of-phase testing (Phase 4)**
- E2E: connector stubs feed inbox/reviews
- E2E: offers → payment → reservation

---

## 3) Next Actions (immediate)
1. Confirm Phase 3 implementation order (recommended):
   1) Tenant isolation centralization + security tests
   2) Refresh tokens + sessions + rate limiting + brute-force
   3) Expanded RBAC (roles + permission matrix + UI gating)
   4) Data protection endpoints + consent logging
   5) CRM intelligence layer + guest summary cards
   6) Loyalty automation + tiers + gamification
2. Define a minimal “Production Ready” acceptance checklist (security + compliance + isolation tests green).
3. After Phase 3 is stable, start Phase 4 Sales Engine.

---

## 4) Success Criteria
- Phase 1: ✅ Two-tenant WS isolation test passes (44/44).
- Phase 2: ✅ V1 app demo-ready; testing agent reports **98%** overall; guest QR panels functional.
- Phase 3 (production-ready target):
  - Refresh token rotation + session management + rate-limits + brute-force protection
  - RBAC roles expanded and enforced in API + UI
  - Centralized tenant isolation enforcement; isolation test suite green
  - KVKK/GDPR endpoints (export/forget) + consent logging + PII-masked logs
  - CRM Guest Intelligence fields computed and visible as staff insights
  - Loyalty tiers + gamification; idempotent ledger awarding
- Phase 4 (sellable revenue engine target):
  - Connector stubs visible in admin + inbox with polling job stubs
  - Reviews module live with sentiment + AI suggestions
  - Offers → mock payment → reservation flow demonstrated end-to-end
  - Dashboard includes sales/revenue and customer sentiment summaries
