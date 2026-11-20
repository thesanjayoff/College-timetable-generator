"""Password hashing, JWT creation/decoding, and auth-related FastAPI dependencies."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.enums import UserRole
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

ACCESS_TOKEN_SUBJECT_CLAIM = "sub"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta if expires_delta is not None else timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode = {ACCESS_TOKEN_SUBJECT_CLAIM: subject, "exp": expire}
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    user_id = payload.get(ACCESS_TOKEN_SUBJECT_CLAIM)
    if user_id is None:
        raise credentials_exception
    try:
        user = db.get(User, int(user_id))
    except (TypeError, ValueError):
        raise credentials_exception
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is inactive")
    return user


def require_role(*roles: UserRole):
    """Dependency factory: 403s unless current_user.role is one of the allowed roles."""

    allowed = set(roles)

    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role.value}' is not permitted to perform this action",
            )
        return current_user

    return _dependency


def require_department_access(user: User, department_id: Optional[int]) -> None:
    """ADMIN always passes. COORDINATOR passes only if department_id matches their own.
    VIEWER never passes (write checks should already be blocked by require_role, but this
    is defense in depth). Raises HTTPException(403) on failure.
    """
    if user.role == UserRole.ADMIN:
        return
    if user.role == UserRole.COORDINATOR:
        if department_id is not None and user.department_id == department_id:
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Coordinators may only manage data scoped to their own department",
        )
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not permitted")


# Convenience role-group dependencies, usable directly as `Depends(...)`.
require_admin = require_role(UserRole.ADMIN)
require_write_access = require_role(UserRole.ADMIN, UserRole.COORDINATOR)
require_read_access = require_role(UserRole.ADMIN, UserRole.COORDINATOR, UserRole.VIEWER)
