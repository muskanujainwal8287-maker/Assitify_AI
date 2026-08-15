import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.security import (
    create_access_token,
    get_current_user,
    get_user_by_email,
    get_user_by_mobile,
    get_user_for_login,
    hash_password,
    verify_password,
)
from backend.app.db.models import User
from backend.app.db.session import get_db
from backend.app.schemas import (
    AuthTokenResponse,
    UserLoginRequest,
    UserOut,
    UserRegisterRequest,
    UserUpdateRequest,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)


def _token_response(user: User) -> AuthTokenResponse:
    token = create_access_token(
        user_id=user.id,
        email=user.email,
        mobile_number=user.mobile_number,
    )
    return AuthTokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.post("/register", response_model=AuthTokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegisterRequest, db: Session = Depends(get_db)) -> AuthTokenResponse:
    email = payload.email.lower().strip()
    if get_user_by_email(db, email):
        raise HTTPException(status_code=400, detail="Email already registered.")
    if get_user_by_mobile(db, payload.mobile_number):
        raise HTTPException(status_code=400, detail="Mobile number already registered.")

    user = User(
        email=email,
        mobile_number=payload.mobile_number,
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.post("/login", response_model=AuthTokenResponse)
def login(payload: UserLoginRequest, db: Session = Depends(get_db)) -> AuthTokenResponse:
    user = get_user_for_login(
        db,
        email=payload.email,
        mobile_number=payload.mobile_number,
    )
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email, mobile number, or password.")
    return _token_response(user)


@router.get(
    "/me",
    response_model=UserOut,
    summary="Current user",
    description=("JWT required."),
)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.patch(
    "/me",
    response_model=UserOut,
    summary="Update current user",
    description="JWT required. Update full name, email, and mobile number.",
)
def update_me(
    payload: UserUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserOut:
    email = payload.email.lower().strip()
    existing_email = get_user_by_email(db, email)
    if existing_email and existing_email.id != user.id:
        raise HTTPException(status_code=400, detail="Email already registered.")
    existing_mobile = get_user_by_mobile(db, payload.mobile_number)
    if existing_mobile and existing_mobile.id != user.id:
        raise HTTPException(status_code=400, detail="Mobile number already registered.")

    user.email = email
    user.mobile_number = payload.mobile_number
    user.full_name = payload.full_name.strip()
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserOut.model_validate(user)
