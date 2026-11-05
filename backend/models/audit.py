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


    actor_id    = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)


    action      = Column(Enum(AuditAction), nullable=False, index=True)


    resource    = Column(String(100), nullable=False, index=True)                            
    resource_id = Column(Integer, nullable=True)                                     


    ip_address  = Column(String(45), nullable=True)                            


    extra       = Column(JSON, nullable=True)


    timestamp   = Column(DateTime(timezone=True), server_default=func.now(), index=True)


    actor = relationship("User", foreign_keys=[actor_id])
