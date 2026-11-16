# System Architecture & Technical Specifications

This document outlines the architectural blueprints, database schema, security mechanisms, role-based access control (RBAC), and technical standards of the OrthoBite platform.

---

## 1. High-Level System Architecture

OrthoBite operates as a decoupled, multi-tier clinical system:

```
[ Client Browser (Vue 3 + Pinia + Tailwind v4) ]
                   │
                   │ HTTPS REST / WSS WebSocket
                   ▼
       [ FastAPI Application Layer ]
       ├── Starlette CORS & SlowAPI Middleware
       ├── JWT & RBAC Dependencies
       └── Domain Controllers
             ├── Auth & Users
             ├── Doctors & Calendar Generator
             ├── Appointments & Conflict Engine
             ├── Treatment Records & Zero-Drift Ledger
             ├── WebSocket Chat Hub
             └── Admin Governance & Audit Logging
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
[ SQLite / PostgreSQL ]   [ External Services ]
(SQLAlchemy 2.0 ORM)      ├── Brevo REST API (v3)
                          └── Local File Storage (/uploads)
```

---

## 2. Role-Based Access Control (RBAC)

The system enforces strict principle-of-least-privilege access control across five distinct user roles:

| Role | Description | Accessible Modules |
|---|---|---|
| `patient` | Individual receiving orthodontic care | Patient Portal (`/portal`), Doctor Discovery, Appointment Booking, My Appointments, Treatment Booklet & Ledger, Patient Chat Room |
| `doctor` / `orthodontist` | Licensed dental/orthodontic practitioner | Clinic Workspace (`/clinic`), Schedule Manager, Patient Record Editor, Tooth Matrix Charting, Clinical Chat |
| `secretary` | Clinical receptionist / front desk staff | Clinic Workspace (`/clinic`), Patient Check-In, Appointment Booking on behalf of patients, Status Updates, Payment Receipts |
| `admin` | System administrator / clinic director | Full System Access, Financial Analytics (`/admin/analytics`), Security Audit Trail (`/admin/audit`), User Management |

### Route Guard Validation Flow
1. **Unauthenticated Access**: Requests to protected routes redirect to `/login` with redirect intent stored.
2. **Authenticated Access**: JWT tokens decoded; expiry checked. If token is invalid or expired, session is cleared and user is redirected to `/login`.
3. **Role Enforcement**: If a user attempts to access a path outside their assigned role (`meta.roles`), the router cancels navigation and redirects to their role's default dashboard (`/portal`, `/clinic/appointments`, or `/admin/analytics`).

---

## 3. Database Models & Schema Design

All tables are defined in SQLAlchemy 2.0 models and auto-created via `Base.metadata.create_all()` on server launch.

### 3.1 Users & Authentication (`models/users.py`)
- `id` (Integer, Primary Key)
- `email` (String, Unique, Indexed)
- `username` (String, Unique, Indexed)
- `hashed_password` (String)
- `full_name` (String)
- `phone` (String, Nullable)
- `role` (Enum: `patient`, `doctor`, `orthodontist`, `secretary`, `admin`)
- `is_active` (Boolean, Default: True)
- `created_at` / `updated_at` (DateTime)

### 3.2 Doctor Profiles & Availability (`models/doctor.py`)
- **DoctorProfile**:
  - `id` (Integer, Primary Key)
  - `user_id` (Integer, Foreign Key to `users.id`)
  - `specialty` (String, e.g. "Orthodontics", "Pediatric Dentistry")
  - `bio` (Text, Nullable)
  - `photo_url` (String, Nullable)
  - `years_of_experience` (Integer)
  - `education` (String, Nullable)
  - `consultation_fee` (Decimal, 2 decimal places)
  - `is_accepting_patients` (Boolean)
- **AvailabilityRule**:
  - `id` (Integer, Primary Key)
  - `doctor_id` (Integer, Foreign Key to `doctor_profiles.id`)
  - `day_of_week` (Integer: 0=Monday through 6=Sunday)
  - `start_time` (Time, e.g. 09:00:00)
  - `end_time` (Time, e.g. 17:00:00)
  - `slot_duration_minutes` (Integer, default 30)
  - `is_active` (Boolean)
- **TimeOff**:
  - `id` (Integer, Primary Key)
  - `doctor_id` (Integer, Foreign Key to `doctor_profiles.id`)
  - `start_datetime` (DateTime)
  - `end_datetime` (DateTime)
  - `reason` (String, Nullable)

### 3.3 Appointments & Conflict Prevention (`models/appointment.py`)
- `id` (Integer, Primary Key)
- `patient_id` (Integer, Foreign Key to `users.id`)
- `doctor_id` (Integer, Foreign Key to `doctor_profiles.id`)
- `start_time` (DateTime, Indexed)
- `end_time` (DateTime, Indexed)
- `status` (Enum: `pending`, `confirmed`, `completed`, `cancelled`, `no_show`)
- `reason_for_visit` (String)
- `notes` (Text, Nullable)
- `cancellation_reason` (String, Nullable)
- `created_at` / `updated_at` (DateTime)

**Atomic Conflict Guarding**:
The appointment engine checks:
1. `start_time < end_time` chronological validity.
2. Slot is not in the past relative to server clock.
3. Doctor is currently accepting patients.
4. No overlap with doctor's scheduled `TimeOff`.
5. Slot falls strictly inside active `AvailabilityRule` hours.
6. Doctor has no overlapping `pending` or `confirmed` appointment.
7. Patient has no simultaneous appointment with any doctor.

### 3.4 Treatment Records & Zero-Drift Financials (`models/record.py`)
- **TreatmentRecord**:
  - `id` (Integer, Primary Key)
  - `patient_id` (Integer, Foreign Key to `users.id`)
  - `doctor_id` (Integer, Foreign Key to `doctor_profiles.id`, Nullable)
  - `date` (Date)
  - `treatment_name` (String, e.g. "Archwire Adjustment", "Bracket Replacement")
  - `tooth_number` (String, Nullable e.g. "11, 21")
  - `value_of_work` (Numeric 10,2)
  - `signature_url` (String, Nullable)
  - `notes` (Text, Nullable)
  - `created_at` / `updated_at` (DateTime)
- **Payment**:
  - `id` (Integer, Primary Key)
  - `treatment_record_id` (Integer, Foreign Key to `treatment_records.id`, Nullable)
  - `patient_id` (Integer, Foreign Key to `users.id`)
  - `amount` (Numeric 10,2)
  - `payment_date` (Date)
  - `method` (Enum: `Cash`, `GCash`, `Card`)
  - `receipt_no` (String, Nullable)
  - `notes` (Text, Nullable)
  - `created_at` (DateTime)

**Zero-Drift Financial Formula**:
For any patient:
$$\text{Total Value of Work} = \sum \text{TreatmentRecord.value\_of\_work}$$
$$\text{Total Paid} = \sum \text{Payment.amount}$$
$$\text{Balance Due} = \text{Total Value of Work} - \text{Total Paid}$$
Each treatment record also tracks its dedicated balance:
$$\text{Record Balance} = \text{value\_of\_work} - \sum \text{Payment.amount}_{\text{record\_id}}$$
All calculations are performed using high-precision `Decimal` objects to prevent floating-point rounding drift.

### 3.5 Live Chat Messages (`models/chat.py`)
- `id` (Integer, Primary Key)
- `room_id` (String, Indexed)
- `sender_id` (Integer, Foreign Key to `users.id`)
- `content` (Text)
- `created_at` (DateTime, Indexed)

### 3.6 Audit Trail & Governance (`models/audit.py`)
- `id` (Integer, Primary Key)
- `actor_id` (Integer, Foreign Key to `users.id`, Nullable)
- `action` (String, e.g. `CREATE_APPOINTMENT`, `CANCEL_APPOINTMENT`, `ADD_TREATMENT_RECORD`, `RECORD_PAYMENT`)
- `target_type` (String, e.g. `appointment`, `treatment_record`, `payment`, `user`)
- `target_id` (Integer, Nullable)
- `details` (JSON / Text, Nullable)
- `ip_address` (String, Nullable)
- `created_at` (DateTime, Indexed)

---

## 4. Security & Hardening

### 4.1 Pillow Byte-Level Image Inspection
To prevent malicious files with falsified MIME headers (e.g. executable scripts masquerading as PNG images), the record controller inspects file bytes via Pillow:
```python
from PIL import Image
import io

image_bytes = file.file.read()
img = Image.open(io.BytesIO(image_bytes))
img.verify()
```
Files failing byte verification are rejected immediately with `400 Bad Request`.

### 4.2 Brevo Transactional Email Engine
The `services/brevo.py` module integrates Brevo v3 REST API to dispatch:
- Account registration confirmations.
- Appointment booking confirmations.
- Appointment status transition updates (Confirmed, Cancelled).
- **Test Mode**: If `BREVO_MOCK_MODE=True` or the API key begins with `test` or `mock`, HTTP calls are safely bypassed and logged to prevent authentication failure exceptions during automated testing.

### 4.3 Rate Limiting
Configured using SlowAPI with memory / Redis backend:
- Auth endpoints: 5 attempts/minute.
- Booking endpoints: 20 requests/minute.
- General REST reads: 100 requests/minute.

