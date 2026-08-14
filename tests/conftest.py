from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.app.api.routes import auth as auth_routes
from backend.app.api.routes import documents as documents_routes
from backend.app.core.security import create_access_token, get_current_user, hash_password
from backend.app.db.models import User
from backend.app.db.session import get_db


class InMemoryDB:
    """Minimal stand-in for SQLAlchemy Session used by auth routes."""

    def __init__(self) -> None:
        self.users_by_id: dict[uuid.UUID, User] = {}
        self.users_by_email: dict[str, User] = {}
        self.users_by_mobile: dict[str, User] = {}
        self._pending: list[User] = []

    def add(self, user: User) -> None:
        self._pending.append(user)

    def commit(self) -> None:
        for user in self._pending:
            if user.id is None:
                user.id = uuid.uuid4()
            if user.created_at is None:
                user.created_at = datetime.now(timezone.utc)
            self.users_by_id[user.id] = user
            self.users_by_email[user.email.lower()] = user
            self.users_by_mobile[user.mobile_number] = user
        self._pending.clear()

    def refresh(self, user: User) -> None:
        if user.id is None:
            user.id = uuid.uuid4()
        if user.created_at is None:
            user.created_at = datetime.now(timezone.utc)

    def get(self, model: type[User], user_id: uuid.UUID) -> User | None:
        if model is not User:
            return None
        return self.users_by_id.get(user_id)


@pytest.fixture
def memory_db() -> InMemoryDB:
    return InMemoryDB()


@pytest.fixture
def sample_user(memory_db: InMemoryDB) -> User:
    user = User(
        id=uuid.uuid4(),
        email="tester@example.com",
        mobile_number="9876543210",
        full_name="Test User",
        password_hash=hash_password("secret123"),
        created_at=datetime.now(timezone.utc),
    )
    memory_db.users_by_id[user.id] = user
    memory_db.users_by_email[user.email] = user
    memory_db.users_by_mobile[user.mobile_number] = user
    return user


@pytest.fixture
def auth_headers(sample_user: User) -> dict[str, str]:
    token = create_access_token(
        user_id=sample_user.id,
        email=sample_user.email,
        mobile_number=sample_user.mobile_number,
    )
    return {"Authorization": f"Bearer {token}"}


def _patch_auth_lookups(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        auth_routes,
        "get_user_by_email",
        lambda db, email: db.users_by_email.get(email.lower().strip()),
    )
    monkeypatch.setattr(
        auth_routes,
        "get_user_by_mobile",
        lambda db, mobile: db.users_by_mobile.get(mobile.strip()),
    )
    monkeypatch.setattr(
        auth_routes,
        "get_user_for_login",
        lambda db, *, email=None, mobile_number=None: (
            (db.users_by_email.get(email.lower().strip()) if email else None)
            or (db.users_by_mobile.get(mobile_number.strip()) if mobile_number else None)
        ),
    )


@pytest.fixture
def auth_client(memory_db: InMemoryDB, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """Auth routes with real JWT validation against in-memory users."""
    app = FastAPI()
    app.include_router(auth_routes.router)

    def override_get_db():
        yield memory_db

    app.dependency_overrides[get_db] = override_get_db
    _patch_auth_lookups(monkeypatch)
    return TestClient(app)


@pytest.fixture
def documents_client(
    memory_db: InMemoryDB,
    sample_user: User,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    """Document routes with auth forced to sample_user (service layer mocked in tests)."""
    app = FastAPI()
    app.include_router(documents_routes.router)
    app.include_router(documents_routes.attempts_router)

    def override_get_db():
        yield memory_db

    def override_get_current_user() -> User:
        return sample_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app)
