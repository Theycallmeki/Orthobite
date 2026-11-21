# XXX Orthodontics Management Platform 

XXX is a enterprise-grade clinical orthodontics management platform engineered with a **FastAPI** backend and a modern **Vue 3** frontend. The system provides real-time appointment scheduling, doctor availability rule generation, electronic treatment records with interactive 32-tooth dental charting, patient signature capture, zero-drift financial installment ledgers, and secure role-based access control.

---

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Technology Stack](#technology-stack)
- [Project Directory Structure](#project-directory-structure)
- [Quick Start Guide](#quick-start-guide)
- [Implementation Progress](#implementation-progress)
- [Documentation Index](#documentation-index)

---

## Architecture Overview

OrthoBite utilizes a decoupled client-server architecture:
- **Backend**: Python 3.12, FastAPI, SQLAlchemy ORM, Pydantic v2, SQLite / PostgreSQL.
  - Strict role-based access control (`patient`, `doctor`, `orthodontist`, `secretary`, `admin`).
  - SlowAPI rate limiting (IP & token based).
  - Pillow byte-level file inspection preventing MIME spoofing on image/signature uploads.
  - Brevo transactional email dispatch with mock testing mode (`BREVO_MOCK_MODE`).
  - WebSocket hub for live clinical chat.
- **Frontend**: Vue 3 Composition API, Vite 8, TypeScript 5, Tailwind CSS v4, Pinia 3 state management, Vue Router 5, and Lucide icons.
  - Fully responsive clinical interface with role-aware application shell.
  - Reactive JWT session persistence with automatic header injection.
  - Zero-drift financial reconciliation for multi-payment treatment installment ledgers.

---

## Technology Stack

| Layer | Technologies |
|---|---|
| **Backend Framework** | FastAPI, Starlette, Uvicorn (ASGI) |
| **Database & ORM** | SQLite (dev) / PostgreSQL (prod), SQLAlchemy 2.0 |
| **Data Validation** | Pydantic v2 |
| **Authentication** | JWT (python-jose), Passlib (Argon2 / BCrypt) |
| **File Verification** | Pillow (PIL `Image.verify()` byte inspection) |
| **Email Service** | Brevo REST API (v3) + Testing Mock Engine |
| **Frontend Framework** | Vue 3 (Composition API `<script setup lang="ts">`) |
| **Build Tooling** | Vite 8, TypeScript 5, Vue TSC |
| **State Management** | Pinia 3 (6 modular domain stores) |
| **Routing** | Vue Router 5 (role guards & JWT validation) |
| **Styling** | Tailwind CSS v4 (`@tailwindcss/vite`), Lucide Icons |

---

## Project Directory Structure

```
orthobite/
├── backend/
│   ├── config/             # Database session, CORS, settings, logging
│   ├── controllers/        # Domain business logic (auth, appointment, record, doctor, admin)
│   ├── models/             # SQLAlchemy ORM models (users, doctor, appointment, record, audit)
│   ├── routes/             # FastAPI APIRouters (auth, doctors, appointments, records, chat, admin)
│   ├── schemas/            # Pydantic v2 input/output DTOs
│   ├── services/           # Brevo transactional email & WebSocket connection manager
│   ├── tests/              # Pytest test suite (unit and end-to-end integration tests)
│   ├── dependencies.py     # JWT extraction, user injection, RBAC role dependencies
│   ├── middleware.py       # CORS & SlowAPI rate limiting middleware
│   └── main.py             # FastAPI entry point & table auto-creation
├── frontend/
│   ├── src/
│   │   ├── api/            # Axios API clients for all backend endpoints
│   │   ├── assets/         # Tailwind CSS v4 theme and styles
│   │   ├── components/     # Reusable UI components (ToothMatrix, SignaturePad, etc.)
│   │   ├── layouts/        # AppLayout (navbar/sidebar) and AuthLayout
│   │   ├── router/         # Vue Router configuration and navigation guards
│   │   ├── stores/         # Pinia stores (auth, doctor, appointment, record, chat, admin)
│   │   ├── views/          # Route views:
│   │   │   ├── auth/       # LoginView, RegisterView
│   │   │   ├── patient/    # DoctorCarouselView, BookAppointmentView, MyAppointmentsView, TreatmentBookletView
│   │   │   ├── clinic/     # AppointmentsScheduleView, PatientRecordEditorView (Phase 5)
│   │   │   ├── chat/       # ChatView (Phase 5)
│   │   │   └── admin/      # AnalyticsDashboardView, AuditTrailView (Phase 6)
│   │   ├── App.vue         # Root application mount
│   │   └── main.ts         # App initialization & plugin mounting
│   ├── package.json        # Dependencies & scripts
│   └── vite.config.ts      # Vite 8 configuration
└── docs/                   # Detailed system documentation
    ├── SYSTEM_ARCHITECTURE.md
    ├── REMAINING_MODULES_SPECIFICATION.md
    └── API_REFERENCE.md
```

---

## Quick Start Guide

### Prerequisites
- Python 3.10+ (Python 3.12 recommended)
- Node.js 20+ and npm 10+

### Backend Setup
1. Clone the repository and navigate to the root directory:
   ```bash
   cd orthobite
   ```
2. Create and activate a Python virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # Linux/macOS:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```
   The backend uses SQLite by default. To use PostgreSQL, set `DATABASE_URL` in an untracked `backend/.env` file or in the deployment environment. When starting the server from `backend/`, it creates missing tables in the configured database.
4. Run the FastAPI development server:
   ```bash
   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```
   Interactive Swagger API documentation will be available at `http://localhost:8000/docs`.

### Frontend Setup
1. From the repository root, navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install dependencies:
   ```bash
   npm install
   ```
3. Run the Vite development server:
   ```bash
   npm run dev
   ```
   The application will mount at `http://localhost:5173`.
4. Type-check and production build:
   ```bash
   npm run type-check
   npm run build-only
   ```

---

## Implementation Progress

| Phase | Description | Status |
|---|---|---|
| **Phase 1** | Backend Hardening, Pillow verification, Brevo mock mode, E2E test suite (27/27 passed) | **Completed** |
| **Phase 2** | Pinia State Stores (`auth`, `doctor`, `appointment`, `record`, `chat`, `admin`) | **Completed** |
| **Phase 3** | Frontend Routing, Tailwind CSS v4, Layouts (`AuthLayout`, `AppLayout`), Role Guards | **Completed** |
| **Phase 4** | Patient Portal: Login, Register, Doctor Discovery, Booking Calendar, My Appointments, Treatment Booklet | **Completed** |
| **Phase 5** | Clinical Tools: Tooth Matrix SVG, Signature Pad Canvas, Live Chat, Clinic Schedule, Record Editor | *Next in line* |
| **Phase 6** | Admin Dashboard: Revenue & KPI Analytics, Security Audit Trail Log Inspector | *Pending* |

---

## Documentation Index

- [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) - Comprehensive backend & frontend system design, security, RBAC, and data schemas.
- [docs/REMAINING_MODULES_SPECIFICATION.md](docs/REMAINING_MODULES_SPECIFICATION.md) - Detailed technical specification and implementation requirements for all remaining Phase 5 and Phase 6 modules.
- [docs/API_REFERENCE.md](docs/API_REFERENCE.md) - Complete REST API and WebSocket reference index.

