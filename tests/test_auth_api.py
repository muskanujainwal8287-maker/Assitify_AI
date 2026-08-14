from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.core.security import create_access_token
from backend.app.db.models import User


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
