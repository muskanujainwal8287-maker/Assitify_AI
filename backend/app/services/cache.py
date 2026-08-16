from __future__ import annotations

import json
import logging
from typing import Any

from redis import Redis

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

# Shared with AI-layer redis repo prefixes (cleared on document delete).
_DOC_PREFIX = "assitify:doc:"
_QUESTIONS_PREFIX = "assitify:questions:"

# Backend BFF response cache.
_SUMMARY_PREFIX = "assitify:bff:summary:"
_KEYPOINTS_PREFIX = "assitify:bff:keypoints:"
_TOPIC_KEYPOINTS_PREFIX = "assitify:bff:topic-keypoints:"
_NOTES_PREFIX = "assitify:bff:notes:"
_BFF_QUESTIONS_PREFIX = "assitify:bff:questions:"

_DEFAULT_TTL_SECONDS = 60 * 60  # 1 hour

_client: Redis | None = None
_client_failed = False


def _get_client() -> Redis | None:
    global _client, _client_failed
    if _client is not None:
        return _client
    if _client_failed or not settings.redis_url:
        return None
    try:
        client = Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        _client = client
        return _client
    except Exception as exc:  # noqa: BLE001
        _client_failed = True
        logger.warning("Redis unavailable (%s); skipping cache operations.", exc)
        return None


def get_json(key: str) -> dict[str, Any] | list[Any] | None:
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if not raw:
            return None
        return json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis get failed for %s: %s", key, exc)
        return None


def set_json(key: str, value: Any, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.set(key, json.dumps(value), ex=ttl_seconds)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis set failed for %s: %s", key, exc)


def delete_key(key: str) -> None:
    client = _get_client()
    if client is None:
        return
    try:
        client.delete(key)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis delete failed for %s: %s", key, exc)


def set_string(key: str, value: str, ttl_seconds: int) -> bool:
    client = _get_client()
    if client is None:
        return False
    try:
        client.set(key, value, ex=ttl_seconds)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis set_string failed for %s: %s", key, exc)
        return False


def get_string(key: str) -> str | None:
    client = _get_client()
    if client is None:
        return None
    try:
        value = client.get(key)
        return str(value) if value is not None else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis get_string failed for %s: %s", key, exc)
        return None


def getdel_string(key: str) -> str | None:
    """Atomically get and delete a string value."""
    client = _get_client()
    if client is None:
        return None
    try:
        value = client.getdel(key)
        return str(value) if value is not None else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis getdel failed for %s: %s", key, exc)
        return None


def incr_with_expire(key: str, ttl_seconds: int) -> int | None:
    """Atomically increment a counter and set TTL on first write. None if Redis down."""
    client = _get_client()
    if client is None:
        return None
    try:
        count = int(client.incr(key))
        if count == 1:
            client.expire(key, ttl_seconds)
        return count
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis incr failed for %s: %s", key, exc)
        return None


def summary_key(document_id: str) -> str:
    return _SUMMARY_PREFIX + document_id


def keypoints_key(document_id: str) -> str:
    return _KEYPOINTS_PREFIX + document_id


def topic_keypoints_key(document_id: str, *, topic: str) -> str:
    topic_part = topic.strip().lower() or "_"
    return f"{_TOPIC_KEYPOINTS_PREFIX}{document_id}:{topic_part}"


def notes_key(
    document_id: str,
    *,
    chapter_id: str,
    topic: str | None,
) -> str:
    topic_part = (topic or "").strip().lower() or "_"
    return f"{_NOTES_PREFIX}{document_id}:{chapter_id.strip()}:{topic_part}"


def questions_key(
    document_id: str,
    *,
    question_type: str,
    difficulty: str,
    count: int,
    topic: str | None,
) -> str:
    topic_part = (topic or "").strip().lower() or "_"
    return f"{_BFF_QUESTIONS_PREFIX}{document_id}:{question_type}:{difficulty}:{count}:{topic_part}"


def delete_document_cache(document_id: str) -> None:
    client = _get_client()
    if client is None:
        return
    keys = [
        _DOC_PREFIX + document_id,
        _QUESTIONS_PREFIX + document_id,
        summary_key(document_id),
        keypoints_key(document_id),
    ]
    try:
        for pattern in (
            f"{_BFF_QUESTIONS_PREFIX}{document_id}:*",
            f"{_NOTES_PREFIX}{document_id}:*",
            f"{_TOPIC_KEYPOINTS_PREFIX}{document_id}:*",
        ):
            for key in client.scan_iter(match=pattern, count=100):
                keys.append(key)
        if keys:
            client.delete(*keys)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Redis delete failed for document %s: %s", document_id, exc)
