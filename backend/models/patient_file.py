from enum import Enum

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, LargeBinary, String, Text
from sqlalchemy import Enum as SqlEnum
from sqlalchemy.orm import deferred, relationship
from sqlalchemy.sql import func

from config.database import Base


class PatientFileFolder(str, Enum):
    XRAYS = "xrays"
    CONTRACTS_CONSENT = "contracts-consent"
    OTHER = "other"


class PatientFile(Base):
    __tablename__ = "patient_files"

    id = Column(Integer, primary_key=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False)
    folder = Column(SqlEnum(PatientFileFolder, native_enum=False, create_constraint=True), nullable=False)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    current_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True))
    deleted_by_id = Column(Integer, ForeignKey("users.id"))

    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])

    __table_args__ = (Index("ix_patient_files_patient_deleted", "patient_id", "deleted_at"),)


class PatientFileVersion(Base):
    __tablename__ = "patient_file_versions"

    file_id = Column(Integer, ForeignKey("patient_files.id", ondelete="CASCADE"), primary_key=True)
    number = Column(Integer, primary_key=True)
    media_type = Column(String(32), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    content = deferred(Column(LargeBinary, nullable=False))
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
