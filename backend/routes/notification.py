from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime

from config.database import get_db
from dependencies import get_current_user, require_staff, require_secretary
from models.appointment import Appointment
from models.notification import NotificationLog, NotificationStatus, NotificationType
from models.users import User, UserRole
from services.scheduler import scan_and_send_reminders

router = APIRouter(prefix="/notifications", tags=["Notifications & Reminders"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class NotificationLogResponse(BaseModel):
    id: int
    appointment_id: int
    recipient: str
    type: NotificationType
    status: NotificationStatus
    subject: Optional[str] = None
    brevo_message_id: Optional[str] = None
    error_message: Optional[str] = None
    scheduled_for: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    total: int
    logs: List[NotificationLogResponse]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/logs",
    response_model=NotificationListResponse,
    summary="List notification dispatch logs (Staff only)",
)
def list_notification_logs(
    appointment_id: Optional[int] = Query(None, description="Filter by appointment ID"),
    notification_type: Optional[NotificationType] = Query(None, alias="type", description="Filter by notification type"),
    status_filter: Optional[NotificationStatus] = Query(None, alias="status", description="Filter by delivery status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Clinic-wide audit log of all transactional emails dispatched via Brevo."""
    query = db.query(NotificationLog)

    if appointment_id:
        query = query.filter(NotificationLog.appointment_id == appointment_id)
    if notification_type:
        query = query.filter(NotificationLog.type == notification_type)
    if status_filter:
        query = query.filter(NotificationLog.status == status_filter)

    total = query.count()
    logs = query.order_by(NotificationLog.created_at.desc()).offset(skip).limit(limit).all()

    return NotificationListResponse(
        total=total,
        logs=[NotificationLogResponse.model_validate(l) for l in logs],
    )


@router.get(
    "/appointment/{appointment_id}",
    response_model=List[NotificationLogResponse],
    summary="Get notification logs for a specific appointment",
)
def get_appointment_notification_logs(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve all reminders and email dispatches for a specific appointment."""
    appt = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found.")

    is_staff = current_user.role in (UserRole.ADMIN, UserRole.SECRETARY, UserRole.DOCTOR, UserRole.ORTHODONTIST)
    if not is_staff and appt.patient_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    logs = (
        db.query(NotificationLog)
        .filter(NotificationLog.appointment_id == appointment_id)
        .order_by(NotificationLog.created_at.desc())
        .all()
    )
    return [NotificationLogResponse.model_validate(l) for l in logs]


@router.post(
    "/reminders/scan",
    summary="Trigger immediate appointment reminder scan (Secretary / Admin)",
)
def trigger_reminder_scan(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_secretary),
):
    """
    Manually triggers the background reminder scan:
    - Checks 24h (±15 min) and 2h (±10 min) appointment windows
    - Dispatches Brevo reminder emails with deduplication
    """
    summary = scan_and_send_reminders(db=db)
    return {
        "message": "Reminder scan completed successfully.",
        "summary": summary,
    }
