import calendar
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional, List

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.doctor import AvailabilityRule, DoctorProfile, TimeOff
from models.users import User, UserRole
from schemas.doctor import (
    AvailabilityRuleItem,
    AvailabilityRuleResponse,
    DayAvailability,
    DoctorAvailabilityResponse,
    DoctorProfileUpdate,
    DoctorPublicResponse,
    TimeOffCreate,
    TimeOffResponse,
    TimeSlot,
)

DAYS_OF_WEEK_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

def get_doctor_profile_or_404(db: Session, doctor_id: int) -> DoctorProfile:
    """Fetch doctor profile by doctor_profile ID."""
    doc = db.query(DoctorProfile).filter(DoctorProfile.id == doctor_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor with ID {doctor_id} not found.",
        )
    return doc


def get_or_create_doctor_profile_for_user(db: Session, user: User) -> DoctorProfile:
    """Get or auto-create doctor profile for a user with DOCTOR or ORTHODONTIST role."""
    if user.role not in (UserRole.DOCTOR, UserRole.ORTHODONTIST, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only doctors can have a doctor profile.",
        )

    profile = db.query(DoctorProfile).filter(DoctorProfile.user_id == user.id).first()
    if not profile:
        profile = DoctorProfile(
            user_id=user.id,
            specialty="Orthodontics & Bite Alignment",
            bio="Dedicated orthodontics specialist providing modern bite alignment treatments.",
            years_of_experience=5,
            is_accepting_patients=True,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)

    return profile


def to_doctor_public_response(doc: DoctorProfile) -> DoctorPublicResponse:
    """Convert DoctorProfile model to public response DTO."""
    return DoctorPublicResponse(
        id=doc.id,
        user_id=doc.user_id,
        full_name=doc.user.full_name if doc.user else "Doctor",
        username=doc.user.username if doc.user else "",
        email=doc.user.email if doc.user else "",
        specialty=doc.specialty,
        bio=doc.bio,
        photo_url=doc.photo_url,
        years_of_experience=doc.years_of_experience,
        education=doc.education,
        consultation_fee=doc.consultation_fee,
        is_accepting_patients=doc.is_accepting_patients,
    )


# ---------------------------------------------------------------------------
# Public Doctor Carousel Queries
# ---------------------------------------------------------------------------

def list_public_doctors(db: Session) -> List[DoctorPublicResponse]:
    """Retrieve all active doctors accepting patients for the frontend carousel."""
    doctors = (
        db.query(DoctorProfile)
        .join(User, DoctorProfile.user_id == User.id)
        .filter(User.is_active == True, DoctorProfile.is_accepting_patients == True)
        .order_by(DoctorProfile.id.asc())
        .all()
    )
    return [to_doctor_public_response(d) for d in doctors]


def get_doctor_public_profile(db: Session, doctor_id: int) -> DoctorPublicResponse:
    """Retrieve public profile for a specific doctor."""
    doc = get_doctor_profile_or_404(db, doctor_id)
    return to_doctor_public_response(doc)


# ---------------------------------------------------------------------------
# Profile Management
# ---------------------------------------------------------------------------

def update_doctor_profile(
    db: Session,
    profile: DoctorProfile,
    data: DoctorProfileUpdate,
) -> DoctorPublicResponse:
    """Update doctor's bio, specialty, photo, fee, or availability status."""
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return to_doctor_public_response(profile)


# ---------------------------------------------------------------------------
# Availability Rules
# ---------------------------------------------------------------------------

def set_doctor_availability_rules(
    db: Session,
    profile: DoctorProfile,
    rules: List[AvailabilityRuleItem],
) -> List[AvailabilityRuleResponse]:
    """Replace doctor's weekly recurring availability rules."""
    # Remove existing rules
    db.query(AvailabilityRule).filter(AvailabilityRule.doctor_id == profile.id).delete()

    created_rules = []
    for item in rules:
        if item.start_time >= item.end_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Start time ({item.start_time}) must be earlier than end time ({item.end_time}).",
            )
        rule = AvailabilityRule(
            doctor_id=profile.id,
            day_of_week=item.day_of_week,
            start_time=item.start_time,
            end_time=item.end_time,
            slot_duration_minutes=item.slot_duration_minutes,
            is_active=item.is_active,
        )
        db.add(rule)
        created_rules.append(rule)

    db.commit()
    for r in created_rules:
        db.refresh(r)

    return [AvailabilityRuleResponse.model_validate(r) for r in created_rules]


def get_doctor_availability_rules(db: Session, doctor_id: int) -> List[AvailabilityRuleResponse]:
    """Fetch weekly recurring rules for a doctor."""
    rules = (
        db.query(AvailabilityRule)
        .filter(AvailabilityRule.doctor_id == doctor_id, AvailabilityRule.is_active == True)
        .order_by(AvailabilityRule.day_of_week.asc(), AvailabilityRule.start_time.asc())
        .all()
    )
    return [AvailabilityRuleResponse.model_validate(r) for r in rules]


# ---------------------------------------------------------------------------
# Time Off
# ---------------------------------------------------------------------------

def add_doctor_time_off(
    db: Session,
    profile: DoctorProfile,
    data: TimeOffCreate,
) -> TimeOffResponse:
    """Block out vacation, leave, or unavailable time range."""
    if data.start_datetime >= data.end_datetime:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start datetime must be before end datetime.",
        )

    time_off = TimeOff(
        doctor_id=profile.id,
        start_datetime=data.start_datetime,
        end_datetime=data.end_datetime,
        reason=data.reason,
    )
    db.add(time_off)
    db.commit()
    db.refresh(time_off)
    return TimeOffResponse.model_validate(time_off)


def list_doctor_time_off(db: Session, doctor_id: int) -> List[TimeOffResponse]:
    """List doctor's scheduled time-off records."""
    records = (
        db.query(TimeOff)
        .filter(TimeOff.doctor_id == doctor_id)
        .order_by(TimeOff.start_datetime.asc())
        .all()
    )
    return [TimeOffResponse.model_validate(r) for r in records]


# ---------------------------------------------------------------------------
# Availability Slot Generation Engine (For Carousel Calendar)
# ---------------------------------------------------------------------------

def generate_doctor_availability(
    db: Session,
    doctor_id: int,
    month_str: Optional[str] = None,
) -> DoctorAvailabilityResponse:
    """
    Generate month availability slots for a doctor.
    month_str: 'YYYY-MM', defaults to current month if None.
    """
    doc = get_doctor_profile_or_404(db, doctor_id)

    now = datetime.now()
    if month_str:
        try:
            parts = month_str.split("-")
            year = int(parts[0])
            month = int(parts[1])
            if month < 1 or month > 12:
                raise ValueError
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid month format. Please use 'YYYY-MM' (e.g. '2026-11').",
            )
    else:
        year = now.year
        month = now.month
        month_str = f"{year:04d}-{month:02d}"

    _, num_days = calendar.monthrange(year, month)

    # Fetch active rules mapped by day_of_week
    rules = (
        db.query(AvailabilityRule)
        .filter(AvailabilityRule.doctor_id == doctor_id, AvailabilityRule.is_active == True)
        .all()
    )
    rules_by_day = {}
    for r in rules:
        rules_by_day.setdefault(r.day_of_week, []).append(r)

    # Fetch time off ranges covering this month
    month_start = datetime(year, month, 1)
    month_end = datetime(year, month, num_days, 23, 59, 59)
    time_off_list = (
        db.query(TimeOff)
        .filter(
            TimeOff.doctor_id == doctor_id,
            TimeOff.start_datetime <= month_end,
            TimeOff.end_datetime >= month_start,
        )
        .all()
    )

    days_result = []

    for day_num in range(1, num_days + 1):
        current_date = date(year, month, day_num)
        day_of_week = current_date.weekday()  # 0=Monday, ..., 6=Sunday
        day_rules = rules_by_day.get(day_of_week, [])

        day_slots = []

        for rule in day_rules:
            # Generate slots from rule.start_time to rule.end_time
            slot_start = datetime.combine(current_date, rule.start_time)
            rule_end = datetime.combine(current_date, rule.end_time)
            slot_delta = timedelta(minutes=rule.slot_duration_minutes)

            while slot_start + slot_delta <= rule_end:
                slot_end = slot_start + slot_delta

                # Determine if slot is available
                is_available = True

                # Check if slot is in the past
                if slot_end < now:
                    is_available = False

                # Check overlap with any TimeOff
                if is_available:
                    for to in time_off_list:
                        to_start = to.start_datetime.replace(tzinfo=None) if to.start_datetime.tzinfo else to.start_datetime
                        to_end = to.end_datetime.replace(tzinfo=None) if to.end_datetime.tzinfo else to.end_datetime
                        if slot_start < to_end and slot_end > to_start:
                            is_available = False
                            break

                day_slots.append(
                    TimeSlot(
                        start_time=slot_start.isoformat(),
                        end_time=slot_end.isoformat(),
                        formatted_time=slot_start.strftime("%I:%M %p"),
                        is_available=is_available,
                    )
                )

                slot_start = slot_end

        days_result.append(
            DayAvailability(
                date=current_date.isoformat(),
                day_of_week=day_of_week,
                day_name=DAYS_OF_WEEK_NAMES[day_of_week],
                slots=day_slots,
            )
        )

    doctor_name = doc.user.full_name if doc.user else f"Doctor #{doc.id}"

    return DoctorAvailabilityResponse(
        doctor_id=doc.id,
        doctor_name=doctor_name,
        month=month_str,
        days=days_result,
    )
