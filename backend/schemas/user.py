from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from models.users import UserRole


class UserBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=255)
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    email: EmailStr
    phone: Optional[str] = None
    role: UserRole = UserRole.PATIENT


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    username: Optional[str] = Field(None, min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    phone: Optional[str] = None
    email: Optional[EmailStr] = None
    avatar_url: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=6)


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    role: UserRole
    avatar_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
