from datetime import date as py_date, datetime as py_datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

from models.record import PaymentMethod


# ---------------------------------------------------------------------------
# Payment Schemas
# ---------------------------------------------------------------------------

class PaymentCreate(BaseModel):
    treatment_record_id: Optional[int] = Field(
        None, description="Optional ID of specific treatment record this payment settles"
    )
    patient_id: Optional[int] = Field(
        None, description="Patient User ID. Inferred from treatment record if omitted"
    )
    amount: Decimal = Field(..., gt=0, description="Payment amount in Philippine Pesos (PHP)")
    payment_date: Optional[py_datetime] = Field(
        None, description="Payment timestamp; defaults to current time if omitted"
    )
    method: PaymentMethod = Field(PaymentMethod.CASH, description="Method: Cash, GCash, Card, Bank Transfer")
    receipt_no: Optional[str] = Field(None, max_length=100, description="Receipt or reference number")
    notes: Optional[str] = Field(None, description="Optional billing or cashier notes")


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    treatment_record_id: Optional[int] = None
    patient_id: int
    amount: Decimal
    payment_date: py_datetime
    method: PaymentMethod
    receipt_no: Optional[str] = None
    notes: Optional[str] = None
    created_at: py_datetime


# ---------------------------------------------------------------------------
# Treatment Record Schemas
# ---------------------------------------------------------------------------

class TreatmentRecordCreate(BaseModel):
    patient_id: int = Field(..., description="Target patient User ID")
    doctor_id: Optional[int] = Field(None, description="Doctor or Orthodontist User ID who performed treatment")
    date: Optional[py_date] = Field(None, description="Date of procedure; defaults to today")
    treatment_name: str = Field(..., min_length=1, max_length=255, description="Name of clinical procedure")
    tooth_number: Optional[str] = Field(
        None, max_length=100, description="Specific tooth number(s) (e.g. '14', '16-18', 'Universal 3')"
    )
    value_of_work: Decimal = Field(
        ..., ge=0, description="Agreed total monetary value / fee for this procedure"
    )
    signature_url: Optional[str] = Field(
        None, max_length=500, description="URL or relative path to captured patient signature PNG"
    )
    signature_base64: Optional[str] = Field(
        None, description="Base64 encoded PNG signature from frontend drawing canvas"
    )
    notes: Optional[str] = Field(None, description="Detailed clinical observations and doctor notes")


class TreatmentRecordUpdate(BaseModel):
    treatment_name: Optional[str] = Field(None, min_length=1, max_length=255)
    tooth_number: Optional[str] = Field(None, max_length=100)
    value_of_work: Optional[Decimal] = Field(None, ge=0)
    doctor_id: Optional[int] = None
    date: Optional[py_date] = None
    signature_url: Optional[str] = Field(None, max_length=500)
    signature_base64: Optional[str] = None
    notes: Optional[str] = None


class TreatmentRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    patient_id: int
    patient_name: Optional[str] = None
    doctor_id: Optional[int] = None
    doctor_name: Optional[str] = None
    date: py_date
    treatment_name: str
    tooth_number: Optional[str] = None
    value_of_work: Decimal
    total_paid: Decimal = Decimal("0.00")
    balance: Decimal = Decimal("0.00")
    signature_url: Optional[str] = None
    notes: Optional[str] = None
    created_at: py_datetime
    updated_at: Optional[py_datetime] = None
    payments: List[PaymentResponse] = []


# ---------------------------------------------------------------------------
# Patient Ledger Summary Schema
# ---------------------------------------------------------------------------

class PatientLedgerSummary(BaseModel):
    patient_id: int
    patient_name: str
    patient_email: Optional[str] = None
    patient_phone: Optional[str] = None
    treatments: List[TreatmentRecordResponse]
    all_payments: List[PaymentResponse]
    total_value_of_work: Decimal
    total_amount_paid: Decimal
    balance_due: Decimal


# ---------------------------------------------------------------------------
# Signature Schemas
# ---------------------------------------------------------------------------

class SignatureUploadRequest(BaseModel):
    signature_base64: str = Field(..., description="Base64 encoded data URI (data:image/png;base64,...)")


class SignatureUploadResponse(BaseModel):
    signature_url: str
    message: str = "Signature uploaded successfully."


# ---------------------------------------------------------------------------
# Rectangular Tooth Template Metadata Schemas
# ---------------------------------------------------------------------------

class ToothMetadata(BaseModel):
    id: int = Field(..., description="Universal Numbering System ID (1 to 32)")
    fdi_number: int = Field(..., description="FDI World Dental Federation Notation (11-48)")
    name: str = Field(..., description="Full anatomical tooth designation")
    arch: str = Field(..., description="'upper' (Maxillary) or 'lower' (Mandibular)")
    quadrant: str = Field(..., description="'upper_right', 'upper_left', 'lower_left', 'lower_right'")
    type: str = Field(..., description="'molar', 'premolar', 'canine', 'incisor'")
    row: int = Field(..., description="Grid row index (0 for upper, 1 for lower)")
    col: int = Field(..., description="Grid column index (0 to 15)")
    x: float = Field(..., description="SVG / Canvas relative X coordinate")
    y: float = Field(..., description="SVG / Canvas relative Y coordinate")
    width: float = Field(..., description="Rectangular width in SVG units")
    height: float = Field(..., description="Rectangular height in SVG units")


class ToothChartTemplateResponse(BaseModel):
    system: str
    layout: str
    total_teeth: int
    canvas_dimensions: Dict[str, float]
    upper_arch: List[ToothMetadata]
    lower_arch: List[ToothMetadata]
    teeth: List[ToothMetadata]
