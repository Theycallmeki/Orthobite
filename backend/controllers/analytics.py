from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from models.appointment import Appointment, AppointmentStatus
from models.doctor import DoctorProfile
from models.patient import Patient
from models.record import Payment, TreatmentRecord
from models.users import User, UserRole
from schemas.analytics import (
    AppointmentBreakdownResponse,
    ClinicOverviewResponse,
    MonthlyAppointmentStat,
    MonthlyRevenueStat,
    RevenueReportResponse,
)


def get_clinic_overview(db: Session) -> ClinicOverviewResponse:
    """High-level dashboard counters for the admin panel."""
    total_patients = (
        db.query(User)
        .filter(User.role == UserRole.PATIENT, User.is_active == True)
        .count()
    )
    total_doctors = (
        db.query(DoctorProfile)
        .join(User, DoctorProfile.user_id == User.id)
        .filter(User.is_active == True)
        .count()
    )
    appt_counts = {
        s: db.query(Appointment).filter(Appointment.status == s).count()
        for s in AppointmentStatus
    }

    return ClinicOverviewResponse(
        total_patients=total_patients,
        total_doctors=total_doctors,
        total_active_appointments=appt_counts[AppointmentStatus.CONFIRMED],
        total_completed_appointments=appt_counts[AppointmentStatus.COMPLETED],
        total_pending_appointments=appt_counts[AppointmentStatus.PENDING],
        total_cancelled_appointments=appt_counts[AppointmentStatus.CANCELLED],
    )


def get_appointment_breakdown(db: Session, months: int = 12) -> AppointmentBreakdownResponse:
    """
    Returns per-month appointment counts broken down by status
    for the last ``months`` calendar months.
    """
    rows = (
        db.query(
            func.to_char(Appointment.start_time, "YYYY-MM").label("month"),
            Appointment.status,
            func.count(Appointment.id).label("cnt"),
        )
        .group_by("month", Appointment.status)
        .order_by("month")
        .all()
    )


    bucket: dict = {}
    for month, status, cnt in rows:
        if month not in bucket:
            bucket[month] = {s.value: 0 for s in AppointmentStatus}
        bucket[month][status.value] = cnt

    stats: List[MonthlyAppointmentStat] = [
        MonthlyAppointmentStat(
            month=m,
            total=sum(v.values()),
            confirmed=v.get("confirmed", 0),
            completed=v.get("completed", 0),
            cancelled=v.get("cancelled", 0),
            no_show=v.get("no_show", 0),
            pending=v.get("pending", 0),
        )
        for m, v in sorted(bucket.items())[-months:]
    ]

    return AppointmentBreakdownResponse(months=stats)


def get_revenue_report(db: Session, months: int = 12) -> RevenueReportResponse:
    """
    Monthly revenue collected (sum of Payment.amount) vs total billed
    (sum of TreatmentRecord.value_of_work) for the last ``months`` months.
    Outstanding = billed − collected.
    """

    payment_rows = (
        db.query(
            func.to_char(Payment.payment_date, "YYYY-MM").label("month"),
            func.sum(Payment.amount).label("collected"),
        )
        .group_by("month")
        .all()
    )


    billing_rows = (
        db.query(
            func.to_char(TreatmentRecord.date, "YYYY-MM").label("month"),
            func.sum(TreatmentRecord.value_of_work).label("billed"),
        )
        .group_by("month")
        .all()
    )


    rev_map: dict = {}
    for month, collected in payment_rows:
        rev_map.setdefault(month, {"collected": Decimal("0"), "billed": Decimal("0")})
        rev_map[month]["collected"] += Decimal(str(collected or 0))

    for month, billed in billing_rows:
        rev_map.setdefault(month, {"collected": Decimal("0"), "billed": Decimal("0")})
        rev_map[month]["billed"] += Decimal(str(billed or 0))

    stats: List[MonthlyRevenueStat] = [
        MonthlyRevenueStat(
            month=m,
            revenue_collected=float(v["collected"]),
            outstanding_balance=float(v["billed"] - v["collected"]),
            total_billed=float(v["billed"]),
        )
        for m, v in sorted(rev_map.items())[-months:]
    ]

    grand_billed    = sum(s.total_billed for s in stats)
    grand_collected = sum(s.revenue_collected for s in stats)

    return RevenueReportResponse(
        months=stats,
        grand_total_billed=grand_billed,
        grand_total_collected=grand_collected,
        grand_outstanding=grand_billed - grand_collected,
    )
