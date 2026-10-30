from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.patient import Patient, TreatmentStage
from models.users import User
from schemas.patient import PatientCreate, PatientResponse, PatientUpdate


def get_patient_or_404(db: Session, patient_id: int) -> Patient:
    """Fetch patient by ID or raise 404."""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found.",
        )
    return patient


def create_patient(db: Session, data: PatientCreate) -> PatientResponse:
    """Create a new patient record."""
    if data.user_id is not None:
        user = db.query(User).filter(User.id == data.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Linked user with ID {data.user_id} does not exist.",
            )
        # Check if already exists for this user
        existing = db.query(Patient).filter(Patient.user_id == data.user_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A clinical profile already exists for this user.",
            )

    if data.assigned_doctor_id is not None:
        doctor = db.query(User).filter(User.id == data.assigned_doctor_id).first()
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assigned doctor with ID {data.assigned_doctor_id} does not exist.",
            )

    patient = Patient(
        user_id=data.user_id,
        date_of_birth=data.date_of_birth,
        gender=data.gender,
        phone=data.phone,
        address=data.address,
        emergency_contact_name=data.emergency_contact_name,
        emergency_contact_phone=data.emergency_contact_phone,
        medical_history=data.medical_history,
        dental_history=data.dental_history,
        bite_type=data.bite_type,
        treatment_stage=data.treatment_stage,
        assigned_doctor_id=data.assigned_doctor_id,
        notes=data.notes,
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return PatientResponse.model_validate(patient)


def get_patient_by_id(db: Session, patient_id: int) -> PatientResponse:
    """Retrieve patient record by ID."""
    patient = get_patient_or_404(db, patient_id)
    return PatientResponse.model_validate(patient)


def get_patient_by_user_id(db: Session, user_id: int) -> Optional[PatientResponse]:
    """Retrieve patient record associated with a user ID."""
    patient = db.query(Patient).filter(Patient.user_id == user_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No patient profile found for this user account.",
        )
    return PatientResponse.model_validate(patient)


def list_patients(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    stage: Optional[TreatmentStage] = None,
    doctor_id: Optional[int] = None,
) -> list[PatientResponse]:
    """List patients with optional stage and doctor filters."""
    query = db.query(Patient)
    if stage:
        query = query.filter(Patient.treatment_stage == stage)
    if doctor_id:
        query = query.filter(Patient.assigned_doctor_id == doctor_id)
    patients = query.order_by(Patient.created_at.desc()).offset(skip).limit(limit).all()
    return [PatientResponse.model_validate(p) for p in patients]


def update_patient(db: Session, patient_id: int, data: PatientUpdate) -> PatientResponse:
    """Update patient details and clinical history."""
    patient = get_patient_or_404(db, patient_id)

    update_dict = data.model_dump(exclude_unset=True)
    if "assigned_doctor_id" in update_dict and update_dict["assigned_doctor_id"] is not None:
        doctor = db.query(User).filter(User.id == update_dict["assigned_doctor_id"]).first()
        if not doctor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Assigned doctor {update_dict['assigned_doctor_id']} does not exist.",
            )

    for field, value in update_dict.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    return PatientResponse.model_validate(patient)


def delete_patient(db: Session, patient_id: int) -> dict:
    """Delete a patient record."""
    patient = get_patient_or_404(db, patient_id)
    db.delete(patient)
    db.commit()
    return {"message": f"Patient {patient_id} deleted successfully."}
