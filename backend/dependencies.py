from typing import Callable, Iterable
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from config.database import get_db
from config.settings import settings
from models.users import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Decode JWT access token and return the authenticated User."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        token_type = payload.get("type", "access")
        if token_type != "access":
            raise credentials_exception

        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception

    return user


def require_role(*allowed_roles: UserRole) -> Callable[[User], User]:
    """Dependency factory checking that the current user has one of the allowed roles."""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            role_names = ", ".join(r.value for r in allowed_roles)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {role_names}.",
            )
        return current_user
    return role_checker


# Specific Role Guards
require_admin = require_role(UserRole.ADMIN)

require_doctor = require_role(UserRole.DOCTOR, UserRole.ORTHODONTIST, UserRole.ADMIN)

require_secretary = require_role(UserRole.SECRETARY, UserRole.ADMIN)

require_staff = require_role(
    UserRole.ADMIN,
    UserRole.DOCTOR,
    UserRole.ORTHODONTIST,
    UserRole.SECRETARY,
)

require_patient = require_role(UserRole.PATIENT, UserRole.ADMIN)
