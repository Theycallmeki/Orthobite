from typing import Dict, List
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

class ClinicOverviewResponse(BaseModel):
    total_patients:          int
    total_doctors:           int
    total_active_appointments: int
    total_completed_appointments: int
    total_pending_appointments: int
    total_cancelled_appointments: int


# ---------------------------------------------------------------------------
# Monthly appointment breakdown
# ---------------------------------------------------------------------------

class MonthlyAppointmentStat(BaseModel):
    month:      str   # "YYYY-MM"
    total:      int
    confirmed:  int
    completed:  int
    cancelled:  int
    no_show:    int
    pending:    int


class AppointmentBreakdownResponse(BaseModel):
    months: List[MonthlyAppointmentStat]


# ---------------------------------------------------------------------------
# Revenue
# ---------------------------------------------------------------------------

class MonthlyRevenueStat(BaseModel):
    month:            str   # "YYYY-MM"
    revenue_collected: float
    outstanding_balance: float
    total_billed:     float


class RevenueReportResponse(BaseModel):
    months:              List[MonthlyRevenueStat]
    grand_total_billed:  float
    grand_total_collected: float
    grand_outstanding:   float

