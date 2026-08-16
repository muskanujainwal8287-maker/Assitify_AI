import pytest
from pydantic import ValidationError

from backend.app.schemas import (
    DoubtRequest,
    ForgotPasswordRequest,
    QuestionGenerationRequest,
    ResetPasswordRequest,
    UserLoginRequest,
    UserRegisterRequest,
    normalize_mobile_number,
)


def test_normalize_mobile_strips_country_code() -> None:
    assert normalize_mobile_number("+91 98765 43210") == "9876543210"
    assert normalize_mobile_number("919876543210") == "9876543210"


def test_normalize_mobile_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        normalize_mobile_number("12345")
    with pytest.raises(ValueError):
        normalize_mobile_number("5876543210")  # must start 6-9


def test_register_request_valid() -> None:
    payload = UserRegisterRequest(
        email="User@Example.com",
        mobile_number="9876543210",
        password="secret1",
        full_name="Ada",
    )
    assert payload.mobile_number == "9876543210"


def test_login_requires_email_or_mobile() -> None:
    with pytest.raises(ValidationError):
        UserLoginRequest(password="secret1")


def test_login_accepts_mobile_only() -> None:
    payload = UserLoginRequest(mobile_number="9876543210", password="secret1")
    assert payload.email is None
    assert payload.mobile_number == "9876543210"


def test_forgot_password_requires_email_or_mobile() -> None:
    with pytest.raises(ValidationError):
        ForgotPasswordRequest()


def test_forgot_password_accepts_email() -> None:
    payload = ForgotPasswordRequest(email="user@example.com")
    assert payload.mobile_number is None


def test_reset_password_min_length() -> None:
    with pytest.raises(ValidationError):
        ResetPasswordRequest(token="shorttok", new_password="123")
    ok = ResetPasswordRequest(token="a-valid-reset-token", new_password="secret1")
    assert ok.new_password == "secret1"


def test_reset_password_accepts_otp() -> None:
    payload = ResetPasswordRequest(
        mobile_number="9876543210",
        otp="123456",
        new_password="secret1",
    )
    assert payload.token is None


def test_reset_password_requires_token_or_otp() -> None:
    with pytest.raises(ValidationError):
        ResetPasswordRequest(new_password="secret1")


def test_doubt_request_min_length() -> None:
    with pytest.raises(ValidationError):
        DoubtRequest(question="hi")
    ok = DoubtRequest(question="What is photosynthesis?")
    assert ok.session_id is None


def test_question_generation_patterns() -> None:
    payload = QuestionGenerationRequest(question_type="objective", difficulty="medium", count=3)
    assert payload.count == 3
    with pytest.raises(ValidationError):
        QuestionGenerationRequest(question_type="mcq")
    with pytest.raises(ValidationError):
        QuestionGenerationRequest(count=0)
