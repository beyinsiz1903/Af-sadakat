# plan.md

## 1) Objectives
- Deliver a deployable Phase-1 MVP for a tourism-first, multi-tenant SaaS: Hotel QR Requests + Restaurant QR Ordering + WebChat (real-time) + CRM Memory + Basic Loyalty + Admin.
- Prove the hardest core workflow early: **multi-tenant scoping + WebSocket real-time events + guest-facing QR flows**.
- Keep architecture AI-ready via `AIProvider` interface (mock templates TR/EN now, real LLM later).
- Ensure security baseline: tenant isolation guard, JWT auth (added after core is proven), RBAC, audit logs.

## 2) Implementation Steps (Phased)

### Phase 1 — Core POC (Isolation) (must be stable before building full UI)
**Goal:** Validate the core that can break the whole product: tenant isolation + WebSocket fanout + QR guest flows.

User stories:
1. As a guest, I can open a room QR link and submit a request without logging in.
2. As staff, I see new room requests appear in real time without refreshing.
3. As a guest, I can open a table QR link and place an order.
4. As kitchen staff, I see incoming orders in real time and can update status.
5. As the system, I guarantee no cross-tenant data leakage (tenant A never sees tenant B).

Steps:
- Web search best practices for FastAPI WebSocket scaling + Redis Pub/Sub patterns (single instance now; pub/sub ready).
- Implement minimal FastAPI POC service:
  - Tenant creation (slug), create room/table codes.
  - Guest endpoints: create `GuestRequest`, create `Order`.
  - WebSocket channels: `tenant:{tenant_id}:requests` and `tenant:{tenant_id}:orders`.
  - In-memory/Redis event bus (choose Redis if available; fallback in-memory for local dev).
- Implement minimal tenant isolation middleware: resolves `tenant_id` from slug in URL and scopes DB queries.
- Write a standalone Python test script to:
  - Create 2 tenants, submit requests/orders for both.
  - Open WS connections and assert only correct tenant receives events.
- Fix until POC is reliable (no dropped events, correct scoping, predictable payloads).

Deliverables:
- `poc_ws_multitenant.py` test script + POC endpoints + WS event contract.

---

### Phase 2 — V1 App Development (MVP UI + API, minimal auth initially)
**Goal:** Build the full working MVP around the proven POC flows; ship guest + staff UIs; keep auth minimal/optional until flow is verified.

User stories:
1. As an owner, I can create a tenant and configure rooms, departments, tables, and menu.
2. As a guest, I can submit a room request and track its status updates live.
3. As department staff, I can manage request lifecycle on a kanban board in real time.
4. As a guest, I can place a restaurant order and see confirmation.
5. As kitchen staff, I can update order status and staff/guest views update instantly.
6. As an agent, I can chat with a guest in real time via WebChat and see AI reply suggestions.

Backend (FastAPI + MongoDB + Redis optional):
- Data model collections (tenant-scoped): Tenant, User, Department, ServiceCategory, Room, GuestRequest, Table, MenuCategory, MenuItem, Order, Contact, Conversation, Message, LoyaltyAccount, LoyaltyLedger, UsageCounters, AuditLog.
- Core API modules:
  - Tenant/admin setup (rooms, departments, tables, menu, loyalty rules).
  - Hotel requests CRUD + lifecycle transitions + SLA timestamps.
  - Restaurant orders create + status transitions.
  - WebChat: conversation create, message send/receive.
  - AI mock: `AIProvider` + `MockProviderTR/EN` returning templates based on intent + DB FAQs/policies/menu/services.
- WebSocket:
  - Unified event envelope `{type, tenant_id, entity, action, payload, ts}`.
  - Broadcast on create/update for requests, orders, messages.
- Guest flows (no login):
  - `/g/{tenantSlug}/room/{roomCode}` submit request + optional loyalty join.
  - `/g/{tenantSlug}/table/{tableCode}` browse menu + order + call waiter/bill.
  - `/g/{tenantSlug}/chat` start chat session.

Frontend (React + Tailwind, dark theme):
- Shared UI kit: dark layout, Indigo primary, Emerald success, Amber warning, Rose error.
- Pages:
  - Guest: Room panel, Table menu/cart, Guest chat.
  - Staff: Requests board (dept filter), Orders board (kitchen), WebChat agent view.
  - Admin: Tenant settings, users placeholder, departments/categories, rooms, tables, menu, loyalty rules.
- Real-time:
  - WS client per tenant; optimistic UI + server reconciliation.

End-of-phase testing:
- 1 full E2E pass: create tenant → configure room/table/menu → guest submits request/order/chat → staff sees live → updates status → guest sees updates.

Deliverables:
- Working V1 app with guest + staff dashboards, real-time updates, AI mock suggestions.

---

### Phase 3 — Hardening + Auth/RBAC + CRM/Loyalty depth (production-friendly refactor)
**Goal:** Add JWT auth (access/refresh), RBAC, audit logs, stronger CRM memory + loyalty ledger; stabilize UX.

User stories:
1. As an owner, I can invite users and assign roles (Owner/Admin/Manager/Agent/DepartmentStaff).
2. As staff, I can only access permitted modules/queues based on my role and department.
3. As staff, I can view a guest summary (tags/notes/timeline) when handling requests/orders/chat.
4. As a guest, I can join loyalty with phone/email (OTP stub) and earn points automatically.
5. As an owner, I can set plan limits and see usage counters update.

Steps:
- Implement JWT auth + refresh flow; protect staff/admin routes.
- RBAC middleware + per-route permission map.
- Tenant isolation guard enforced for all authenticated + guest endpoints.
- CRM Memory:
  - Contact matching by phone/email; attach requests/orders/messages to contact timeline.
  - Notes/tags/consent flags.
- Loyalty:
  - Rules per tenant; ledger entries on `DONE/SERVED` events.
  - Guest join flow (OTP stub) + staff “guest summary” card.
- Audit logs for admin actions; basic admin usage counters (users/rooms/tables/AI replies).

End-of-phase testing:
- E2E with 2 roles + 2 tenants: verify access control + no leakage + loyalty accrual + timeline linkage.

---

### Phase 4 — Phase-2 Modules (stubs first, then UI): Omnichannel Inbox + Reviews + Offers/Mock Payment
User stories:
1. As an agent, I can view a unified inbox that includes WebChat and stub channels (IG/WA).
2. As an admin, I can configure connector credentials (stored as JSON) per tenant.
3. As an agent, I can reply from the unified inbox and see messages update live.
4. As a manager, I can view review list and respond with saved templates (stub).
5. As an owner, I can create an offer and simulate payment status (mock) end-to-end.

Steps:
- Implement connector interfaces + stub data generators.
- Reviews CRUD + response templates.
- Offer objects + mock payment state machine.
- Extend AIProvider to use channel context.

## 3) Next Actions (immediate)
1. Run web search on FastAPI WebSocket patterns + Redis Pub/Sub; pick event envelope + reconnect strategy.
2. Implement Phase-1 POC endpoints + WS + tenant guard.
3. Write and run `poc_ws_multitenant.py` until it passes reliably.
4. Once stable, scaffold V1 app (backend routes + frontend pages) in one cohesive build.

## 4) Success Criteria
- POC: two-tenant WS test passes (no cross-tenant events; stable reconnect; correct payload schema).
- V1: guest can submit room request/order/chat; staff sees and updates in real time; status reflects everywhere.
- Tenant isolation: every collection is tenant-scoped; guard prevents leakage (tested with 2 tenants).
- Usability: dark theme consistent; core flows doable in <2 minutes for demo.
- Reliability: no blocking errors in core flows; basic input validation; audit logs for admin changes by Phase 3.
