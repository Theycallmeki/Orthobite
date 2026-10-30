from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
from models.patient import TreatmentStage, BiteType
from schemas.user import UserResponse


class PatientBase(BaseModel):
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=20)
    phone: Optional[str] = Field(None, max_length=50)
    address: Optional[str] = Field(None, max_length=500)
    emergency_contact_name: Optional[str] = Field(None, max_length=255)
    emergency_contact_phone: Optional[str] = Field(None, max_length=50)
    medical_history: Optional[str] = None
    dental_history: Optional[str] = None
    bite_type: BiteType = BiteType.NORMAL
    treatment_stage: TreatmentStage = TreatmentStage.CONSULTATION
    assigned_doctor_id: Optional[int] = None
    notes: Optional[str] = None


class PatientCreate(PatientBase):
    user_id: Optional[int] = None


class PatientUpdate(BaseModel):
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    emergency_contact_name: Optional[str] = None
    emergency_contact_phone: Optional[str] = None
    medical_history: Optional[str] = None
    dental_history: Optional[str] = None
    bite_type: Optional[BiteType] = None
    treatment_stage: Optional[TreatmentStage] = None
    assigned_doctor_id: Optional[int] = None
    notes: Optional[str] = None


class PatientResponse(PatientBase):
    id: int
    user_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    user: Optional[UserResponse] = None
    assigned_doctor: Optional[UserResponse] = None

    model_config = {"from_attributes": True}
