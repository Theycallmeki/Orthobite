from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Enum,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from config.database import Base


class AppointmentStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False, index=True)
    start_time = Column(DateTime(timezone=True), nullable=False, index=True)
    end_time = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.PENDING, nullable=False, index=True)

    # Clinical & Administrative Details
    reason_for_visit = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    cancellation_reason = Column(String(500), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    patient = relationship("User", foreign_keys=[patient_id], backref="patient_appointments")
    doctor = relationship("DoctorProfile", foreign_keys=[doctor_id], backref="doctor_appointments")

    # Composite Index for high-performance conflict detection and schedule queries
    __table_args__ = (
        Index("ix_appointments_doctor_time_status", "doctor_id", "start_time", "end_time", "status"),
        Index("ix_appointments_patient_time_status", "patient_id", "start_time", "end_time", "status"),
    )
