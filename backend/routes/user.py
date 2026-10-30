from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

import controllers.auth as auth_controller
import controllers.user as user_controller
from config.database import get_db
from dependencies import get_current_user, require_admin, require_staff
from models.users import User, UserRole
from schemas.auth import (
    LoginRequest,
    RegisterRequest,
    StaffCreateRequest,
    Token,
)
from schemas.user import (
    PasswordChange,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["Users"])


# ---------------------------------------------------------------------------
# Backwards-compatible Auth Aliases (/users/register & /users/login)
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new patient account (alias)",
)
def register_alias(data: RegisterRequest, db: Session = Depends(get_db)):
    """Self-registration alias for patient accounts."""
    return auth_controller.register_patient(db, data)


@router.post(
    "/login",
    response_model=Token,
    summary="Login user (alias)",
)
def login_alias(data: LoginRequest, db: Session = Depends(get_db)):
    """Login alias accepting username or email."""
    user = auth_controller.authenticate_user(db, data.identifier, data.password)
    return auth_controller.build_token_response(user)


# ---------------------------------------------------------------------------
# Current User Profile
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user's profile",
)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return user_controller.get_me(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update current user's profile",
)
def update_me(
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update full name, phone number, username, or avatar for the authenticated user."""
    return user_controller.update_me(db, current_user, data)


@router.post(
    "/me/change-password",
    summary="Change current user's password",
)
def change_password(
    data: PasswordChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify old password and set a new password."""
    return user_controller.change_password(db, current_user, data)


# ---------------------------------------------------------------------------
# Staff / Administrative Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/staff",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create staff account (Admin only)",
)
def create_staff(
    data: StaffCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """Admin-only endpoint to register Doctor or Secretary accounts."""
    return auth_controller.create_staff_user(db, data)


@router.get(
    "/",
    response_model=list[UserResponse],
    summary="List users (Staff only: Admin, Doctor, Secretary)",
)
def list_users(
    skip: int = 0,
    limit: int = 100,
    role: Optional[UserRole] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Paginated list of active users, with optional role filtering."""
    return user_controller.list_users(db, skip=skip, limit=limit, role=role)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user profile by ID (Staff only)",
)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Retrieve user details by ID."""
    return user_controller.get_user_by_id(db, user_id)
