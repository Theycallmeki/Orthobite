from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Date,
    DateTime,
    Numeric,
    Enum,
    ForeignKey,
    Index,
    LargeBinary,
)
from sqlalchemy.orm import deferred, relationship
from sqlalchemy.sql import func
import enum
from config.database import Base


class PaymentMethod(str, enum.Enum):
    CASH = "Cash"
    GCASH = "GCash"
    CARD = "Card"
    BANK_TRANSFER = "Bank Transfer"


class TreatmentRecord(Base):
    """
    Digital treatment ledger entry replacing the physical paper book.
    Tracks clinical procedures, tooth numbers, cost, notes, and patient signature.
    """
    __tablename__ = "treatment_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    date = Column(Date, nullable=False, default=func.current_date(), index=True)
    treatment_name = Column(String(255), nullable=False, index=True)
    tooth_number = Column(String(100), nullable=True) 
    value_of_work = Column(Numeric(12, 2), default=0.00, nullable=False)
    signature_url = Column(String(500), nullable=True) 
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    patient = relationship("User", foreign_keys=[patient_id], backref="treatment_records")
    doctor = relationship("User", foreign_keys=[doctor_id], backref="doctor_treatments")
    payments = relationship(
        "Payment",
        back_populates="treatment_record",
        cascade="all, delete-orphan",
        order_by="Payment.payment_date.desc()",
    )

    __table_args__ = (
        Index("ix_treatment_records_patient_date", "patient_id", "date"),
    )


class Payment(Base):
    """
    Payment transaction recording downpayments, installments, or full settlement
    for a patient's treatment.
    """
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    treatment_record_id = Column(Integer, ForeignKey("treatment_records.id"), nullable=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), default=0.00, nullable=False)
    payment_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    method = Column(Enum(PaymentMethod), default=PaymentMethod.CASH, nullable=False)
    receipt_no = Column(String(100), nullable=True, index=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    treatment_record = relationship("TreatmentRecord", back_populates="payments")
    patient = relationship("User", foreign_keys=[patient_id], backref="patient_payments")
    capture = relationship(
        "PaymentCapture", back_populates="payment", uselist=False, lazy="selectin",
        cascade="all, delete-orphan",
    )

    @property
    def has_consent(self) -> bool:
        return self.capture is not None and self.capture.media_type is not None

    __table_args__ = (
        Index("ix_payments_patient_date", "patient_id", "payment_date"),
    )


class PaymentCapture(Base):
    __tablename__ = "payment_captures"

    request_id = Column(String(36), primary_key=True)
    payment_id = Column(Integer, ForeignKey("payments.id", ondelete="CASCADE"), nullable=False, unique=True)
    image_data = deferred(Column(LargeBinary))
    media_type = Column(String(30))
    reused_from_payment_id = Column(Integer)
    payment = relationship("Payment", back_populates="capture")
