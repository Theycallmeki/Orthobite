from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

from models.appointment import AppointmentStatus


# ---------------------------------------------------------------------------
# Nested Profile Summaries for Response Payloads
# ---------------------------------------------------------------------------

class AppointmentDoctorSummary(BaseModel):
    id: int
    user_id: int
    full_name: str
    specialty: str
    photo_url: Optional[str] = None
    consultation_fee: Decimal = Decimal("0.00")

    model_config = {"from_attributes": True}


class AppointmentPatientSummary(BaseModel):
    id: int
    full_name: str
    username: str
    email: str
    phone: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Request Payloads
# ---------------------------------------------------------------------------

class AppointmentCreate(BaseModel):
    doctor_id: int = Field(..., description="ID of the doctor profile to book with")
    start_time: datetime = Field(..., description="ISO datetime of appointment start (e.g. 2026-11-02T10:00:00)")
    end_time: Optional[datetime] = Field(None, description="Optional ISO datetime of appointment end. If omitted, computed from doctor slot duration.")
    reason_for_visit: Optional[str] = Field(None, max_length=255, description="Brief reason e.g. 'Initial consultation', 'Braces adjustment'")
    notes: Optional[str] = Field(None, description="Patient notes or clinical concerns")


class AppointmentAdminCreate(AppointmentCreate):
    """Used by Secretary or Admin to book an appointment on behalf of any patient."""
    patient_id: int = Field(..., description="User ID of the patient")


class AppointmentUpdate(BaseModel):
    """Used to reschedule an appointment or update visit notes."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    reason_for_visit: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None


class AppointmentStatusUpdate(BaseModel):
    """Used by Doctor or Secretary to update status (or Patient to cancel)."""
    status: AppointmentStatus
    cancellation_reason: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Response Payloads
# ---------------------------------------------------------------------------

class AppointmentResponse(BaseModel):
    id: int
    patient_id: int
    doctor_id: int
    start_time: datetime
    end_time: datetime
    status: AppointmentStatus
    reason_for_visit: Optional[str] = None
    notes: Optional[str] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Enriched presentation fields
    doctor: Optional[AppointmentDoctorSummary] = None
    patient: Optional[AppointmentPatientSummary] = None
    formatted_date: Optional[str] = None
    formatted_time: Optional[str] = None

    model_config = {"from_attributes": True}


class DailyScheduleResponse(BaseModel):
    date: str
    total_appointments: int
    confirmed_count: int
    pending_count: int
    completed_count: int
    cancelled_count: int
    no_show_count: int
    appointments: List[AppointmentResponse]


class AppointmentListResponse(BaseModel):
    total: int
    appointments: List[AppointmentResponse]
