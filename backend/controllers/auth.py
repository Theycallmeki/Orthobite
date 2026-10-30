import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import or_
from sqlalchemy.orm import Session

from config.settings import settings
from models.users import User, UserRole
from schemas.auth import (
    RegisterRequest,
    StaffCreateRequest,
    Token,
)
from schemas.user import UserResponse

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Password & JWT Helpers
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Hash plaintext password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plaintext password against bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_token(data: dict, expires_delta: timedelta, token_type: str = "access") -> str:
    """Create a signed JWT token with a unique jti claim."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({
        "exp": expire,
        "type": token_type,
        "jti": str(uuid.uuid4()),
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_access_token(user_id: int, role: str) -> str:
    """Generate an access token."""
    return create_token(
        data={"sub": str(user_id), "role": role},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        token_type="access",
    )


def create_refresh_token(user_id: int, role: str) -> str:
    """Generate a refresh token."""
    return create_token(
        data={"sub": str(user_id), "role": role},
        expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        token_type="refresh",
    )


def build_token_response(user: User) -> Token:
    """Generate both access and refresh tokens for an authenticated user."""
    access_token = create_access_token(user.id, user.role.value)
    refresh_token = create_refresh_token(user.id, user.role.value)
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
    )


# ---------------------------------------------------------------------------
# Authentication & User Creation Business Logic
# ---------------------------------------------------------------------------

def register_patient(db: Session, data: RegisterRequest) -> UserResponse:
    """Self-registration for patients."""
    # Check duplicate email or username
    existing = db.query(User).filter(
        or_(User.email == data.email, User.username == data.username)
    ).first()
    if existing:
        if existing.email == data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email address already exists.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This username is already taken.",
            )

    user = User(
        full_name=data.full_name,
        username=data.username,
        email=data.email,
        phone=data.phone,
        hashed_password=hash_password(data.password),
        role=UserRole.PATIENT,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserResponse.model_validate(user)


def create_staff_user(db: Session, data: StaffCreateRequest) -> UserResponse:
    """Admin-only creation of doctor, orthodontist, or secretary accounts."""
    if data.role not in (UserRole.DOCTOR, UserRole.ORTHODONTIST, UserRole.SECRETARY, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid staff role specified.",
        )

    existing = db.query(User).filter(
        or_(User.email == data.email, User.username == data.username)
    ).first()
    if existing:
        if existing.email == data.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A staff member with this email address already exists.",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This username is already taken.",
            )

    user = User(
        full_name=data.full_name,
        username=data.username,
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


def authenticate_user(db: Session, identifier: str, password: str) -> User:
    """Authenticate via email or username. Raises 401 if invalid."""
    user = db.query(User).filter(
        or_(User.email == identifier, User.username == identifier)
    ).first()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive. Please contact the clinic.",
        )
    return user


def refresh_access_token(db: Session, refresh_token: str) -> Token:
    """Validate refresh token and issue a new token pair."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_type: str = payload.get("type")
        user_id: str = payload.get("sub")
        if token_type != "refresh" or user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception

    return build_token_response(user)
