from datetime import date
from typing import List, Optional, Union
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from config.database import get_db
import controllers.appointment as appointment_controller
import controllers.doctor as doctor_controller
from dependencies import (
    get_current_user,
    require_doctor,
    require_patient,
    require_secretary,
    require_staff,
)
from models.appointment import AppointmentStatus
from models.users import User, UserRole
from schemas.appointment import (
    AppointmentAdminCreate,
    AppointmentCreate,
    AppointmentListResponse,
    AppointmentResponse,
    AppointmentStatusUpdate,
    AppointmentUpdate,
    DailyScheduleResponse,
)

router = APIRouter(prefix="/appointments", tags=["Appointments"])


# ---------------------------------------------------------------------------
# Patient & Staff Booking Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=AppointmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Book a new appointment (Requires logged-in user)",
)
def book_appointment(
    payload: Union[AppointmentAdminCreate, AppointmentCreate],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Book a new appointment with double-booking and time-off conflict prevention.
    - If booked by a **Patient**: books for self using authenticated account.
    - If booked by **Secretary** or **Admin**: can specify a target patient_id.
    """
    target_patient_id = None
    is_staff = current_user.role in (UserRole.ADMIN, UserRole.SECRETARY)

    if isinstance(payload, AppointmentAdminCreate) or hasattr(payload, "patient_id"):
        if getattr(payload, "patient_id", None) is not None:
            if not is_staff and payload.patient_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only receptionists or administrators can book on behalf of other patients.",
                )
            target_patient_id = payload.patient_id

    return appointment_controller.book_appointment(
        db=db,
        current_user=current_user,
        data=payload,
        target_patient_id=target_patient_id,
    )


# ---------------------------------------------------------------------------
# Patient Schedule View
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=List[AppointmentResponse],
    summary="Patient view of upcoming and past visits",
)
def get_my_appointments(
    status_filter: Optional[AppointmentStatus] = Query(
        None,
        alias="status",
        description="Filter by appointment status (e.g. pending, confirmed, completed, cancelled)",
    ),
    upcoming_only: bool = Query(
        False,
        description="Set to true to return only future appointments ordered chronologically",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns all appointments for the currently logged-in patient.
    Supports filtering by status or retrieving only upcoming visits.
    """
    return appointment_controller.get_patient_appointments(
        db=db,
        patient_id=current_user.id,
        status_filter=status_filter,
        upcoming_only=upcoming_only,
    )


# ---------------------------------------------------------------------------
# Doctor Daily Schedule View
# ---------------------------------------------------------------------------

@router.get(
    "/doctor/today",
    response_model=DailyScheduleResponse,
    summary="Doctor's daily schedule view",
)
def get_doctor_today_schedule(
    target_date: Optional[date] = Query(
        None,
        alias="date",
        description="Target schedule date (YYYY-MM-DD). Defaults to today.",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """
    Doctor's daily appointment itinerary and progress status breakdown.
    Displays patient names, start/end times, reason for visit, and booking status.
    """
    doctor_profile = doctor_controller.get_or_create_doctor_profile_for_user(db, current_user)
    return appointment_controller.get_doctor_daily_schedule(
        db=db,
        doctor_profile_id=doctor_profile.id,
        target_date=target_date,
    )


# ---------------------------------------------------------------------------
# Secretary Clinic-Wide Schedule View
# ---------------------------------------------------------------------------

@router.get(
    "/secretary",
    response_model=AppointmentListResponse,
    summary="Clinic-wide schedule & filter view for secretary",
)
def get_secretary_schedule(
    target_date: Optional[date] = Query(
        None,
        alias="date",
        description="Filter by specific date (YYYY-MM-DD)",
    ),
    doctor_id: Optional[int] = Query(
        None,
        description="Filter by doctor profile ID",
    ),
    status_filter: Optional[AppointmentStatus] = Query(
        None,
        alias="status",
        description="Filter by appointment status",
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_secretary),
):
    """
    Clinic-wide master schedule for secretary and receptionists.
    Supports filtering by date, doctor, and status with pagination.
    """
    return appointment_controller.list_secretary_appointments(
        db=db,
        target_date=target_date,
        doctor_id=doctor_id,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )


# ---------------------------------------------------------------------------
# Appointment Details, Status Management & Rescheduling
# ---------------------------------------------------------------------------

@router.get(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Get single appointment details",
)
def get_appointment_details(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Fetch details of a specific appointment."""
    appt = appointment_controller.get_appointment_or_404(db, appointment_id)

    # Permission check: patient, assigned doctor, or staff
    is_staff = current_user.role in (UserRole.ADMIN, UserRole.SECRETARY)
    is_own_doc = appt.doctor and appt.doctor.user_id == current_user.id
    if not is_staff and not is_own_doc and appt.patient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to view this appointment.",
        )

    return appointment_controller.to_appointment_response(appt)


@router.patch(
    "/{appointment_id}/status",
    response_model=AppointmentResponse,
    summary="Secretary/Doctor confirm, complete, or cancel",
)
def update_status(
    appointment_id: int,
    payload: AppointmentStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update appointment status:
    - **Doctor & Secretary**: Confirm, Complete, Cancel, or Mark No-Show.
    - **Patient**: May only cancel their own appointment (subject to 2h notice window).
    """
    return appointment_controller.update_appointment_status(
        db=db,
        appointment_id=appointment_id,
        current_user=current_user,
        data=payload,
    )


@router.patch(
    "/{appointment_id}/reschedule",
    response_model=AppointmentResponse,
    summary="Reschedule an appointment to a new time",
)
def reschedule_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reschedule an existing appointment to a new time slot.
    Performs conflict detection against doctor schedule and other appointments.
    """
    return appointment_controller.reschedule_appointment(
        db=db,
        appointment_id=appointment_id,
        current_user=current_user,
        data=payload,
    )


@router.delete(
    "/{appointment_id}",
    response_model=AppointmentResponse,
    summary="Cancel an appointment",
)
def cancel_appointment(
    appointment_id: int,
    reason: Optional[str] = Query(None, description="Reason for cancellation"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Convenience endpoint to cancel an appointment."""
    status_update = AppointmentStatusUpdate(
        status=AppointmentStatus.CANCELLED,
        cancellation_reason=reason or "Cancelled by user",
    )
    return appointment_controller.update_appointment_status(
        db=db,
        appointment_id=appointment_id,
        current_user=current_user,
        data=status_update,
    )
