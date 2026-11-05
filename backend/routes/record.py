from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

import controllers.record as record_controller
from config.database import get_db
from dependencies import get_current_user, require_staff
from models.patient import Patient
from models.users import User, UserRole
from schemas.record import (
    PatientLedgerSummary,
    PaymentCreate,
    PaymentResponse,
    SignatureUploadRequest,
    SignatureUploadResponse,
    ToothChartTemplateResponse,
    TreatmentRecordCreate,
    TreatmentRecordResponse,
    TreatmentRecordUpdate,
)

router = APIRouter(prefix="/records", tags=["Treatment Records & Financial Ledger"])


@router.get(
    "/tooth-chart/template",
    response_model=ToothChartTemplateResponse,
    summary="Get rectangular tooth chart layout metadata",
)
def get_tooth_chart_template():
    """
    Serves rectangular tooth chart coordinate metadata and layout schema
    for the 32 adult permanent teeth (Universal & FDI systems).
    Used by frontend highlighters to map and visualize procedures on teeth.
    """
    return record_controller.generate_tooth_chart_template()


@router.post(
    "/signature/upload",
    response_model=SignatureUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload patient signature PNG (Base64)",
)
def upload_signature_base64(
    payload: SignatureUploadRequest,
    _: User = Depends(get_current_user),
):
    """Saves a base64 encoded signature PNG and returns the static URL path."""
    url = record_controller.save_signature_base64(payload.signature_base64)
    return SignatureUploadResponse(signature_url=url)


@router.post(
    "/signature/upload-file",
    response_model=SignatureUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload patient signature image file (Multipart)",
)
async def upload_signature_file(
    file: UploadFile = File(...),
    _: User = Depends(get_current_user),
):
    """Accepts a multipart file upload for signatures."""
    url = await record_controller.save_signature_file(file)
    return SignatureUploadResponse(signature_url=url)


# ---------------------------------------------------------------------------
# Treatment Records (Staff Only for creation & modification)
# ---------------------------------------------------------------------------

@router.post(
    "/",
    response_model=TreatmentRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add treatment record entry (Staff only)",
)
def create_treatment_record(
    data: TreatmentRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Adds a new clinical procedure entry to the patient's digital treatment ledger.
    Captures procedure name, tooth number(s), agreed value of work, and patient signature.
    """
    if data.doctor_id is None and current_user.role in (UserRole.DOCTOR, UserRole.ORTHODONTIST):
        data.doctor_id = current_user.id

    return record_controller.create_treatment_record(db, data)


@router.get(
    "/{record_id}",
    response_model=TreatmentRecordResponse,
    summary="Get treatment record details",
)
def get_treatment_record(
    record_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieves full details of a specific treatment record including payment installments.
    Accessible by clinic staff or the owning patient.
    """
    record = record_controller.get_treatment_record_or_404(db, record_id)
    is_staff = current_user.role in (
        UserRole.ADMIN,
        UserRole.DOCTOR,
        UserRole.ORTHODONTIST,
        UserRole.SECRETARY,
    )
    if not is_staff and record.patient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this treatment record.",
        )

    return record_controller.compute_treatment_record_response(record)


@router.patch(
    "/{record_id}",
    response_model=TreatmentRecordResponse,
    summary="Update treatment record (Staff only)",
)
def update_treatment_record(
    record_id: int,
    data: TreatmentRecordUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Update procedure details, tooth number, value of work, or signature."""
    return record_controller.update_treatment_record(db, record_id, data)


@router.delete(
    "/{record_id}",
    summary="Delete treatment record (Staff only)",
)
def delete_treatment_record(
    record_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Delete a treatment record from the ledger."""
    return record_controller.delete_treatment_record(db, record_id)



@router.post(
    "/{record_id}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record payment for a specific treatment record (Staff only)",
)
def create_payment_for_record(
    record_id: int,
    data: PaymentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """
    Records downpayment or installment linked directly to a treatment record.
    Immediately reduces remaining balance for that procedure.
    """
    return record_controller.create_payment(db, data, record_id_param=record_id)


@router.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record general payment (Staff only)",
)
def create_general_payment(
    data: PaymentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Records a general payment or downpayment for a patient."""
    return record_controller.create_payment(db, data)


@router.get(
    "/payments/{payment_id}",
    response_model=PaymentResponse,
    summary="Get payment details",
)
def get_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve details of a payment transaction."""
    payment = record_controller.get_payment_or_404(db, payment_id)
    is_staff = current_user.role in (
        UserRole.ADMIN,
        UserRole.DOCTOR,
        UserRole.ORTHODONTIST,
        UserRole.SECRETARY,
    )
    if not is_staff and payment.patient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this payment.",
        )
    return PaymentResponse.model_validate(payment)



@router.get(
    "/patient/{patient_id}/ledger",
    response_model=PatientLedgerSummary,
    summary="Get patient financial ledger summary",
)
def get_patient_ledger(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Computes and returns the complete real-time financial ledger for a patient.
    Aggregates all treatment rows, payment installments, total value of work,
    total amount paid, and net balance due on the fly to prevent balance drift.
    """
    resolved_patient_id = patient_id
    patient_user = db.query(User).filter(User.id == patient_id).first()
    if not patient_user:
        patient_profile = db.query(Patient).filter(Patient.id == patient_id).first()
        if patient_profile and patient_profile.user_id:
            resolved_patient_id = patient_profile.user_id
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Patient with ID {patient_id} does not exist.",
            )

    is_staff = current_user.role in (
        UserRole.ADMIN,
        UserRole.DOCTOR,
        UserRole.ORTHODONTIST,
        UserRole.SECRETARY,
    )
    if not is_staff and resolved_patient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this patient's financial ledger.",
        )

    return record_controller.compute_patient_ledger_summary(db, resolved_patient_id)
