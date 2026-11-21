from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from sqlalchemy.orm import Session

import controllers.record as record_controller
from config.database import get_db
from dependencies import get_current_user, require_staff
from models.patient import Patient
from models.record import Payment
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
    return record_controller.generate_tooth_chart_template()


@router.post(
    "/signatures/upload",
    response_model=SignatureUploadResponse,
    summary="Upload patient signature image",
)
async def upload_signature(
    file: UploadFile = File(...),
    _: User = Depends(require_staff),
):
    url = await record_controller.save_signature_file(file)
    return SignatureUploadResponse(
        url=url,
        signature_url=url,
        filename=file.filename or "signature.png",
        content_type=file.content_type or "image/png",
    )


@router.post(
    "/signatures/base64",
    response_model=SignatureUploadResponse,
    summary="Save Base64 canvas signature",
)
def save_signature_base64_endpoint(
    payload: SignatureUploadRequest,
    _: User = Depends(require_staff),
):
    data_str = payload.signature_data or payload.signature_base64 or ""
    url = record_controller.save_signature_base64(data_str)
    return SignatureUploadResponse(
        url=url,
        signature_url=url,
        filename="signature.png",
        content_type="image/png",
    )


@router.post(
    "/",
    response_model=TreatmentRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add treatment record entry (Staff only)",
)
def create_treatment_record(
    data: TreatmentRecordCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    if data.doctor_id is None and current_user.role in (UserRole.DOCTOR, UserRole.ORTHODONTIST):
        data.doctor_id = current_user.id

    ip = request.client.host if request.client else None
    return record_controller.create_treatment_record(db, data, actor_id=current_user.id, ip_address=ip)


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
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    ip = request.client.host if request.client else None
    return record_controller.update_treatment_record(db, record_id, data, actor_id=current_user.id, ip_address=ip)


@router.delete(
    "/{record_id}",
    summary="Delete treatment record (Staff only)",
)
def delete_treatment_record(
    record_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    ip = request.client.host if request.client else None
    return record_controller.delete_treatment_record(db, record_id, actor_id=current_user.id, ip_address=ip)


def _validate_payment_consent(data: PaymentCreate, user: User) -> None:
    has_new = data.consent_signature_base64 is not None
    has_saved = data.reuse_consent_payment_id is not None
    if not has_new and not has_saved:
        return
    if user.role != UserRole.SECRETARY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only a secretary can collect consent at payment.")
    if (has_new and has_saved) or data.payment_request_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Choose one signature option and include a payment request ID.")
    if has_saved and not data.reuse_consent_confirmed:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Confirm the patient agrees to reuse their signature for this payment.")


@router.post(
    "/{record_id}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record payment for a specific treatment record (Staff only)",
)
def create_payment_for_record(
    record_id: int,
    data: PaymentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    _validate_payment_consent(data, current_user)
    ip = request.client.host if request.client else None
    return record_controller.create_payment(db, data, record_id_param=record_id, actor_id=current_user.id, ip_address=ip)


@router.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record general payment (Staff only)",
)
def create_general_payment(
    data: PaymentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    _validate_payment_consent(data, current_user)
    ip = request.client.host if request.client else None
    return record_controller.create_payment(db, data, actor_id=current_user.id, ip_address=ip)


def _get_accessible_payment(
    payment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Payment:
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
    return payment


@router.get(
    "/payments/{payment_id}",
    response_model=PaymentResponse,
    summary="Get payment details",
)
def get_payment(payment: Payment = Depends(_get_accessible_payment)):
    return PaymentResponse.model_validate(payment)


@router.get("/payments/{payment_id}/consent", summary="View the patient's signed payment consent")
def get_payment_consent(payment: Payment = Depends(_get_accessible_payment)):
    if not payment.has_consent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No consent was captured for this payment.")
    return Response(
        content=payment.capture.image_data,
        media_type=payment.capture.media_type,
        headers={"Cache-Control": "private, no-store"},
    )


@router.get(
    "/patient/{patient_id}/ledger",
    response_model=PatientLedgerSummary,
    summary="Get patient financial ledger summary",
)
def get_patient_ledger(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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

    ip = request.client.host if request.client else None
    return record_controller.compute_patient_ledger_summary(db, resolved_patient_id, actor_id=current_user.id, ip_address=ip)
