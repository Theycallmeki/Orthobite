from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.patient import Patient, TreatmentStage
from models.patient_file import PatientFile
from models.users import User, UserRole
from schemas.patient import PatientCreate, PatientResponse, PatientUpdate


def get_patient_or_404(db: Session, patient_id: int, *, lock: bool = False) -> Patient:
    """Fetch patient by ID or raise 404."""
    query = db.query(Patient).filter(Patient.id == patient_id)
    if lock:
        # SQLite ignores FOR UPDATE. Acquire the write lock before checking the patient.
        if db.get_bind().dialect.name == "sqlite":
            db.connection().exec_driver_sql("BEGIN IMMEDIATE")
        query = query.with_for_update().populate_existing()
    patient = query.first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID {patient_id} not found.",
        )
    return patient


def validate_doctor_assignment(db: Session, doctor_id: int | None, actor: User) -> None:
    if actor.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only administrators can change doctor assignments.")
    if doctor_id is None:
        return

    doctor = db.get(User, doctor_id)
    if doctor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Assigned doctor with ID {doctor_id} does not exist.")
    if doctor.role not in (UserRole.DOCTOR, UserRole.ORTHODONTIST) or not doctor.is_active:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Assign an active doctor or orthodontist.")


def create_patient(db: Session, data: PatientCreate, actor: User) -> PatientResponse:
    """Create a new patient record."""
    if data.user_id is not None:
        user = db.query(User).filter(User.id == data.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Linked user with ID {data.user_id} does not exist.",
            )

        existing = db.query(Patient).filter(Patient.user_id == data.user_id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A clinical profile already exists for this user.",
            )

    if data.assigned_doctor_id is not None:
        validate_doctor_assignment(db, data.assigned_doctor_id, actor)

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
    patients = query.order_by(Patient.created_at.desc(), Patient.id.desc()).offset(skip).limit(limit).all()
    return [PatientResponse.model_validate(p) for p in patients]


def update_patient(db: Session, patient_id: int, data: PatientUpdate, actor: User) -> PatientResponse:
    """Update patient details and clinical history."""
    patient = get_patient_or_404(db, patient_id)

    update_dict = data.model_dump(exclude_unset=True)
    if "assigned_doctor_id" in update_dict:
        validate_doctor_assignment(db, data.assigned_doctor_id, actor)

    for field, value in update_dict.items():
        setattr(patient, field, value)

    db.commit()
    db.refresh(patient)
    return PatientResponse.model_validate(patient)


def delete_patient(db: Session, patient_id: int) -> dict:
    """Delete a patient record."""
    patient = get_patient_or_404(db, patient_id, lock=True)
    if db.query(PatientFile.id).filter(PatientFile.patient_id == patient_id).first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This profile has retained patient files and cannot be deleted.")
    db.delete(patient)
    db.commit()
    return {"message": f"Patient {patient_id} deleted successfully."}
