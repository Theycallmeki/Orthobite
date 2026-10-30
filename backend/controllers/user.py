from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from controllers.auth import hash_password, verify_password
from models.users import User, UserRole
from schemas.user import (
    PasswordChange,
    UserResponse,
    UserUpdate,
)


def get_user_or_404(db: Session, user_id: int) -> User:
    """Fetch an active user or raise a 404 exception."""
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found.",
        )
    return user


def get_me(current_user: User) -> UserResponse:
    """Return the profile of the authenticated user."""
    return UserResponse.model_validate(current_user)


def get_user_by_id(db: Session, user_id: int) -> UserResponse:
    """Return a user profile by ID."""
    user = get_user_or_404(db, user_id)
    return UserResponse.model_validate(user)


def list_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    role: Optional[UserRole] = None,
) -> list[UserResponse]:
    """Return active users list with pagination and optional role filtering."""
    query = db.query(User).filter(User.is_active == True)
    if role:
        query = query.filter(User.role == role)
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    return [UserResponse.model_validate(u) for u in users]


def update_me(db: Session, current_user: User, data: UserUpdate) -> UserResponse:
    """Update editable fields on current user profile."""
    if data.full_name is not None:
        current_user.full_name = data.full_name
    if data.phone is not None:
        current_user.phone = data.phone
    if data.avatar_url is not None:
        current_user.avatar_url = data.avatar_url

    # Check username uniqueness if changed
    if data.username is not None and data.username != current_user.username:
        exists = db.query(User).filter(User.username == data.username).first()
        if exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username is already taken by another account.",
            )
        current_user.username = data.username

    # Check email uniqueness if changed
    if data.email is not None and data.email != current_user.email:
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
