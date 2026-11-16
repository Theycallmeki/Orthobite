# API Reference & Data Contracts

This document provides a comprehensive index of all RESTful HTTP endpoints and WebSocket protocols exposed by the OrthoBite FastAPI backend.

---

## 1. Authentication & Users (`/auth`)

| Method | Endpoint | Access | Summary |
|---|---|---|---|
| `POST` | `/auth/register` | Public | Register new patient account with Brevo welcome email |
| `POST` | `/auth/login` | Public | Authenticate user credentials, returns JWT bearer token |
| `GET` | `/auth/me` | Authenticated | Retrieve authenticated user profile and assigned role |
| `POST` | `/auth/refresh` | Authenticated | Refresh JWT access token before expiration |

---

## 2. Doctors & Calendar Availability (`/doctors`)

| Method | Endpoint | Access | Summary |
|---|---|---|---|
| `GET` | `/doctors/` | Public | List all active practitioners for doctor discovery carousel |
| `GET` | `/doctors/{doctor_id}` | Public | Retrieve public doctor profile, specialty, bio, and fee |
| `GET` | `/doctors/{doctor_id}/availability` | Public | Compute 30-min available slots for month `YYYY-MM` |
| `GET` | `/doctors/me/profile` | Doctor | Retrieve logged-in doctor's personal profile |
| `PATCH` | `/doctors/me/profile` | Doctor | Update specialty, bio, photo URL, fee, or patient acceptance |
| `GET` | `/doctors/me/availability` | Doctor | Retrieve recurring weekly availability rules |
| `PUT` | `/doctors/me/availability` | Doctor | Replace weekly availability rules (0=Monday to 6=Sunday) |
| `GET` | `/doctors/me/time-off` | Doctor | List scheduled doctor vacations and unavailable blocks |
| `POST` | `/doctors/me/time-off` | Doctor | Schedule new time-off block |

---

## 3. Appointments & Scheduling (`/appointments`)

| Method | Endpoint | Access | Summary |
|---|---|---|---|
| `POST` | `/appointments/` | Patient / Staff | Book new appointment with conflict detection & email alert |
| `POST` | `/appointments/admin` | Staff / Admin | Book appointment on behalf of any patient |
| `GET` | `/appointments/` | Authenticated | List appointments filtered by status, doctor, date range |
| `GET` | `/appointments/{id}` | Authenticated | Get detailed appointment metadata |
| `PATCH` | `/appointments/{id}` | Staff | Reschedule or update visit notes |
| `PATCH` | `/appointments/{id}/status` | Staff / Doctor | Transition status (`confirmed`, `completed`, `no_show`) |
| `POST` | `/appointments/{id}/cancel` | Patient / Staff | Cancel appointment with mandatory cancellation reason |
| `GET` | `/appointments/schedule/daily` | Staff / Doctor | Daily schedule matrix with 30-min slot allocations |

---

## 4. Treatment Records & Financial Ledger (`/records`)

| Method | Endpoint | Access | Summary |
|---|---|---|---|
| `GET` | `/records/tooth-chart/template` | Authenticated | Rectangular 32-tooth layout geometry and arch metadata |
| `POST` | `/records/signatures/upload` | Staff | Upload multipart patient signature PNG with Pillow byte verification |
| `POST` | `/records/signatures/base64` | Staff | Save Base64 canvas signature with Pillow byte verification |
| `POST` | `/records/` | Staff | Add new treatment record entry (procedure, teeth, value of work) |
| `GET` | `/records/{id}` | Patient / Staff | Get treatment record, notes, signature URL, and payment history |
| `PATCH` | `/records/{id}` | Staff | Update treatment entry notes or procedure details |
| `DELETE` | `/records/{id}` | Staff | Delete treatment entry and trigger audit logging |
| `POST` | `/records/{id}/payments` | Staff | Record installment payment applied to a specific record |
| `POST` | `/records/payments` | Staff | Record general unallocated installment payment |
| `GET` | `/records/payments/{id}` | Patient / Staff | Retrieve payment receipt details |
| `GET` | `/records/patient/{patient_id}/ledger` | Patient / Staff | Compute zero-drift patient financial ledger summary |

---

## 5. Live WebSocket Chat (`/ws/chat`)

| Protocol | Endpoint | Access | Summary |
|---|---|---|---|
| `WSS` | `/ws/chat/{room_id}?token={jwt}` | Authenticated | Persistent bi-directional WebSocket messaging hub |
| `GET` | `/chat/rooms` | Authenticated | List accessible chat channels and direct conversations |
| `GET` | `/chat/rooms/{room_id}/messages` | Authenticated | Retrieve paginated historical room messages |

### WebSocket Client Payload Schema
```json
{
  "type": "message",
  "content": "Doctor, I would like to reschedule my wire tightening."
}
```

### WebSocket Server Broadcast Schema
```json
{
  "type": "message",
  "room_id": "room_12",
  "sender_id": 5,
  "sender_name": "Dr. Sarah Jenkins",
  "sender_role": "orthodontist",
  "content": "Sure, let us check available slots for this Thursday.",
  "created_at": "2026-11-15T15:45:00Z"
}
```

---

## 6. Admin Analytics & Security Audit (`/admin`)

| Method | Endpoint | Access | Summary |
|---|---|---|---|
| `GET` | `/admin/analytics/summary` | Admin | Clinical KPIs, revenue totals, and appointment counts |
| `GET` | `/admin/analytics/revenue` | Admin | Monthly billing vs collections zero-drift time series |
| `GET` | `/admin/audit/logs` | Admin | Query paginated audit logs with actor, action, and date filters |
| `GET` | `/admin/audit/logs/{id}` | Admin | Get full structured change diff payload for a specific event |

---

## 7. Patient Records & Lookup (`/patients`)

| Method | Endpoint | Access | Summary |
|---|---|---|---|
| `GET` | `/patients/search` | Staff / Admin | Quick search patients by name, email, or telephone |
| `GET` | `/patients/{id}` | Staff / Admin | Get full patient profile and contact information |

