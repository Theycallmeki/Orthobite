# Remaining Modules Specification & Technical Implementation Guide

This specification details the technical requirements, architecture, API contracts, component interfaces, state bindings, and target git commits for the remaining modules of the OrthoBite platform.

---

## 1. Summary of Remaining Modules

| Phase | Module / Component | Target File | Primary Role |
|---|---|---|---|
| **Phase 5 (Commit 1)** | `ToothMatrix.vue` | `src/components/ToothMatrix.vue` | Interactive 32-tooth adult dental chart & surface selector |
| **Phase 5 (Commit 2)** | `SignaturePad.vue` | `src/components/SignaturePad.vue` | HTML5 Canvas electronic signature capture |
| **Phase 5 (Commit 3)** | `ChatView.vue` | `src/views/chat/ChatView.vue` | Live WebSocket chat with reconnection & typing indicator |
| **Phase 5 (Commit 4)** | `AppointmentsScheduleView.vue` | `src/views/clinic/AppointmentsScheduleView.vue` | Clinic daily schedule & appointment status manager |
| **Phase 5 (Commit 5)** | `PatientRecordEditorView.vue` | `src/views/clinic/PatientRecordEditorView.vue` | Treatment record sheet editor with matrix & signature |
| **Phase 6 (Commit 1)** | `AnalyticsDashboardView.vue` | `src/views/admin/AnalyticsDashboardView.vue` | Financial KPI cards & clinical distribution analytics |
| **Phase 6 (Commit 2)** | `AuditTrailView.vue` | `src/views/admin/AuditTrailView.vue` | HIPAA / clinical compliance audit log table & inspector |

---

## 2. Phase 5: Clinical Tools, Tooth Matrix & Live Chat

### Module 5.1: `ToothMatrix.vue` (Interactive 32-Tooth Chart)
- **Path**: `frontend/src/components/ToothMatrix.vue`
- **Purpose**: High-fidelity adult dental chart representing all 32 adult teeth with anatomical surface tagging.

#### Anatomical Layout
- **Maxillary Arch (Upper)**:
  - Upper Right (Quadrant 1): Teeth 18, 17, 16, 15, 14, 13, 12, 11 (Universal #1–#8)
  - Upper Left (Quadrant 2): Teeth 21, 22, 23, 24, 25, 26, 27, 28 (Universal #9–#16)
- **Mandibular Arch (Lower)**:
  - Lower Left (Quadrant 3): Teeth 38, 37, 36, 35, 34, 33, 32, 31 (Universal #17–#24)
  - Lower Right (Quadrant 4): Teeth 41, 42, 43, 44, 45, 46, 47, 48 (Universal #25–#32)

#### 5 Anatomical Surfaces per Tooth
1. **Mesial (M)**: Surface facing toward the dental midline.
2. **Distal (D)**: Surface facing away from the dental midline.
3. **Occlusal / Incisal (O/I)**: Chewing/biting surface.
4. **Facial / Buccal (F/B)**: Outer surface facing the lips/cheeks.
5. **Lingual (L)**: Inner surface facing the tongue.

#### Component Interface
```typescript
interface ToothCondition {
  toothId: number
  condition: 'healthy' | 'caries' | 'restored' | 'crown' | 'banded' | 'missing'
  surfaces?: ('M' | 'D' | 'O' | 'B' | 'L')[]
}

// Props
defineProps<{
  modelValue?: number[]                    // Currently selected tooth IDs
  conditions?: Record<number, ToothCondition> // Highlighted clinical states
  readOnly?: boolean                      // View-only vs interactive selection
  showSurfaces?: boolean                  // Whether to open surface picker on tooth click
}>()

// Emits
defineEmits<{
  (e: 'update:modelValue', value: number[]): void
  (e: 'select-tooth', toothId: number): void
  (e: 'select-surface', payload: { toothId: number; surface: string }): void
}>()
```

#### State & Backend Integration
- Consumes `useRecordStore.fetchToothTemplate()` to retrieve backend layout geometry.
- Interacts with `recordStore.toggleToothSelection(toothId)` and `recordStore.selectedTeeth`.
- **Target Git Commit**:
  ```bash
  git add frontend/src/components/ToothMatrix.vue
  git commit -m "feat: implement interactive 32-tooth matrix svg component with surface selection"
  ```

---

### Module 5.2: `SignaturePad.vue` (Canvas Electronic Signature)
- **Path**: `frontend/src/components/SignaturePad.vue`
- **Purpose**: HTML5 Canvas electronic signature capture for digital patient informed consent.

#### Technical Features
- High-resolution rendering using `window.devicePixelRatio` to prevent pixelation on Retina/HiDPI screens.
- Smooth Bezier curve stroke rendering (`context.quadraticCurveTo`) capturing pressure and velocity.
- Unified touch (`touchstart`, `touchmove`, `touchend`) and mouse (`mousedown`, `mousemove`, `mouseup`) events with canvas coordinate normalization (`getBoundingClientRect()`).
- Stroke history buffer supporting undo of individual strokes.
- Export formats:
  - Base64 Data URL (`image/png`) for direct JSON transmission.
  - Binary `Blob` for standard multipart form uploads.

#### Component Interface
```typescript
// Props
defineProps<{
  width?: number          // Default 500
  height?: number         // Default 200
  strokeColor?: string    // Default '#0f172a' (slate-900)
  lineWidth?: number      // Default 2.5
  placeholder?: string    // 'Sign here with mouse or stylus...'
}>()

// Emits
defineEmits<{
  (e: 'change', hasSignature: boolean): void
  (e: 'save', signatureBase64: string): void
  (e: 'clear'): void
}>()

// Exposed Methods (via defineExpose)
defineExpose({
  clear: () => void,
  undo: () => void,
  isEmpty: () => boolean,
  toDataURL: (type?: string) => string,
  toBlob: () => Promise<Blob | null>
})
```

#### State & Backend Integration
- Directly connects to `useRecordStore.saveSignatureBase64(dataUrl)` and `uploadSignatureFile(blob)`.
- Populates `recordStore.capturedSignatureUrl` for immediate treatment sheet embedding.
- **Target Git Commit**:
  ```bash
  git add frontend/src/components/SignaturePad.vue
  git commit -m "feat: implement html5 canvas signature pad component for patient consent"
  ```

---

### Module 5.3: `ChatView.vue` (Real-Time WebSocket Messaging)
- **Path**: `frontend/src/views/chat/ChatView.vue`
- **Route**: `/portal/chat` (patient) and `/clinic/chat` (clinical staff)
- **Purpose**: Real-time encrypted communication between patients, attending orthodontists, and front-desk receptionists.

#### Protocol & Communication Flow
- **Endpoint**: `ws://<host>:<port>/ws/chat/{room_id}?token=<jwt>`
- **Handshake**: WebSocket dependency verifies JWT payload; rejects unauthenticated sockets with 4003 policy violation.
- **Message Framing**:
  ```json
  {
    "type": "message",
    "room_id": "clinical-care-101",
    "content": "Doctor, my lower bracket feels loose after lunch.",
    "sender_id": 42,
    "sender_name": "Maria Santos",
    "sender_role": "patient",
    "created_at": "2026-11-15T15:30:00"
  }
  ```
- **Connection Resilience**:
  - Exponential backoff retry on drop ($1s, 2s, 4s, 8s, \dots, \max 30s$).
  - Heartbeat `{"type": "ping"}` sent every 25 seconds to keep intermediary proxies alive.
  - Sticky offline banner when disconnected, auto-dismissing upon reconnection.

#### Component Structure
- **Left Sidebar**: Active channels and direct doctor/patient conversations with unread counter badges.
- **Header**: Active room title, interlocutor status (Online/Offline), attending doctor specialty badge.
- **Message Feed**: Auto-scrolling transcript with chronological separation, sender avatars, role badges, and read confirmations.
- **Composer**: Text input, emoji picker, attachment button, and typing indicator broadcast.

#### State & Backend Integration
- Managed by `useChatStore`:
  - `activeRoom`, `messages`, `isConnected`, `isReconnecting`.
  - Methods: `connectWebSocket(roomId)`, `sendMessage(content)`, `fetchRoomHistory(roomId)`.
- **Target Git Commit**:
  ```bash
  git add frontend/src/views/chat/ChatView.vue frontend/src/router/index.ts
  git commit -m "feat: implement live websocket chat room with automatic reconnection and typing indicator"
  ```

---

### Module 5.4: `AppointmentsScheduleView.vue` (Clinic Schedule Manager)
- **Path**: `frontend/src/views/clinic/AppointmentsScheduleView.vue`
- **Route**: `/clinic/appointments`
- **Purpose**: Daily and weekly operational schedule dashboard for Doctors, Orthodontists, and Clinic Secretaries.

#### Key Features
- **Schedule Views**:
  - Daily Schedule View: Time-grid showing 30-min slot allocations per practitioner.
  - Weekly List View: Tabular view grouped by date with quick filtering.
- **Status Lifecycle Workflow**:
  - `pending` $\rightarrow$ `confirmed` (via "Confirm Visit" button, triggers Brevo notification).
  - `confirmed` $\rightarrow$ `completed` (via "Mark Completed" check-in action).
  - `confirmed` / `pending` $\rightarrow$ `no_show` (patient failed to attend).
  - `pending` / `confirmed` $\rightarrow$ `cancelled` (with mandatory cancellation reason dialog).
- **Administrative Booking**:
  - Modal allowing receptionists to book appointments on behalf of walk-in or telephone patients via `POST /appointments/admin`.
- **Filters**:
  - Practitioner selector (filter by specific doctor or view all).
  - Date picker (Today, Tomorrow, Pick custom date).
  - Patient search query (matches name, phone, or appointment reference).

#### State & Backend Integration
- Interacts with `useAppointmentStore`:
  - `fetchAppointments({ doctor_id, start_date, end_date, status })`.
  - `updateAppointmentStatus(id, newStatus, reason)`.
  - `bookAppointment(adminPayload)`.
- **Target Git Commit**:
  ```bash
  git add frontend/src/views/clinic/AppointmentsScheduleView.vue frontend/src/router/index.ts
  git commit -m "feat: implement clinic appointment schedule manager and status workflow view"
  ```

---

### Module 5.5: `PatientRecordEditorView.vue` (Treatment Sheet Editor)
- **Path**: `frontend/src/views/clinic/PatientRecordEditorView.vue`
- **Route**: `/clinic/records`
- **Purpose**: Comprehensive clinical record editor used by doctors during or immediately after orthodontic procedures.

#### Workflow & Integrated Components
1. **Patient Selection**: Auto-complete search bar to select patient by name, username, or email.
2. **Patient Financial Overview**: Displays patient's current ledger summary (Total Billed, Total Paid, Balance Due).
3. **Tooth Chart Integration**: Embeds `ToothMatrix.vue` allowing the clinician to click affected teeth (e.g. #11, #21) and surfaces to auto-populate the procedure's `tooth_number` field.
4. **Procedure Details**:
   - Procedure Preset Chips: "Archwire Replacement", "Bracket Rebonding", "Composite Restorative", "Prophylaxis", "Appliance Fitting".
   - Value of Work input field ($).
   - Clinical progress notes.
5. **Electronic Signature Capture**:
   - Embeds `SignaturePad.vue` allowing the patient to sign the tablet/screen confirming informed consent.
   - Saves signature to backend via `recordStore.saveSignatureBase64()` and links `signature_url`.
6. **Immediate Payment Collection**:
   - Optional inline payment collector to record initial down-payment or installment.
   - Inputs: Amount, Payment Method (`Cash`, `GCash`, `Card`), Receipt Number.
   - Updates patient ledger instantaneously with zero drift.

#### State & Backend Integration
- Interacts with `useRecordStore`:
  - `createTreatmentRecord(payload)`.
  - `addPaymentForRecord(recordId, paymentPayload)`.
  - `fetchPatientLedger(patientId)`.
- **Target Git Commit**:
  ```bash
  git add frontend/src/views/clinic/PatientRecordEditorView.vue frontend/src/router/index.ts
  git commit -m "feat: implement clinical patient record editor with tooth matrix and signature pad integration"
  ```

---

## 3. Phase 6: Admin Analytics & Governance

### Module 6.1: `AnalyticsDashboardView.vue` (Executive KPI Dashboard)
- **Path**: `frontend/src/views/admin/AnalyticsDashboardView.vue`
- **Route**: `/admin/analytics`
- **Purpose**: Real-time revenue analytics, clinic throughput metrics, and orthodontic procedure volume breakdown.

#### Metric Cards & KPI Calculations
- **Gross Clinical Billing**: Total value of all recorded treatment procedures.
- **Collected Revenue**: Actual cash, card, and digital funds collected across all payments.
- **Outstanding Patient Receivables**: Total balance due across all active patient accounts (verifying zero drift).
- **Appointment Volume & Conversion**:
  - Total scheduled appointments.
  - Completion rate ($\frac{\text{Completed}}{\text{Total}} \times 100\%$).
  - Cancellation / No-show rate ($\frac{\text{Cancelled} + \text{No-Show}}{\text{Total}} \times 100\%$).

#### Data Visualizations
- **Revenue Timeline Chart**: Monthly billing vs monthly collected payments.
- **Appointment Status Distribution**: Visual breakdown of `pending`, `confirmed`, `completed`, and `cancelled`.
- **Top Orthodontic Procedures**: Bar chart ranking procedures by revenue and frequency.

#### State & Backend Integration
- Interacts with `useAdminStore`:
  - `fetchAnalyticsSummary()`.
  - `fetchRevenueStats()`.
- **Target Git Commit**:
  ```bash
  git add frontend/src/views/admin/AnalyticsDashboardView.vue frontend/src/router/index.ts
  git commit -m "feat: implement admin clinical analytics and revenue dashboard view"
  ```

---

### Module 6.2: `AuditTrailView.vue` (Compliance & Security Audit Log)
- **Path**: `frontend/src/views/admin/AuditTrailView.vue`
- **Route**: `/admin/audit`
- **Purpose**: Immutable security audit log inspector tracking all clinical, financial, and access events for HIPAA compliance.

#### Table Columns & Filter Capabilities
- **Timestamp**: Formatted date & time with millisecond precision.
- **Actor**: Username, full name, and role badge of user performing the action.
- **Action Type Badge**:
  - `CREATE_APPOINTMENT` (Emerald)
  - `CANCEL_APPOINTMENT` (Rose)
  - `ADD_TREATMENT_RECORD` (Teal)
  - `RECORD_PAYMENT` (Indigo)
  - `LOGIN_SUCCESS` / `LOGIN_FAILURE` (Slate / Amber)
- **Target Entity**: Entity category (`appointment`, `treatment_record`, `payment`, `user`) and target ID.
- **Client IP Address**: Network address recorded on the request.
- **Detail Inspector**:
  - "Inspect Payload" button opens a modal displaying the complete structured JSON payload (e.g. before/after change diffs, payment receipt references, cancellation reasons).

#### State & Backend Integration
- Interacts with `useAdminStore`:
  - `fetchAuditLogs({ actor_id, action, target_type, start_date, end_date, page, limit })`.
- **Target Git Commit**:
  ```bash
  git add frontend/src/views/admin/AuditTrailView.vue frontend/src/router/index.ts
  git commit -m "feat: implement admin security and compliance audit trail inspector view"
  ```

