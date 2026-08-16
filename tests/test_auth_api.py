from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.core.security import create_access_token, verify_password
from backend.app.db.models import User
from backend.app.services import password_reset as password_reset_service


def test_register_success(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/auth/register",
        json={
            "email": "newuser@example.com",
            "mobile_number": "9123456780",
            "password": "secret12",
            "full_name": "New User",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert "access_token" in body
    assert body["user"]["email"] == "newuser@example.com"
    assert body["token_type"] == "bearer"


def test_register_duplicate_email(auth_client: TestClient, sample_user: User) -> None:
    response = auth_client.post(
        "/api/auth/register",
        json={
            "email": sample_user.email,
            "mobile_number": "9123456781",
            "password": "secret12",
        },
    )
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


def test_login_with_email(auth_client: TestClient, sample_user: User) -> None:
    response = auth_client.post(
        "/api/auth/login",
        json={"email": sample_user.email, "password": "secret123"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["access_token"]


def test_login_with_mobile(auth_client: TestClient, sample_user: User) -> None:
    response = auth_client.post(
        "/api/auth/login",
        json={"mobile_number": sample_user.mobile_number, "password": "secret123"},
    )
    assert response.status_code == 200


def test_login_wrong_password(auth_client: TestClient, sample_user: User) -> None:
    response = auth_client.post(
        "/api/auth/login",
        json={"email": sample_user.email, "password": "nope"},
    )
    assert response.status_code == 401


def test_me_requires_auth(auth_client: TestClient) -> None:
    response = auth_client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_with_token(auth_client: TestClient, sample_user: User) -> None:
    token = create_access_token(
        user_id=sample_user.id,
        email=sample_user.email,
        mobile_number=sample_user.mobile_number,
    )
    response = auth_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, response.text
    assert response.json()["email"] == sample_user.email


def test_me_rejects_unknown_user_token(auth_client: TestClient) -> None:
    token = create_access_token(
        user_id=uuid4(),
        email="ghost@example.com",
        mobile_number="9000000000",
    )
    response = auth_client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_forgot_password_unknown_email(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )
    assert response.status_code == 200
    assert "If an account exists" in response.json()["message"]


def test_forgot_password_known_email_sends_and_resets(
    auth_client: TestClient,
    sample_user: User,
    monkeypatch,
) -> None:
    sent: dict[str, str] = {}

    def fake_send(*, to_email: str, reset_url: str) -> None:
        sent["to_email"] = to_email
        sent["reset_url"] = reset_url

    monkeypatch.setattr("backend.app.api.routes.auth.send_password_reset_email", fake_send)

    response = auth_client.post(
        "/api/auth/forgot-password",
        json={"email": sample_user.email},
    )
    assert response.status_code == 200
    body = response.json()
    assert "If an account exists" in body["message"]
    assert body["channel"] == "email"
    assert sent["to_email"] == sample_user.email
    assert "/reset-password?token=" in sent["reset_url"]

    token = sent["reset_url"].split("token=", 1)[1]
    reset = auth_client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "brandnew1"},
    )
    assert reset.status_code == 200, reset.text

    assert verify_password("brandnew1", sample_user.password_hash)
    assert (
        auth_client.post(
            "/api/auth/login",
            json={"email": sample_user.email, "password": "brandnew1"},
        ).status_code
        == 200
    )
    assert (
        auth_client.post(
            "/api/auth/login",
            json={"email": sample_user.email, "password": "secret123"},
        ).status_code
        == 401
    )


def test_forgot_password_by_mobile_sends_otp_and_resets(
    auth_client: TestClient,
    sample_user: User,
    monkeypatch,
) -> None:
    sent: dict[str, str] = {}

    def fake_sms(*, mobile_number: str, otp: str | None = None) -> None:
        sent["mobile_number"] = mobile_number
        if otp:
            sent["otp"] = otp

    monkeypatch.setattr("backend.app.api.routes.auth.send_password_reset_sms", fake_sms)
    monkeypatch.setattr("backend.app.api.routes.auth.uses_twilio_verify", lambda: False)

    response = auth_client.post(
        "/api/auth/forgot-password",
        json={"mobile_number": sample_user.mobile_number},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["channel"] == "sms"
    assert sent["mobile_number"] == sample_user.mobile_number
    assert len(sent["otp"]) == 6

    reset = auth_client.post(
        "/api/auth/reset-password",
        json={
            "mobile_number": sample_user.mobile_number,
            "otp": sent["otp"],
            "new_password": "mobilepw1",
        },
    )
    assert reset.status_code == 200, reset.text
    assert verify_password("mobilepw1", sample_user.password_hash)
    assert (
        auth_client.post(
            "/api/auth/login",
            json={"mobile_number": sample_user.mobile_number, "password": "mobilepw1"},
        ).status_code
        == 200
    )


def test_forgot_password_twilio_verify_flow(
    auth_client: TestClient,
    sample_user: User,
    monkeypatch,
) -> None:
    sent: dict[str, str] = {}

    monkeypatch.setattr("backend.app.api.routes.auth.uses_twilio_verify", lambda: True)
    monkeypatch.setattr(
        "backend.app.api.routes.auth.send_password_reset_sms",
        lambda *, mobile_number, otp=None: sent.update(mobile_number=mobile_number),
    )
    monkeypatch.setattr(
        "backend.app.api.routes.auth.check_password_reset_otp",
        lambda *, mobile_number, otp: otp == "654321" and mobile_number == sample_user.mobile_number,
    )

    response = auth_client.post(
        "/api/auth/forgot-password",
        json={"mobile_number": sample_user.mobile_number},
    )
    assert response.status_code == 200
    assert response.json()["channel"] == "sms"
    assert sent["mobile_number"] == sample_user.mobile_number

    bad = auth_client.post(
        "/api/auth/reset-password",
        json={
            "mobile_number": sample_user.mobile_number,
            "otp": "000000",
            "new_password": "verifyok1",
        },
    )
    assert bad.status_code == 400

    ok = auth_client.post(
        "/api/auth/reset-password",
        json={
            "mobile_number": sample_user.mobile_number,
            "otp": "654321",
            "new_password": "verifyok1",
        },
    )
    assert ok.status_code == 200, ok.text
    assert verify_password("verifyok1", sample_user.password_hash)


def test_reset_password_rejects_invalid_otp(
    auth_client: TestClient,
    sample_user: User,
) -> None:
    password_reset_service.store_reset_otp(
        user_id=sample_user.id,
        mobile_number=sample_user.mobile_number,
    )
    response = auth_client.post(
        "/api/auth/reset-password",
        json={
            "mobile_number": sample_user.mobile_number,
            "otp": "000000",
            "new_password": "brandnew1",
        },
    )
    assert response.status_code == 400
    assert "OTP" in response.json()["detail"]


def test_reset_password_rejects_invalid_token(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/auth/reset-password",
        json={"token": "not-a-real-token-value", "new_password": "brandnew1"},
    )
    assert response.status_code == 400
    assert "Invalid or expired" in response.json()["detail"]


def test_reset_password_token_is_single_use(
    auth_client: TestClient,
    sample_user: User,
) -> None:
    raw = password_reset_service.store_reset_token(sample_user.id)
    first = auth_client.post(
        "/api/auth/reset-password",
        json={"token": raw, "new_password": "onceonly1"},
    )
    assert first.status_code == 200
    second = auth_client.post(
        "/api/auth/reset-password",
        json={"token": raw, "new_password": "onceonly2"},
    )
    assert second.status_code == 400


def test_forgot_password_requires_identifier(auth_client: TestClient) -> None:
    response = auth_client.post("/api/auth/forgot-password", json={})
    assert response.status_code == 422
