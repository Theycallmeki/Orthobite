from fastapi import APIRouter, Depends, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

import controllers.auth as auth_controller
from config.database import get_db
from dependencies import get_current_user
from models.users import User
from schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    RegisterRequest,
    Token,
)
from schemas.user import UserResponse

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Patient self-registration",
)
@limiter.limit("5/minute")
def register(request: Request, data: RegisterRequest, db: Session = Depends(get_db)):
    """Self-register a new patient account with username, email, phone, and password.
    Rate-limited to 5 requests per minute per IP to prevent abuse.
    """
    return auth_controller.register_patient(db, data)


@router.post(
    "/login",
    response_model=Token,
    summary="Login with username or email",
)
@limiter.limit("10/minute")
def login(request: Request, data: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate using username or email and password. Returns access and refresh tokens.
    Rate-limited to 10 requests per minute per IP to prevent brute-force attacks.
    """
    user = auth_controller.authenticate_user(
        db, data.identifier, data.password,
        ip_address=request.client.host if request.client else None,
    )
    return auth_controller.build_token_response(user)


@router.post(
    "/refresh",
    response_model=Token,
    summary="Refresh access token",
)
def refresh_token(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a fresh access token and refresh token."""
    return auth_controller.refresh_access_token(db, data.refresh_token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Verify current session and return user",
)
def auth_me(current_user: User = Depends(get_current_user)):
    """Return authenticated user profile from access token."""
    return UserResponse.model_validate(current_user)
