from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

import controllers.analytics as analytics_controller
from config.database import get_db
from dependencies import require_admin
from models.users import User
from schemas.analytics import (
    AppointmentBreakdownResponse,
    ClinicOverviewResponse,
    RevenueReportResponse,
)

router = APIRouter(prefix="/admin/analytics", tags=["Admin Analytics"])


@router.get(
    "/overview",
    response_model=ClinicOverviewResponse,
    summary="Clinic overview counters (Admin only)",
)
def clinic_overview(
    db: Session = Depends(get_db),
    _:  User    = Depends(require_admin),
):
    """
    Returns total active patients, doctors, and appointment counts
    broken down by status. Feeds the main admin dashboard card row.
    """
    return analytics_controller.get_clinic_overview(db)


@router.get(
    "/appointments",
    response_model=AppointmentBreakdownResponse,
    summary="Monthly appointment breakdown (Admin only)",
)
def appointment_breakdown(
    months: int     = Query(12, ge=1, le=36, description="Number of recent months to include"),
    db:     Session = Depends(get_db),
    _:      User    = Depends(require_admin),
):
    """
    Per-month appointment counts broken down by status
    (pending, confirmed, completed, cancelled, no_show).
    Feeds bar/line charts on the admin analytics dashboard.
    """
    return analytics_controller.get_appointment_breakdown(db, months)


@router.get(
    "/revenue",
    response_model=RevenueReportResponse,
    summary="Monthly revenue vs outstanding balance (Admin only)",
)
def revenue_report(
    months: int     = Query(12, ge=1, le=36, description="Number of recent months to include"),
    db:     Session = Depends(get_db),
    _:      User    = Depends(require_admin),
):
    """
    Monthly revenue collected vs total billed, with outstanding balance.
    Feeds the financial chart on the admin analytics dashboard.
    """
    return analytics_controller.get_revenue_report(db, months)

