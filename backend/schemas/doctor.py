from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import time, datetime
from decimal import Decimal


class DoctorProfileBase(BaseModel):
    specialty: str = Field("Orthodontics", max_length=100)
    bio: Optional[str] = None
    photo_url: Optional[str] = Field(None, max_length=500)
    years_of_experience: int = Field(0, ge=0)
    education: Optional[str] = Field(None, max_length=255)
    consultation_fee: Decimal = Field(Decimal("0.00"), ge=0)
    is_accepting_patients: bool = True


class DoctorProfileCreate(DoctorProfileBase):
    pass


class DoctorProfileUpdate(BaseModel):
    specialty: Optional[str] = None
    bio: Optional[str] = None
    photo_url: Optional[str] = None
    years_of_experience: Optional[int] = Field(None, ge=0)
    education: Optional[str] = None
    consultation_fee: Optional[Decimal] = Field(None, ge=0)
    is_accepting_patients: Optional[bool] = None


class DoctorPublicResponse(DoctorProfileBase):
    """Public profile payload used in frontend doctor carousel."""
    id: int
    user_id: int
    full_name: str
    username: str
    email: str

    model_config = {"from_attributes": True}


class AvailabilityRuleItem(BaseModel):
    day_of_week: int = Field(..., ge=0, le=6, description="0=Monday, 1=Tuesday, ..., 6=Sunday")
    start_time: time = Field(..., description="HH:MM:SS format e.g. 09:00:00")
    end_time: time = Field(..., description="HH:MM:SS format e.g. 17:00:00")
    slot_duration_minutes: int = Field(30, ge=10, le=240)
    is_active: bool = True


class SetAvailabilityRulesRequest(BaseModel):
    rules: List[AvailabilityRuleItem]


class AvailabilityRuleResponse(AvailabilityRuleItem):
    id: int
    doctor_id: int

    model_config = {"from_attributes": True}


class TimeOffCreate(BaseModel):
    start_datetime: datetime
    end_datetime: datetime
    reason: Optional[str] = Field(None, max_length=255)


class TimeOffResponse(TimeOffCreate):
    id: int
    doctor_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class TimeSlot(BaseModel):
    start_time: str                                             
    end_time: str                                               
    formatted_time: str                                  
    is_available: bool                                                      


class DayAvailability(BaseModel):
    date: str                              
    day_of_week: int                                    
    day_name: str                                         
    slots: List[TimeSlot]


class DoctorAvailabilityResponse(BaseModel):
    doctor_id: int
    doctor_name: str
    month: str                          
    days: List[DayAvailability]
