from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

import controllers.doctor as doctor_controller
from config.database import get_db
from dependencies import get_current_user, require_doctor
from models.users import User
from schemas.doctor import (
    AvailabilityRuleResponse,
    DoctorAvailabilityResponse,
    DoctorProfileUpdate,
    DoctorPublicResponse,
    SetAvailabilityRulesRequest,
    TimeOffCreate,
    TimeOffResponse,
)

router = APIRouter(prefix="/doctors", tags=["Doctors & Availability"])


# ---------------------------------------------------------------------------
# Public Carousel & Calendar Endpoints (No login required)
# ---------------------------------------------------------------------------

@router.get(
    "/",
    response_model=List[DoctorPublicResponse],
    summary="List all doctors for the homepage carousel (Public)",
)
def list_doctors(db: Session = Depends(get_db)):
    """
    Public endpoint feeding the doctor carousel on the homepage.
    Returns active doctors, photos, specialties, bios, and consultation fees.
    """
    return doctor_controller.list_public_doctors(db)


@router.get(
    "/{doctor_id}/availability",
    response_model=DoctorAvailabilityResponse,
    summary="Get doctor availability calendar slots (Public)",
)
def get_doctor_availability(
    doctor_id: int,
    month: Optional[str] = Query(
        None,
        description="Target month in YYYY-MM format (e.g. 2026-11). Defaults to current month.",
    ),
    db: Session = Depends(get_db),
):
    """
    Public endpoint feeding the calendar under each doctor in the carousel.
    Computes available 30-min time slots based on weekly rules minus time-off minus past time.
    """
    return doctor_controller.generate_doctor_availability(db, doctor_id, month)


@router.get(
    "/{doctor_id}",
    response_model=DoctorPublicResponse,
    summary="Get doctor public profile by ID (Public)",
)
def get_doctor_by_id(doctor_id: int, db: Session = Depends(get_db)):
    """Public details of a doctor."""
    return doctor_controller.get_doctor_public_profile(db, doctor_id)


# ---------------------------------------------------------------------------
# Authenticated Doctor Self-Management Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/me/profile",
    response_model=DoctorPublicResponse,
    summary="Get current doctor's own profile",
)
def get_my_doctor_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """Retrieve logged-in doctor's profile details."""
    profile = doctor_controller.get_or_create_doctor_profile_for_user(db, current_user)
    return doctor_controller.to_doctor_public_response(profile)


@router.patch(
    "/me/profile",
    response_model=DoctorPublicResponse,
    summary="Update current doctor's profile and photo",
)
def update_my_doctor_profile(
    data: DoctorProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """Update specialty, bio, photo URL, fee, or patient acceptance status."""
    profile = doctor_controller.get_or_create_doctor_profile_for_user(db, current_user)
    return doctor_controller.update_doctor_profile(db, profile, data)


@router.get(
    "/me/availability",
    response_model=List[AvailabilityRuleResponse],
    summary="Get current doctor's weekly recurring availability rules",
)
def get_my_availability_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """Get weekly rules for Monday through Sunday."""
    profile = doctor_controller.get_or_create_doctor_profile_for_user(db, current_user)
    return doctor_controller.get_doctor_availability_rules(db, profile.id)


@router.put(
    "/me/availability",
    response_model=List[AvailabilityRuleResponse],
    summary="Set current doctor's weekly recurring availability rules",
)
def set_my_availability_rules(
    payload: SetAvailabilityRulesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """
    Set or replace doctor's weekly schedule.
    Example: Monday-Friday from 09:00:00 to 17:00:00 in 30-minute intervals.
    """
    profile = doctor_controller.get_or_create_doctor_profile_for_user(db, current_user)
    return doctor_controller.set_doctor_availability_rules(db, profile, payload.rules)


@router.post(
    "/me/time-off",
    response_model=TimeOffResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Schedule doctor time-off / blocked range",
)
def create_my_time_off(
    data: TimeOffCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """Block out holidays, leave, or unavailable times from the public calendar."""
    profile = doctor_controller.get_or_create_doctor_profile_for_user(db, current_user)
    return doctor_controller.add_doctor_time_off(db, profile, data)


@router.get(
    "/me/time-off",
    response_model=List[TimeOffResponse],
    summary="List current doctor's scheduled time-off records",
)
def list_my_time_off(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor),
):
    """List scheduled leaves and blocked ranges."""
    profile = doctor_controller.get_or_create_doctor_profile_for_user(db, current_user)
    return doctor_controller.list_doctor_time_off(db, profile.id)
