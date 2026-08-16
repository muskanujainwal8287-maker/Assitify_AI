from uuid import uuid4

import jwt
import pytest
from fastapi import HTTPException

from backend.app.core.config import settings
from backend.app.core.security import (
    create_access_token,
    create_otp,
    create_reset_token,
    decode_access_token,
    hash_password,
    hash_reset_token,
    verify_password,
)


def test_password_hash_roundtrip() -> None:
    hashed = hash_password("my-password")
    assert hashed != "my-password"
    assert verify_password("my-password", hashed) is True
    assert verify_password("wrong", hashed) is False


def test_reset_token_hash_is_stable_and_not_raw() -> None:
    raw = create_reset_token()
    hashed = hash_reset_token(raw)
    assert hashed != raw
    assert hash_reset_token(raw) == hashed
    assert len(raw) >= 32


def test_otp_is_six_digits() -> None:
    otp = create_otp()
    assert len(otp) == 6
    assert otp.isdigit()


def test_access_token_roundtrip() -> None:
    user_id = uuid4()
    token = create_access_token(
        user_id=user_id,
        email="a@example.com",
        mobile_number="9876543210",
    )
    payload = decode_access_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["email"] == "a@example.com"
    assert payload["mobile_number"] == "9876543210"


def test_decode_rejects_tampered_token() -> None:
    user_id = uuid4()
    token = create_access_token(
        user_id=user_id,
        email="a@example.com",
        mobile_number="9876543210",
    )
    bad = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")
    with pytest.raises(HTTPException) as exc:
        decode_access_token(bad)
    assert exc.value.status_code == 401


def test_decode_rejects_wrong_secret() -> None:
    token = jwt.encode(
        {"sub": str(uuid4()), "email": "x@y.com", "mobile_number": "9876543210"},
        "not-the-real-secret",
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(HTTPException):
        decode_access_token(token)
