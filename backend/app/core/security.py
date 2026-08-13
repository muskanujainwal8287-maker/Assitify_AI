from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.models import User
from backend.app.db.session import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
jwt_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="JWT",
    bearerFormat="JWT",
    description="Paste access_token from /api/auth/login or /register. Do not type Bearer.",
)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(*, user_id: UUID, email: str, mobile_number: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": str(user_id),
        "email": email,
        "mobile_number": mobile_number,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        ) from exc


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email.lower().strip()))


def get_user_by_mobile(db: Session, mobile_number: str) -> User | None:
    return db.scalar(select(User).where(User.mobile_number == mobile_number.strip()))


def get_user_for_login(db: Session, *, email: str | None, mobile_number: str | None) -> User | None:
    if email:
        user = get_user_by_email(db, email)
        if user:
            return user
    if mobile_number:
        return get_user_by_mobile(db, mobile_number)
    return None


def _token_from_authorization_header(authorization: str) -> str:
    value = authorization.strip()
    if value.lower().startswith("bearer "):
        value = value[7:].strip()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Send Authorization: Bearer <token>.",
        )
    return value


def _user_from_token(db: Session, token: str) -> User:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")

    user = db.get(User, UUID(user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    return user


def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(jwt_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User | None:
    if credentials is None:
        if settings.auth_required:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required. Send Authorization: Bearer <token>.",
            )
        return None
    return _user_from_token(db, credentials.credentials)


def get_user_from_bearer_header(db: Session, authorization: str) -> User:
    return _user_from_token(db, _token_from_authorization_header(authorization))


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(jwt_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing JWT. Send header: Authorization: Bearer <access_token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _user_from_token(db, credentials.credentials)
