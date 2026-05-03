# Omni Inbox Hub

A comprehensive multi-tenant SaaS platform for the hospitality and service industries (hotels, restaurants, clinics). Provides a centralized dashboard for managing guest requests, room service, reservations, loyalty programs, and AI-driven guest communication.

## Architecture

- **Frontend**: React 19 + Tailwind CSS + Shadcn UI, built with CRACO (Create React App), runs on port 5000
- **Backend**: FastAPI (Python) with async MongoDB (motor), runs on port 8000
- **Database**: MongoDB 7.0, runs locally on port 27017
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
│   ├── server.py      # Main entry point (~1310 lines, websocket + 33 legacy routes; rooms/orders/contacts/analytics/demo-seed/guest-resolve extracted)
│   ├── routers/       # Modular API routers (auth, tenants, billing, system, hotel, restaurant, inbox, etc.)
│   ├── services/      # Business logic + external provider integrations
│   ├── connectors/    # Third-party platform connectors
│   └── core/          # Config, middleware, tenant guards
├── data/db/           # MongoDB data directory
├── start.sh           # Startup script (MongoDB + backend + frontend)
└── tests/             # Pytest test suites
```

## Environment Variables

- `MONGO_URL`: MongoDB connection URL (default: `mongodb://localhost:27017`)
- `DB_NAME`: MongoDB database name (default: `omni_inbox_hub`)
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
