import enum

from sqlalchemy import Column, Integer, String, DateTime, Enum, JSON, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from config.database import Base


class AuditAction(str, enum.Enum):
    CREATE = "CREATE"
    READ   = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN  = "LOGIN"
    LOGIN_FAILED = "LOGIN_FAILED"


class AuditLog(Base):
    """
    Immutable audit trail for Data Privacy Act of 2012 compliance.
    Every sensitive read/write on clinical and financial data is recorded here.
    Records must never be edited — only appended or purged after the
    minimum legal retention period.
    """
    __tablename__ = "audit_logs"

    id          = Column(Integer, primary_key=True, index=True)

    # Who performed the action (nullable for anonymous / failed logins)
    actor_id    = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # What they did
    action      = Column(Enum(AuditAction), nullable=False, index=True)

    # What resource was accessed
    resource    = Column(String(100), nullable=False, index=True)   # e.g. "treatment_record"
    resource_id = Column(Integer, nullable=True)                    # affected row PK

    # Network context
    ip_address  = Column(String(45), nullable=True)                 # IPv4/IPv6

    # Optional extra payload (e.g. changed fields, error message)
    extra       = Column(JSON, nullable=True)

    # Always server-stamped — no client control
    timestamp   = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships (read-only convenience)
    actor = relationship("User", foreign_keys=[actor_id])

