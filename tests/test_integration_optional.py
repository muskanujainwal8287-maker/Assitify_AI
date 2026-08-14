"""Optional live checks. Skipped automatically when Docker/services are down."""

from __future__ import annotations

import os

import httpx
import pytest


def _ping(url: str, timeout: float = 2.0) -> bool:
    try:
        response = httpx.get(url, timeout=timeout)
        return response.status_code < 500
    except Exception:
        return False


@pytest.fixture(scope="module")
def backend_url() -> str:
    return os.getenv("BACKEND_URL", "http://127.0.0.1:8001")


@pytest.fixture(scope="module")
def ai_url() -> str:
    return os.getenv("AI_LAYER_URL", "http://127.0.0.1:8000")


@pytest.mark.integration
def test_backend_health_if_running(backend_url: str) -> None:
    if not _ping(f"{backend_url}/"):
        pytest.skip("Backend not running on :8001")
    response = httpx.get(f"{backend_url}/health", timeout=5.0)
    assert response.status_code == 200
    body = response.json()
    assert body.get("status") == "ok"
    assert "ai" in body


@pytest.mark.integration
def test_ai_health_if_running(ai_url: str) -> None:
    if not _ping(f"{ai_url}/"):
        pytest.skip("AI layer not running on :8000")
    response = httpx.get(f"{ai_url}/health/ai", timeout=5.0)
    assert response.status_code == 200
    body = response.json()
    assert body.get("status") == "ok"


@pytest.mark.integration
def test_postgres_reachable_via_backend_settings() -> None:
    """Connect only if DATABASE_URL host answers; does not mutate schema."""
    try:
        from sqlalchemy import create_engine, text

        from backend.app.core.config import settings
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Cannot import settings: {exc}")

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        with engine.connect() as conn:
            value = conn.execute(text("SELECT 1")).scalar()
            assert value == 1
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Postgres not reachable: {exc}")
    finally:
        engine.dispose()


@pytest.mark.integration
def test_redis_reachable_via_backend_settings() -> None:
    try:
        from redis import Redis

        from backend.app.core.config import settings
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Cannot import redis/settings: {exc}")

    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)
        assert client.ping() is True
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"Redis not reachable: {exc}")
