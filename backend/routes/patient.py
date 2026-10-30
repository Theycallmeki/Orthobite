from typing import Optional
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session

import controllers.patient as patient_controller
from config.database import get_db
from dependencies import get_current_user, require_admin, require_staff
from models.patient import TreatmentStage
from models.users import User, UserRole
from schemas.patient import PatientCreate, PatientResponse, PatientUpdate

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.post(
    "/",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create patient clinical profile (Staff only)",
)
def create_patient(
    data: PatientCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Create a new patient clinical profile and record."""
    return patient_controller.create_patient(db, data)


@router.get(
    "/",
    response_model=list[PatientResponse],
    summary="List patient records (Staff only)",
)
def list_patients(
    skip: int = 0,
    limit: int = 100,
    stage: Optional[TreatmentStage] = None,
    doctor_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Retrieve list of patients with optional filtering by treatment stage or doctor."""
    return patient_controller.list_patients(
        db, skip=skip, limit=limit, stage=stage, doctor_id=doctor_id
    )


@router.get(
    "/me",
    response_model=PatientResponse,
    summary="Get current patient's clinical profile",
)
def get_my_patient_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve the clinical profile of the authenticated patient."""
    return patient_controller.get_patient_by_user_id(db, current_user.id)


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Get patient details by ID",
)
def get_patient_by_id(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve patient record by ID. Accessible by staff or the patient themselves."""
    patient = patient_controller.get_patient_or_404(db, patient_id)
    is_staff = current_user.role in (UserRole.ADMIN, UserRole.ORTHODONTIST, UserRole.SECRETARY)
    if not is_staff and patient.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this patient profile.",
        )
    return PatientResponse.model_validate(patient)


@router.patch(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Update patient record (Staff only)",
)
def update_patient(
    patient_id: int,
    data: PatientUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Update treatment stage, notes, or assigned orthodontist."""
    return patient_controller.update_patient(db, patient_id, data)


@router.delete(
    "/{patient_id}",
    summary="Delete patient record (Admin only)",
)
def delete_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Delete a patient record."""
    return patient_controller.delete_patient(db, patient_id)
