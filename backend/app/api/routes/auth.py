import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.core.config import settings
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
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    MessageResponse,
    ResetPasswordRequest,
    UserLoginRequest,
    UserOut,
    UserRegisterRequest,
    UserUpdateRequest,
)
from backend.app.services.email import send_password_reset_email
from backend.app.services import password_reset as password_reset_service
from backend.app.services.sms import (
    check_password_reset_otp,
    send_password_reset_sms,
    uses_twilio_verify,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
logger = logging.getLogger(__name__)

_FORGOT_EMAIL_MESSAGE = (
    "If an account exists for that email, we sent a password reset link."
)
_FORGOT_SMS_MESSAGE = (
    "If an account exists for that mobile number, we sent a one-time code."
)


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


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(
    payload: ForgotPasswordRequest,
    db: Session = Depends(get_db),
) -> ForgotPasswordResponse:
    via_sms = bool(payload.mobile_number) and not payload.email
    identifier = (str(payload.email) if payload.email else payload.mobile_number) or ""
    if password_reset_service.is_rate_limited(identifier):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many reset requests. Please try again later.",
        )

    user = get_user_for_login(
        db,
        email=payload.email,
        mobile_number=payload.mobile_number,
    )
    if user:
        if via_sms:
            try:
                if uses_twilio_verify():
                    password_reset_service.store_pending_sms_reset(
                        user_id=user.id,
                        mobile_number=user.mobile_number,
                    )
                    send_password_reset_sms(mobile_number=user.mobile_number)
                else:
                    otp = password_reset_service.store_reset_otp(
                        user_id=user.id,
                        mobile_number=user.mobile_number,
                    )
                    send_password_reset_sms(mobile_number=user.mobile_number, otp=otp)
            except Exception:  # noqa: BLE001
                logger.exception("Password reset SMS failed for user %s", user.id)
        else:
            raw_token = password_reset_service.store_reset_token(user.id)
            reset_url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={raw_token}"
            try:
                send_password_reset_email(to_email=user.email, reset_url=reset_url)
            except Exception:  # noqa: BLE001
                logger.exception("Password reset email failed for user %s", user.id)

    if via_sms:
        return ForgotPasswordResponse(message=_FORGOT_SMS_MESSAGE, channel="sms")
    return ForgotPasswordResponse(message=_FORGOT_EMAIL_MESSAGE, channel="email")


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(
    payload: ResetPasswordRequest,
    db: Session = Depends(get_db),
) -> MessageResponse:
    if payload.token:
        user_id = password_reset_service.consume_reset_token(payload.token)
        invalid_detail = "Invalid or expired reset token."
    else:
        assert payload.mobile_number and payload.otp
        invalid_detail = "Invalid or expired OTP."
        if uses_twilio_verify():
            if not check_password_reset_otp(
                mobile_number=payload.mobile_number,
                otp=payload.otp,
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=invalid_detail,
                )
            user_id = password_reset_service.consume_pending_sms_reset(
                mobile_number=payload.mobile_number,
            )
        else:
            user_id = password_reset_service.consume_reset_otp(
                mobile_number=payload.mobile_number,
                otp=payload.otp,
            )

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=invalid_detail,
        )

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=invalid_detail,
        )

    user.password_hash = hash_password(payload.new_password)
    db.add(user)
    db.commit()
    return MessageResponse(message="Password updated. You can log in with your new password.")


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
