from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.audit import AuditAction, AuditLog
from schemas.audit import AuditLogListResponse, AuditLogResponse, AuditPurgeResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_response(log: AuditLog) -> AuditLogResponse:
    return AuditLogResponse.model_validate(log)


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def list_audit_logs(
    db:          Session,
    actor_id:    Optional[int]          = None,
    action:      Optional[AuditAction]  = None,
    resource:    Optional[str]          = None,
    date_from:   Optional[datetime]     = None,
    date_to:     Optional[datetime]     = None,
    page:        int                    = 1,
    limit:       int                    = 50,
) -> AuditLogListResponse:
    """Paginated, filterable audit log listing (admin only)."""
    q = db.query(AuditLog)

    if actor_id is not None:
        q = q.filter(AuditLog.actor_id == actor_id)
    if action is not None:
        q = q.filter(AuditLog.action == action)
    if resource is not None:
        q = q.filter(AuditLog.resource == resource)
    if date_from is not None:
        q = q.filter(AuditLog.timestamp >= date_from)
    if date_to is not None:
        q = q.filter(AuditLog.timestamp <= date_to)

    total = q.count()
    logs  = (
        q.order_by(AuditLog.timestamp.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return AuditLogListResponse(
        total=total,
        page=page,
        limit=limit,
        items=[_to_response(l) for l in logs],
    )


def get_audit_log_or_404(db: Session, log_id: int) -> AuditLogResponse:
    log = db.query(AuditLog).filter(AuditLog.id == log_id).first()
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log entry {log_id} not found.",
        )
    return _to_response(log)


def purge_old_logs(db: Session, older_than_days: int = 365) -> AuditPurgeResponse:
    """
    Delete audit entries older than ``older_than_days`` days.
    Default retention: 365 days (DPA 2012 recommends at least 1 year).
    """
    if older_than_days < 30:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum purge window is 30 days to comply with data retention policy.",
        )

    cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
    deleted = (
        db.query(AuditLog)
        .filter(AuditLog.timestamp < cutoff)
        .delete(synchronize_session=False)
    )
    db.commit()

    return AuditPurgeResponse(
        deleted_count=deleted,
        cutoff_date=cutoff,
        message=f"Purged {deleted} audit log entries older than {older_than_days} days.",
    )

