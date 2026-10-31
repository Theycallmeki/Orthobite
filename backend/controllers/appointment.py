from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.appointment import Appointment, AppointmentStatus
from models.doctor import AvailabilityRule, DoctorProfile, TimeOff
from models.patient import Patient
from models.users import User, UserRole
from schemas.appointment import (
    AppointmentCreate,
    AppointmentDoctorSummary,
    AppointmentListResponse,
    AppointmentPatientSummary,
    AppointmentResponse,
    AppointmentStatusUpdate,
    AppointmentUpdate,
    DailyScheduleResponse,
)

MIN_CANCELLATION_NOTICE_HOURS = 2


# ---------------------------------------------------------------------------
# Internal Helpers & Mappers
# ---------------------------------------------------------------------------

def get_appointment_or_404(db: Session, appointment_id: int) -> Appointment:
    """Fetch appointment by ID or raise 404."""
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Appointment with ID {appointment_id} not found.",
        )
    return appt


def to_appointment_response(appt: Appointment) -> AppointmentResponse:
    """Transform ORM Appointment into enriched AppointmentResponse."""
    doctor_summary = None
    if appt.doctor:
        doc_user = appt.doctor.user
        doctor_summary = AppointmentDoctorSummary(
            id=appt.doctor.id,
            user_id=appt.doctor.user_id,
            full_name=doc_user.full_name if doc_user else "Doctor",
            specialty=appt.doctor.specialty,
            photo_url=appt.doctor.photo_url,
            consultation_fee=appt.doctor.consultation_fee or Decimal("0.00"),
        )

    patient_summary = None
    if appt.patient:
        patient_summary = AppointmentPatientSummary(
            id=appt.patient.id,
            full_name=appt.patient.full_name,
            username=appt.patient.username,
            email=appt.patient.email,
            phone=appt.patient.phone,
        )

    formatted_date = appt.start_time.strftime("%A, %b %d, %Y")
    formatted_time = f"{appt.start_time.strftime('%I:%M %p')} - {appt.end_time.strftime('%I:%M %p')}"

    return AppointmentResponse(
        id=appt.id,
        patient_id=appt.patient_id,
        doctor_id=appt.doctor_id,
        start_time=appt.start_time,
        end_time=appt.end_time,
        status=appt.status,
        reason_for_visit=appt.reason_for_visit,
        notes=appt.notes,
        cancellation_reason=appt.cancellation_reason,
        created_at=appt.created_at,
        updated_at=appt.updated_at,
        doctor=doctor_summary,
        patient=patient_summary,
        formatted_date=formatted_date,
        formatted_time=formatted_time,
    )


def compute_slot_duration(db: Session, doctor_id: int, start_time: datetime) -> int:
    """Fetch configured slot duration for this doctor on this day of week, defaulting to 30 min."""
    rule = (
        db.query(AvailabilityRule)
        .filter(
            AvailabilityRule.doctor_id == doctor_id,
            AvailabilityRule.day_of_week == start_time.weekday(),
            AvailabilityRule.is_active == True,
        )
        .first()
    )
    return rule.slot_duration_minutes if rule else 30


# ---------------------------------------------------------------------------
# Conflict Detection Engine
# ---------------------------------------------------------------------------

def check_booking_conflicts(
    db: Session,
    doctor_id: int,
    patient_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_appointment_id: Optional[int] = None,
):
    """
    Comprehensive conflict prevention:
    1. Chronological order (start_time < end_time).
    2. Past time validation.
    3. Doctor active & accepting patients check.
    4. Doctor scheduled Time-Off overlap check.
    5. Doctor working hours compliance (weekly availability rules).
    6. Doctor double-booking overlap check (atomic conflict prevention).
    7. Patient simultaneous booking check.
    """
    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment start time must be strictly before end time.",
        )

    now = datetime.now(timezone.utc if start_time.tzinfo else None)
    if start_time < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot book an appointment in the past.",
        )

    # 1. Doctor Profile check
    doctor = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with ID {doctor_id} not found.",
        )
    if not doctor.is_accepting_patients:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dr. {doctor.user.full_name if doctor.user else doctor_id} is currently not accepting new appointments.",
        )

    # 2. Doctor Time-Off Conflict
    time_off = (
        db.query(TimeOff)
        .filter(
            TimeOff.doctor_id == doctor_id,
            TimeOff.start_datetime < end_time,
            TimeOff.end_datetime > start_time,
        )
        .first()
    )
    if time_off:
        reason_desc = f" ({time_off.reason})" if time_off.reason else ""
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Doctor is unavailable due to scheduled time-off{reason_desc}.",
        )

    # 3. Doctor Weekly Availability Rules Compliance
    day_rules = (
        db.query(AvailabilityRule)
        .filter(
            AvailabilityRule.doctor_id == doctor_id,
            AvailabilityRule.day_of_week == start_time.weekday(),
            AvailabilityRule.is_active == True,
        )
        .all()
    )
    if day_rules:
        # Verify requested slot falls within at least one active working window
        start_t = start_time.time()
        end_t = end_time.time()
        within_rule = any(
            rule.start_time <= start_t and rule.end_time >= end_t
            for rule in day_rules
        )
        if not within_rule:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The requested slot falls outside the doctor's active working hours for this day.",
            )

    # 4. Doctor Double-Booking Conflict Check
    doc_conflict_query = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]),
        Appointment.start_time < end_time,
        Appointment.end_time > start_time,
    )
    if exclude_appointment_id:
        doc_conflict_query = doc_conflict_query.filter(Appointment.id != exclude_appointment_id)

    if doc_conflict_query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The doctor already has an active appointment scheduled during this time window.",
        )

    # 5. Patient Double-Booking Conflict Check
    patient_conflict_query = db.query(Appointment).filter(
        Appointment.patient_id == patient_id,
        Appointment.status.in_([AppointmentStatus.PENDING, AppointmentStatus.CONFIRMED]),
        Appointment.start_time < end_time,
        Appointment.end_time > start_time,
    )
    if exclude_appointment_id:
        patient_conflict_query = patient_conflict_query.filter(Appointment.id != exclude_appointment_id)

    if patient_conflict_query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have an active appointment scheduled during this time window.",
        )


# ---------------------------------------------------------------------------
# Booking Business Logic
# ---------------------------------------------------------------------------

def book_appointment(
    db: Session,
    current_user: User,
    data: AppointmentCreate,
    target_patient_id: Optional[int] = None,
) -> AppointmentResponse:
    """
    Book an appointment.
    - If booked by patient: target_patient_id is current_user.id.
    - If booked by secretary or admin: target_patient_id is provided in the admin schema.
    """
    patient_id = target_patient_id if target_patient_id is not None else current_user.id

    patient_user = db.query(User).filter(User.id == patient_id).first()
    if not patient_user or not patient_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient user with ID {patient_id} not found.",
        )

    # Auto-provision clinical patient record if not yet created
    patient_record = db.query(Patient).filter(Patient.user_id == patient_id).first()
    if not patient_record:
        patient_record = Patient(
            user_id=patient_id,
            phone=patient_user.phone,
        )
        db.add(patient_record)
        db.flush()

    # Determine end_time if omitted
    end_time = data.end_time
    if not end_time:
        duration_mins = compute_slot_duration(db, data.doctor_id, data.start_time)
        end_time = data.start_time + timedelta(minutes=duration_mins)

    # Validate conflicts
    check_booking_conflicts(
        db=db,
        doctor_id=data.doctor_id,
        patient_id=patient_id,
        start_time=data.start_time,
        end_time=end_time,
    )

    appointment = Appointment(
        patient_id=patient_id,
        doctor_id=data.doctor_id,
        start_time=data.start_time,
        end_time=end_time,
        status=AppointmentStatus.PENDING,
        reason_for_visit=data.reason_for_visit,
        notes=data.notes,
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    return to_appointment_response(appointment)


# ---------------------------------------------------------------------------
# Patient Schedule Queries
# ---------------------------------------------------------------------------

def get_patient_appointments(
    db: Session,
    patient_id: int,
    status_filter: Optional[AppointmentStatus] = None,
    upcoming_only: bool = False,
) -> List[AppointmentResponse]:
    """Retrieve all appointments for a patient (history and upcoming)."""
    query = db.query(Appointment).filter(Appointment.patient_id == patient_id)

    if status_filter:
        query = query.filter(Appointment.status == status_filter)

    now = datetime.now()
    if upcoming_only:
        query = query.filter(Appointment.start_time >= now).order_by(Appointment.start_time.asc())
    else:
        query = query.order_by(Appointment.start_time.desc())

    records = query.all()
    return [to_appointment_response(a) for a in records]


# ---------------------------------------------------------------------------
# Doctor Schedule Queries
# ---------------------------------------------------------------------------

def get_doctor_daily_schedule(
    db: Session,
    doctor_profile_id: int,
    target_date: Optional[date] = None,
) -> DailyScheduleResponse:
    """Retrieve full schedule and stats for a doctor on a specific day (default today)."""
    if not target_date:
        target_date = date.today()

    start_of_day = datetime.combine(target_date, time.min)
    end_of_day = datetime.combine(target_date, time.max)

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.doctor_id == doctor_profile_id,
            Appointment.start_time >= start_of_day,
            Appointment.start_time <= end_of_day,
        )
        .order_by(Appointment.start_time.asc())
        .all()
    )

    confirmed_count = sum(1 for a in appointments if a.status == AppointmentStatus.CONFIRMED)
    pending_count = sum(1 for a in appointments if a.status == AppointmentStatus.PENDING)
    completed_count = sum(1 for a in appointments if a.status == AppointmentStatus.COMPLETED)
    cancelled_count = sum(1 for a in appointments if a.status == AppointmentStatus.CANCELLED)
    no_show_count = sum(1 for a in appointments if a.status == AppointmentStatus.NO_SHOW)

    return DailyScheduleResponse(
        date=target_date.isoformat(),
        total_appointments=len(appointments),
        confirmed_count=confirmed_count,
        pending_count=pending_count,
        completed_count=completed_count,
        cancelled_count=cancelled_count,
        no_show_count=no_show_count,
        appointments=[to_appointment_response(a) for a in appointments],
    )


# ---------------------------------------------------------------------------
# Secretary & Clinic-Wide Queries
# ---------------------------------------------------------------------------

def list_secretary_appointments(
    db: Session,
    target_date: Optional[date] = None,
    doctor_id: Optional[int] = None,
    status_filter: Optional[AppointmentStatus] = None,
    skip: int = 0,
    limit: int = 100,
) -> AppointmentListResponse:
    """Clinic-wide schedule view with filtering for secretary and admin staff."""
    query = db.query(Appointment)

    if target_date:
        start_of_day = datetime.combine(target_date, time.min)
        end_of_day = datetime.combine(target_date, time.max)
        query = query.filter(
            Appointment.start_time >= start_of_day,
            Appointment.start_time <= end_of_day,
        )

    if doctor_id:
        query = query.filter(Appointment.doctor_id == doctor_id)

    if status_filter:
        query = query.filter(Appointment.status == status_filter)

    total = query.count()
    appointments = query.order_by(Appointment.start_time.asc()).offset(skip).limit(limit).all()

    return AppointmentListResponse(
        total=total,
        appointments=[to_appointment_response(a) for a in appointments],
    )


# ---------------------------------------------------------------------------
# Status Update & Cancellation Rules
# ---------------------------------------------------------------------------

def update_appointment_status(
    db: Session,
    appointment_id: int,
    current_user: User,
    data: AppointmentStatusUpdate,
) -> AppointmentResponse:
    """
    Update appointment status with strict role and cancellation notice validation:
    - Patients may ONLY cancel their own appointments, subject to the minimum notice window.
    - Doctors may confirm, complete, cancel, or mark no-show for their assigned appointments.
    - Secretaries and Admins have clinic-wide authority to manage statuses.
    """
    appt = get_appointment_or_404(db, appointment_id)

    # 1. State machine rules
    if appt.status == AppointmentStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Completed appointments cannot change status.",
        )
    if appt.status == AppointmentStatus.CANCELLED and data.status == AppointmentStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment is already cancelled.",
        )

    # 2. Patient-specific restrictions & notice window
    if current_user.role == UserRole.PATIENT:
        if appt.patient_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only manage your own appointments.",
            )
        if data.status != AppointmentStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Patients are only authorized to cancel appointments. Status updates must be performed by clinic staff.",
            )

        # Minimum notice window check
        now = datetime.now(timezone.utc if appt.start_time.tzinfo else None)
        if appt.start_time - now < timedelta(hours=MIN_CANCELLATION_NOTICE_HOURS):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Appointments cannot be cancelled online less than {MIN_CANCELLATION_NOTICE_HOURS} hours before start time. Please call the clinic directly.",
            )

    # 3. Doctor-specific restrictions
    elif current_user.role in (UserRole.DOCTOR, UserRole.ORTHODONTIST):
        # Verify doctor is assigned to this appointment
        if not appt.doctor or appt.doctor.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Doctors can only manage appointments assigned to them.",
            )

    # 4. Apply status update
    appt.status = data.status
    if data.status == AppointmentStatus.CANCELLED:
        appt.cancellation_reason = data.cancellation_reason or "Cancelled by user"

    if data.notes:
        appt.notes = data.notes

    db.commit()
    db.refresh(appt)
    return to_appointment_response(appt)


# ---------------------------------------------------------------------------
# Rescheduling
# ---------------------------------------------------------------------------

def reschedule_appointment(
    db: Session,
    appointment_id: int,
    current_user: User,
    data: AppointmentUpdate,
) -> AppointmentResponse:
    """Reschedule an existing appointment to a new date and time."""
    appt = get_appointment_or_404(db, appointment_id)

    # Authorization check
    is_staff = current_user.role in (UserRole.ADMIN, UserRole.SECRETARY, UserRole.DOCTOR, UserRole.ORTHODONTIST)
    if not is_staff and appt.patient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only reschedule your own appointments.",
        )

    if appt.status in (AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reschedule an appointment with status '{appt.status.value}'.",
        )

    new_start = data.start_time or appt.start_time
    new_end = data.end_time
    if not new_end:
        duration = appt.end_time - appt.start_time
        new_end = new_start + duration

    # Conflict check
    check_booking_conflicts(
        db=db,
        doctor_id=appt.doctor_id,
        patient_id=appt.patient_id,
        start_time=new_start,
        end_time=new_end,
        exclude_appointment_id=appt.id,
    )

    appt.start_time = new_start
    appt.end_time = new_end
    if data.reason_for_visit:
        appt.reason_for_visit = data.reason_for_visit
    if data.notes:
        appt.notes = data.notes

    db.commit()
    db.refresh(appt)
    return to_appointment_response(appt)
