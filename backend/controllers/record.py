import base64
import os
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from config.settings import settings
from models.record import Payment, PaymentMethod, TreatmentRecord
from models.users import User, UserRole
from schemas.record import (
    PatientLedgerSummary,
    PaymentCreate,
    PaymentResponse,
    ToothChartTemplateResponse,
    ToothMetadata,
    TreatmentRecordCreate,
    TreatmentRecordResponse,
    TreatmentRecordUpdate,
)


# ---------------------------------------------------------------------------
# Dynamic Ledger Calculations (Zero-Drift Financial Mathematics)
# ---------------------------------------------------------------------------

TWO_PLACES = Decimal("0.01")


def _quantize_money(val: Any) -> Decimal:
    """Ensure consistent 2-decimal place precision."""
    if val is None:
        return Decimal("0.00")
    if not isinstance(val, Decimal):
        val = Decimal(str(val))
    return val.quantize(TWO_PLACES)


def get_patient_user_or_404(db: Session, patient_id: int) -> User:
    """Retrieve patient user or raise 404."""
    user = db.query(User).filter(User.id == patient_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient user with ID {patient_id} does not exist.",
        )
    return user


def compute_treatment_record_response(
    record: TreatmentRecord, payments: Optional[List[Payment]] = None
) -> TreatmentRecordResponse:
    """
    Format a single treatment record with dynamically calculated total_paid
    and remaining balance for that specific procedure.
    """
    if payments is None:
        record_payments = record.payments or []
    else:
        record_payments = [p for p in payments if p.treatment_record_id == record.id]

    val_of_work = _quantize_money(record.value_of_work)
    paid = _quantize_money(sum((p.amount for p in record_payments), Decimal("0.00")))
    bal = _quantize_money(val_of_work - paid)

    payment_responses = [PaymentResponse.model_validate(p) for p in record_payments]

    return TreatmentRecordResponse(
        id=record.id,
        patient_id=record.patient_id,
        patient_name=record.patient.full_name if record.patient else None,
        doctor_id=record.doctor_id,
        doctor_name=record.doctor.full_name if record.doctor else None,
        date=record.date,
        treatment_name=record.treatment_name,
        tooth_number=record.tooth_number,
        value_of_work=val_of_work,
        total_paid=paid,
        balance=bal,
        signature_url=record.signature_url,
        notes=record.notes,
        created_at=record.created_at,
        updated_at=record.updated_at,
        payments=payment_responses,
    )


def compute_patient_ledger_summary(db: Session, patient_id: int) -> PatientLedgerSummary:
    """
    Calculates dynamic ledger balances on the fly across all treatments and payments.
    Prevents balance drift by aggregating directly from raw financial transactions.
    """
    patient = get_patient_user_or_404(db, patient_id)

    treatments = (
        db.query(TreatmentRecord)
        .filter(TreatmentRecord.patient_id == patient_id)
        .order_by(TreatmentRecord.date.desc(), TreatmentRecord.id.desc())
        .all()
    )

    all_payments = (
        db.query(Payment)
        .filter(Payment.patient_id == patient_id)
        .order_by(Payment.payment_date.desc(), Payment.id.desc())
        .all()
    )

    # Calculate exact dynamic sums
    total_val = _quantize_money(sum((t.value_of_work for t in treatments), Decimal("0.00")))
    total_paid = _quantize_money(sum((p.amount for p in all_payments), Decimal("0.00")))
    balance_due = _quantize_money(total_val - total_paid)

    treatment_responses = [
        compute_treatment_record_response(t, all_payments) for t in treatments
    ]
    payment_responses = [PaymentResponse.model_validate(p) for p in all_payments]

    return PatientLedgerSummary(
        patient_id=patient.id,
        patient_name=patient.full_name,
        patient_email=patient.email,
        patient_phone=patient.phone,
        treatments=treatment_responses,
        all_payments=payment_responses,
        total_value_of_work=total_val,
        total_amount_paid=total_paid,
        balance_due=balance_due,
    )


# ---------------------------------------------------------------------------
# Signature Storage Engine
# ---------------------------------------------------------------------------

def save_signature_base64(signature_data: str) -> str:
    """
    Decodes base64 PNG signature string from frontend canvas and saves to disk.
    Returns the relative public URL path.
    """
    if not signature_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Signature data cannot be empty.",
        )

    # Strip header if data URI format (e.g. data:image/png;base64,...)
    if "," in signature_data:
        _, base64_str = signature_data.split(",", 1)
    else:
        base64_str = signature_data

    try:
        decoded_bytes = base64.b64decode(base64_str)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid base64 signature encoding: {e}",
        )

    os.makedirs(settings.SIGNATURES_DIR, exist_ok=True)
    filename = f"sig_{uuid.uuid4().hex}.png"
    filepath = os.path.join(settings.SIGNATURES_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(decoded_bytes)

    # Return static web path
    return f"/{settings.SIGNATURES_DIR}/{filename}".replace("\\", "/")


async def save_signature_file(file: UploadFile) -> str:
    """Saves uploaded multipart signature image file to disk."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded signature has no filename.")

    ext = os.path.splitext(file.filename)[1].lower() or ".png"
    os.makedirs(settings.SIGNATURES_DIR, exist_ok=True)
    filename = f"sig_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(settings.SIGNATURES_DIR, filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    return f"/{settings.SIGNATURES_DIR}/{filename}".replace("\\", "/")


# ---------------------------------------------------------------------------
# Treatment Records CRUD
# ---------------------------------------------------------------------------

def create_treatment_record(db: Session, data: TreatmentRecordCreate) -> TreatmentRecordResponse:
    """Creates a new digital treatment entry in the patient ledger."""
    # Validate patient
    get_patient_user_or_404(db, data.patient_id)

    # Validate doctor if provided
    if data.doctor_id is not None:
        doctor = db.query(User).filter(User.id == data.doctor_id).first()
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Doctor user with ID {data.doctor_id} not found.",
            )

    sig_url = data.signature_url
    if data.signature_base64:
        sig_url = save_signature_base64(data.signature_base64)

    record_date = data.date or date.today()

    record = TreatmentRecord(
        patient_id=data.patient_id,
        doctor_id=data.doctor_id,
        date=record_date,
        treatment_name=data.treatment_name.strip(),
        tooth_number=data.tooth_number.strip() if data.tooth_number else None,
        value_of_work=_quantize_money(data.value_of_work),
        signature_url=sig_url,
        notes=data.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return compute_treatment_record_response(record)


def get_treatment_record_or_404(db: Session, record_id: int) -> TreatmentRecord:
    record = db.query(TreatmentRecord).filter(TreatmentRecord.id == record_id).first()
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Treatment record with ID {record_id} not found.",
        )
    return record


def update_treatment_record(
    db: Session, record_id: int, data: TreatmentRecordUpdate
) -> TreatmentRecordResponse:
    """Updates an existing treatment record entry."""
    record = get_treatment_record_or_404(db, record_id)

    if data.treatment_name is not None:
        record.treatment_name = data.treatment_name.strip()
    if data.tooth_number is not None:
        record.tooth_number = data.tooth_number.strip()
    if data.value_of_work is not None:
        record.value_of_work = _quantize_money(data.value_of_work)
    if data.doctor_id is not None:
        doctor = db.query(User).filter(User.id == data.doctor_id).first()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor user not found.")
        record.doctor_id = data.doctor_id
    if data.date is not None:
        record.date = data.date
    if data.notes is not None:
        record.notes = data.notes
    if data.signature_url is not None:
        record.signature_url = data.signature_url
    if data.signature_base64:
        record.signature_url = save_signature_base64(data.signature_base64)

    db.commit()
    db.refresh(record)
    return compute_treatment_record_response(record)


def delete_treatment_record(db: Session, record_id: int) -> Dict[str, Any]:
    record = get_treatment_record_or_404(db, record_id)
    db.delete(record)
    db.commit()
    return {"message": f"Treatment record {record_id} deleted successfully."}


# ---------------------------------------------------------------------------
# Payment Transactions CRUD
# ---------------------------------------------------------------------------

def create_payment(
    db: Session, data: PaymentCreate, record_id_param: Optional[int] = None
) -> PaymentResponse:
    """
    Records downpayment, installment, or balance settlement.
    Links to a specific treatment record and patient.
    """
    treatment_id = record_id_param or data.treatment_record_id
    patient_id = data.patient_id

    treatment_record = None
    if treatment_id is not None:
        treatment_record = get_treatment_record_or_404(db, treatment_id)
        if patient_id is None:
            patient_id = treatment_record.patient_id
        elif patient_id != treatment_record.patient_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Patient ID {patient_id} does not match Treatment Record owner ({treatment_record.patient_id}).",
            )

    if patient_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="patient_id must be provided or inferred from treatment_record_id.",
        )

    # Validate patient exists
    get_patient_user_or_404(db, patient_id)

    payment = Payment(
        treatment_record_id=treatment_id,
        patient_id=patient_id,
        amount=_quantize_money(data.amount),
        payment_date=data.payment_date or datetime.now(),
        method=data.method,
        receipt_no=data.receipt_no.strip() if data.receipt_no else None,
        notes=data.notes,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return PaymentResponse.model_validate(payment)


def get_payment_or_404(db: Session, payment_id: int) -> Payment:
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment with ID {payment_id} not found.",
        )
    return payment


# ---------------------------------------------------------------------------
# Rectangular Tooth Template Metadata Engine
# ---------------------------------------------------------------------------

# Universal (1-32) to FDI mapping table & anatomical specifications
TOOTH_DEFINITIONS = [
    # Upper Arch: Patient Right to Left (Universal 1 to 16)
    (1, 18, "Maxillary Right Third Molar (Wisdom)", "upper", "upper_right", "molar", 0, 0),
    (2, 17, "Maxillary Right Second Molar", "upper", "upper_right", "molar", 0, 1),
    (3, 16, "Maxillary Right First Molar", "upper", "upper_right", "molar", 0, 2),
    (4, 15, "Maxillary Right Second Premolar", "upper", "upper_right", "premolar", 0, 3),
    (5, 14, "Maxillary Right First Premolar", "upper", "upper_right", "premolar", 0, 4),
    (6, 13, "Maxillary Right Canine", "upper", "upper_right", "canine", 0, 5),
    (7, 12, "Maxillary Right Lateral Incisor", "upper", "upper_right", "incisor", 0, 6),
    (8, 11, "Maxillary Right Central Incisor", "upper", "upper_right", "incisor", 0, 7),
    (9, 21, "Maxillary Left Central Incisor", "upper", "upper_left", "incisor", 0, 8),
    (10, 22, "Maxillary Left Lateral Incisor", "upper", "upper_left", "incisor", 0, 9),
    (11, 23, "Maxillary Left Canine", "upper", "upper_left", "canine", 0, 10),
    (12, 24, "Maxillary Left First Premolar", "upper", "upper_left", "premolar", 0, 11),
    (13, 25, "Maxillary Left Second Premolar", "upper", "upper_left", "premolar", 0, 12),
    (14, 26, "Maxillary Left First Molar", "upper", "upper_left", "molar", 0, 13),
    (15, 27, "Maxillary Left Second Molar", "upper", "upper_left", "molar", 0, 14),
    (16, 28, "Maxillary Left Third Molar (Wisdom)", "upper", "upper_left", "molar", 0, 15),

    # Lower Arch: Patient Right to Left (Universal 32 down to 17)
    # Aligned vertically under the corresponding upper tooth
    (32, 48, "Mandibular Right Third Molar (Wisdom)", "lower", "lower_right", "molar", 1, 0),
    (31, 47, "Mandibular Right Second Molar", "lower", "lower_right", "molar", 1, 1),
    (30, 46, "Mandibular Right First Molar", "lower", "lower_right", "molar", 1, 2),
    (29, 45, "Mandibular Right Second Premolar", "lower", "lower_right", "premolar", 1, 3),
    (28, 44, "Mandibular Right First Premolar", "lower", "lower_right", "premolar", 1, 4),
    (27, 43, "Mandibular Right Canine", "lower", "lower_right", "canine", 1, 5),
    (26, 42, "Mandibular Right Lateral Incisor", "lower", "lower_right", "incisor", 1, 6),
    (25, 41, "Mandibular Right Central Incisor", "lower", "lower_right", "incisor", 1, 7),
    (24, 31, "Mandibular Left Central Incisor", "lower", "lower_left", "incisor", 1, 8),
    (23, 32, "Mandibular Left Lateral Incisor", "lower", "lower_left", "incisor", 1, 9),
    (22, 33, "Mandibular Left Canine", "lower", "lower_left", "canine", 1, 10),
    (21, 34, "Mandibular Left First Premolar", "lower", "lower_left", "premolar", 1, 11),
    (20, 35, "Mandibular Left Second Premolar", "lower", "lower_left", "premolar", 1, 12),
    (19, 36, "Mandibular Left First Molar", "lower", "lower_left", "molar", 1, 13),
    (18, 37, "Mandibular Left Second Molar", "lower", "lower_left", "molar", 1, 14),
    (17, 38, "Mandibular Left Third Molar (Wisdom)", "lower", "lower_left", "molar", 1, 15),
]


def generate_tooth_chart_template() -> ToothChartTemplateResponse:
    """
    Generates rectangular coordinate and layout metadata for the 32 adult permanent teeth.
    Allows frontend SVG/Canvas components to highlight individual teeth, multi-tooth
    bridges, and quadrant procedures cleanly.
    """
    cell_width = 56.0
    cell_height = 80.0
    col_gap = 6.0
    arch_gap = 36.0
    padding_x = 20.0
    padding_y = 20.0

    teeth_metadata: List[ToothMetadata] = []

    for item in TOOTH_DEFINITIONS:
        tooth_id, fdi, name, arch, quad, t_type, row, col = item
        x_pos = padding_x + col * (cell_width + col_gap)
        y_pos = padding_y + row * (cell_height + arch_gap)

        teeth_metadata.append(
            ToothMetadata(
                id=tooth_id,
                fdi_number=fdi,
                name=name,
                arch=arch,
                quadrant=quad,
                type=t_type,
                row=row,
                col=col,
                x=round(x_pos, 2),
                y=round(y_pos, 2),
                width=cell_width,
                height=cell_height,
            )
        )

    total_width = padding_x * 2 + 16 * cell_width + 15 * col_gap
    total_height = padding_y * 2 + 2 * cell_height + arch_gap

    upper = [t for t in teeth_metadata if t.arch == "upper"]
    lower = [t for t in teeth_metadata if t.arch == "lower"]

    return ToothChartTemplateResponse(
        system="Universal Numbering System & FDI Notation",
        layout="Dual-Arch Rectangular Grid Matrix (16x2)",
        total_teeth=32,
        canvas_dimensions={
            "viewBox_width": round(total_width, 2),
            "viewBox_height": round(total_height, 2),
            "cell_width": cell_width,
            "cell_height": cell_height,
            "arch_gap": arch_gap,
            "col_gap": col_gap,
        },
        upper_arch=upper,
        lower_arch=lower,
        teeth=teeth_metadata,
    )
