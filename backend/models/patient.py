from sqlalchemy import Column, Integer, String, Text, Date, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from config.database import Base


class TreatmentStage(str, enum.Enum):
    CONSULTATION = "consultation"
    SCANNING = "scanning"
    PLANNING = "planning"
    ACTIVE_TREATMENT = "active_treatment"
    RETENTION = "retention"
    COMPLETED = "completed"


class BiteType(str, enum.Enum):
    NORMAL = "normal"
    CLASS_I = "class_i"
    CLASS_II = "class_ii"
    CLASS_III = "class_iii"
    OPEN_BITE = "open_bite"
    CROSSBITE = "crossbite"
    DEEP_BITE = "deep_bite"


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True, index=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(String(20), nullable=True)
    phone = Column(String(50), nullable=True)
    address = Column(String(500), nullable=True)

    # Emergency Contact
    emergency_contact_name = Column(String(255), nullable=True)
    emergency_contact_phone = Column(String(50), nullable=True)

    # Clinical Records & History
    medical_history = Column(Text, nullable=True)
    dental_history = Column(Text, nullable=True)
    bite_type = Column(Enum(BiteType), default=BiteType.NORMAL, nullable=False)
    treatment_stage = Column(Enum(TreatmentStage), default=TreatmentStage.CONSULTATION, nullable=False)
    
    # Orthodontist Assignment
    assigned_doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    notes = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="patient_profile")
    assigned_doctor = relationship("User", foreign_keys=[assigned_doctor_id])
