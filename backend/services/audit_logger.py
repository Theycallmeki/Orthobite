"""
audit_logger.py — Thin, fire-and-forget audit event recorder.

Call `log_event()` from any controller to append an immutable audit entry.
The function intentionally never raises — a logging failure must NEVER
break the primary business operation.
"""
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from models.audit import AuditAction, AuditLog

logger = logging.getLogger("orthobite.audit")


def log_event(
    db:          Session,
    action:      AuditAction,
    resource:    str,
    actor_id:    Optional[int] = None,
    resource_id: Optional[int] = None,
    ip_address:  Optional[str] = None,
    extra:       Optional[Dict[str, Any]] = None,
) -> None:
    """
    Append a single audit entry to the database.

    Parameters
    ----------
    db          : Active SQLAlchemy session (must be open/un-committed).
    action      : AuditAction enum value (CREATE, READ, UPDATE, DELETE, LOGIN, …).
    resource    : Human-readable resource name, e.g. ``"treatment_record"``.
    actor_id    : User ID of the authenticated actor; None for anonymous events.
    resource_id : Primary key of the affected row; None for list/login events.
    ip_address  : Client IP from ``Request.client.host``.
    extra       : Any JSON-serialisable dict for additional context.
    """
    try:
        entry = AuditLog(
            actor_id=actor_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            ip_address=ip_address,
            extra=extra,
        )
        db.add(entry)
        db.commit()
    except Exception as exc:                    
        logger.error("audit_logger: failed to write audit entry — %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
