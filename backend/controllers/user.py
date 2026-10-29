from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from passlib.context import CryptContext
from jose import jwt
from sqlalchemy.orm import Session

from config.settings import settings
from models.users import User
from schemas.user import (
    PasswordChange,
    UserCreate,
    UserResponse,
    UserUpdate,
)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Password & Token Helpers
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against its bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

def get_user_or_404(db: Session, user_id: int) -> User:
    """Fetch an active user or raise a 404 exception."""
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found.",
        )
    return user


# ---------------------------------------------------------------------------
# Business Logic / Controller Methods
# ---------------------------------------------------------------------------

def register_user(db: Session, data: UserCreate) -> UserResponse:
    """Create a new user. Raises 400 if the email is already registered."""
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )

    user = User(
        full_name=data.full_name,
        email=data.email,
        phone=data.phone,
        hashed_password=hash_password(data.password),
        role=data.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def authenticate_user(db: Session, email: str, password: str) -> User:
    """Authenticate credentials. Raises 401 if invalid."""
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive.",
        )
    return user


def get_me(current_user: User) -> UserResponse:
    """Return the profile of the authenticated user."""
    return UserResponse.model_validate(current_user)


def get_user_by_id(db: Session, user_id: int) -> UserResponse:
    """Return a user profile by ID."""
    user = get_user_or_404(db, user_id)
    return UserResponse.model_validate(user)


def list_users(db: Session, skip: int = 0, limit: int = 100) -> list[UserResponse]:
    """Return active users list with pagination."""
    users = db.query(User).filter(User.is_active == True).offset(skip).limit(limit).all()
    return [UserResponse.model_validate(u) for u in users]


def update_me(db: Session, current_user: User, data: UserUpdate) -> UserResponse:
    """Update editable fields on current user profile."""
    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.phone is not None:
        current_user.phone = data.phone
    if data.email is not None and data.email != current_user.email:
        # Check duplicate
        exists = db.query(User).filter(User.email == data.email).first()
        if exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already in use by another account.",
            )
        current_user.email = data.email

    db.commit()
    db.refresh(current_user)
    return UserResponse.model_validate(current_user)


def change_password(db: Session, current_user: User, data: PasswordChange) -> dict:
    """Verify current password and set new password."""
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"message": "Password updated successfully."}
