from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from models.users import UserRole


class LoginRequest(BaseModel):
    """Login with either username or email and password."""
    identifier: str = Field(..., description="Username or Email address")
    password: str = Field(..., min_length=6)


class RegisterRequest(BaseModel):
    """Patient self-registration payload."""
    full_name: str = Field(..., min_length=1, max_length=255)
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    password: str = Field(..., min_length=6)


class StaffCreateRequest(BaseModel):
    """Admin-only payload to create doctor or secretary staff accounts."""
    full_name: str = Field(..., min_length=1, max_length=255)
    username: str = Field(..., min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    password: str = Field(..., min_length=6)
    role: UserRole = Field(..., description="Staff role: doctor, orthodontist, or secretary")


class Token(BaseModel):
    """Access and refresh token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    full_name: str
    role: UserRole


class RefreshTokenRequest(BaseModel):
    """Payload to refresh an expired access token."""
    refresh_token: str


class TokenPayload(BaseModel):
    """JWT decoded payload structure."""
    sub: str
    type: str  # "access" or "refresh"
    role: Optional[str] = None
    exp: Optional[int] = None
