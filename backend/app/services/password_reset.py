from __future__ import annotations

import logging
import time
from threading import Lock
from uuid import UUID

from backend.app.core.config import settings
from backend.app.core.security import create_otp, create_reset_token, hash_reset_token
from backend.app.services import cache as cache_service

logger = logging.getLogger(__name__)

_RESET_PREFIX = "assitify:reset:"
_OTP_PREFIX = "assitify:otp:"
_RATE_PREFIX = "assitify:reset-rate:"

_memory_tokens: dict[str, tuple[str, float]] = {}
_memory_rates: dict[str, list[float]] = {}
_lock = Lock()


def _token_key(token_hash: str) -> str:
    return _RESET_PREFIX + token_hash


def _otp_key(mobile_number: str) -> str:
    return _OTP_PREFIX + mobile_number.strip()


def _rate_key(identifier: str) -> str:
    return _RATE_PREFIX + identifier.strip().lower()


def clear_memory_store() -> None:
    """Test helper to wipe in-process reset state."""
    with _lock:
        _memory_tokens.clear()
        _memory_rates.clear()


def is_rate_limited(identifier: str) -> bool:
    """Return True if this identifier has hit the forgot-password rate limit."""
    key = _rate_key(identifier)
    window_seconds = settings.password_reset_expire_minutes * 60
    limit = settings.password_reset_rate_limit
    now = time.time()

    count = cache_service.incr_with_expire(key, window_seconds)
    if count is not None:
        return count > limit

    with _lock:
        stamps = [ts for ts in _memory_rates.get(key, []) if now - ts < window_seconds]
        stamps.append(now)
        _memory_rates[key] = stamps
        return len(stamps) > limit


def _store_value(key: str, value: str, ttl: int) -> None:
    if cache_service.set_string(key, value, ttl):
        with _lock:
            _memory_tokens.pop(key, None)
        return
    with _lock:
        _memory_tokens[key] = (value, time.time() + ttl)


def _consume_value(key: str) -> str | None:
    value = cache_service.getdel_string(key)
    if value is not None:
        with _lock:
            _memory_tokens.pop(key, None)
        return value

    with _lock:
        entry = _memory_tokens.pop(key, None)
        if not entry:
            return None
        stored, expires_at = entry
        if time.time() > expires_at:
            return None
        return stored


def _peek_value(key: str) -> str | None:
    value = cache_service.get_string(key)
    if value is not None:
        return value
    with _lock:
        entry = _memory_tokens.get(key)
        if not entry:
            return None
        stored, expires_at = entry
        if time.time() > expires_at:
            _memory_tokens.pop(key, None)
            return None
        return stored


def store_reset_token(user_id: UUID) -> str:
    """Create and store a one-time reset token; return the raw token."""
    raw = create_reset_token()
    key = _token_key(hash_reset_token(raw))
    ttl = settings.password_reset_expire_minutes * 60
    _store_value(key, str(user_id), ttl)
    return raw


def consume_reset_token(raw_token: str) -> UUID | None:
    """Validate and consume a reset token. Returns user_id or None."""
    key = _token_key(hash_reset_token(raw_token.strip()))
    user_id_str = _consume_value(key)
    if not user_id_str:
        return None
    return UUID(user_id_str)


def store_reset_otp(*, user_id: UUID, mobile_number: str) -> str:
    """Create and store a one-time OTP for a mobile number; return the raw OTP."""
    otp = create_otp()
    key = _otp_key(mobile_number)
    ttl = settings.password_reset_expire_minutes * 60
    value = f"{user_id}:{hash_reset_token(otp)}"
    _store_value(key, value, ttl)
    return otp


def store_pending_sms_reset(*, user_id: UUID, mobile_number: str) -> None:
    """Remember which user requested an externally delivered OTP (e.g. Twilio Verify)."""
    key = _otp_key(mobile_number)
    ttl = settings.password_reset_expire_minutes * 60
    _store_value(key, f"{user_id}:external", ttl)


def consume_pending_sms_reset(*, mobile_number: str) -> UUID | None:
    """Consume a pending external-OTP reset and return the user id."""
    key = _otp_key(mobile_number)
    stored = _peek_value(key)
    if not stored or not stored.endswith(":external"):
        return None
    user_id_str = stored.split(":", 1)[0]
    _consume_value(key)
    return UUID(user_id_str)


def consume_reset_otp(*, mobile_number: str, otp: str) -> UUID | None:
    """Validate and consume a mobile OTP. Returns user_id or None.

    Wrong OTP does not consume the stored code (user can retry).
    """
    key = _otp_key(mobile_number)
    stored = _peek_value(key)
    if not stored or ":" not in stored:
        return None
    user_id_str, otp_hash = stored.split(":", 1)
    if otp_hash == "external":
        return None
    if hash_reset_token(otp.strip()) != otp_hash:
        return None
    _consume_value(key)
    return UUID(user_id_str)
