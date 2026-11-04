from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

import controllers.audit as audit_controller
from config.database import get_db
from dependencies import require_admin
from models.audit import AuditAction
from models.users import User
from schemas.audit import AuditLogListResponse, AuditLogResponse, AuditPurgeResponse

router = APIRouter(prefix="/admin/audit", tags=["Audit Logs (Admin)"])


@router.get(
    "/logs",
    response_model=AuditLogListResponse,
    summary="List audit logs with filters (Admin only)",
)
def list_logs(
    actor_id:  Optional[int]         = Query(None, description="Filter by actor user ID"),
    action:    Optional[AuditAction] = Query(None, description="Filter by action type"),
    resource:  Optional[str]         = Query(None, description="Filter by resource name"),
    date_from: Optional[datetime]    = Query(None, description="Start of date range (ISO 8601)"),
    date_to:   Optional[datetime]    = Query(None, description="End of date range (ISO 8601)"),
    page:      int                   = Query(1, ge=1),
    limit:     int                   = Query(50, ge=1, le=200),
    db:        Session               = Depends(get_db),
    _:         User                  = Depends(require_admin),
):
    """
    Paginated audit log. Filter by actor, action type, resource, or date range.
    Use this to satisfy DPA 2012 audit trail requirements.
    """
    return audit_controller.list_audit_logs(
        db=db,
        actor_id=actor_id,
        action=action,
        resource=resource,
        date_from=date_from,
        date_to=date_to,
        page=page,
        limit=limit,
    )


@router.get(
    "/logs/{log_id}",
    response_model=AuditLogResponse,
    summary="Get single audit log entry (Admin only)",
)
def get_log(
    log_id: int,
    db:     Session = Depends(get_db),
    _:      User    = Depends(require_admin),
):
    """Retrieve a specific audit log entry by ID."""
    return audit_controller.get_audit_log_or_404(db, log_id)


@router.delete(
    "/purge",
    response_model=AuditPurgeResponse,
    status_code=status.HTTP_200_OK,
    summary="Purge old audit logs (Admin only)",
)
def purge_logs(
    older_than_days: int     = Query(365, ge=30, description="Delete entries older than N days (min 30)"),
    db:              Session = Depends(get_db),
    _:               User    = Depends(require_admin),
):
    """
    Permanently delete audit log entries older than the specified number of days.
    Minimum 30 days to comply with data retention policy.
    Default: 365 days (DPA 2012 recommended minimum).
    """
    return audit_controller.purge_old_logs(db, older_than_days)

