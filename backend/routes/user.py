from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

import controllers.user as user_controller
from config.database import get_db
from dependencies import get_current_user, require_staff
from models.users import User
from schemas.user import (
    LoginRequest,
    PasswordChange,
    Token,
    UserCreate,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["Users"])


# ---------------------------------------------------------------------------
# Auth / Registration
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user account (patient, staff, secretary, or orthodontist)."""
    return user_controller.register_user(db, data)


@router.post(
    "/login",
    response_model=Token,
    summary="Authenticate user and return JWT access token",
)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email & password, returning a Bearer access token."""
    user = user_controller.authenticate_user(db, data.email, data.password)
    access_token = user_controller.create_access_token(
        data={"sub": str(user.id), "role": user.role.value}
    )
    return Token(access_token=access_token, token_type="bearer")


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
    """Update full name, phone number, or email for the authenticated user."""
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

@router.get(
    "/",
    response_model=list[UserResponse],
    summary="List users (Staff only: Admin, Orthodontist, Secretary)",
)
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: User = Depends(require_staff),
):
    """Paginated list of active users."""
    return user_controller.list_users(db, skip=skip, limit=limit)


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
