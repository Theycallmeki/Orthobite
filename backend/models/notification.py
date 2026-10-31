from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from config.database import Base


class NotificationType(str, enum.Enum):
    BOOKING_CONFIRMATION = "booking_confirmation"
    CANCELLATION_NOTICE = "cancellation_notice"
    REMINDER_24H = "reminder_24h"
    REMINDER_2H = "reminder_2h"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    SIMULATED = "simulated"


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=False, index=True)
    recipient = Column(String(255), nullable=False, index=True)
    type = Column(Enum(NotificationType), nullable=False, index=True)
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING, nullable=False, index=True)
    
    subject = Column(String(255), nullable=True)
    brevo_message_id = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    scheduled_for = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    appointment = relationship("Appointment", foreign_keys=[appointment_id], backref="notification_logs")

    # Composite index for fast deduplication lookups
    __table_args__ = (
        Index("ix_notification_logs_appt_type_status", "appointment_id", "type", "status"),
    )
