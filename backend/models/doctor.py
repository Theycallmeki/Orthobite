from sqlalchemy import Column, Integer, String, Text, Boolean, Numeric, DateTime, Time, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from config.database import Base


class DoctorProfile(Base):
    __tablename__ = "doctor_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    specialty = Column(String(100), default="Orthodontics", nullable=False)
    bio = Column(Text, nullable=True)
    photo_url = Column(String(500), nullable=True)
    years_of_experience = Column(Integer, default=0, nullable=False)
    education = Column(String(255), nullable=True)
    consultation_fee = Column(Numeric(10, 2), default=0.00, nullable=False)
    is_accepting_patients = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="doctor_profile")
    availability_rules = relationship("AvailabilityRule", back_populates="doctor", cascade="all, delete-orphan")
    time_off_records = relationship("TimeOff", back_populates="doctor", cascade="all, delete-orphan")


class AvailabilityRule(Base):
    """Recurring weekly availability rule (e.g., Mondays 09:00 - 17:00, 30 min slots)."""
    __tablename__ = "availability_rules"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False, index=True)
    day_of_week = Column(Integer, nullable=False)  # 0 = Monday, 1 = Tuesday, ..., 6 = Sunday
    start_time = Column(Time, nullable=False)      # e.g., 09:00:00
    end_time = Column(Time, nullable=False)        # e.g., 17:00:00
    slot_duration_minutes = Column(Integer, default=30, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    doctor = relationship("DoctorProfile", back_populates="availability_rules")


class TimeOff(Base):
    """Doctor leave, holidays, or blocked-out date/time ranges."""
    __tablename__ = "time_off"

    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctor_profiles.id"), nullable=False, index=True)
    start_datetime = Column(DateTime(timezone=True), nullable=False)
    end_datetime = Column(DateTime(timezone=True), nullable=False)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    doctor = relationship("DoctorProfile", back_populates="time_off_records")
