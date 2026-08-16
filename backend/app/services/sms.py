from __future__ import annotations

import logging
from base64 import b64encode
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


def uses_twilio_verify() -> bool:
    return (
        (settings.sms_provider or "").strip().lower() == "twilio"
        and bool(settings.twilio_verify_service_sid.strip())
        and bool(settings.twilio_account_sid.strip())
        and bool(settings.twilio_auth_token.strip())
    )


def _e164_in(mobile_number: str) -> str:
    return mobile_number if mobile_number.startswith("+") else f"+91{mobile_number}"


def _twilio_auth_header() -> str:
    raw = f"{settings.twilio_account_sid}:{settings.twilio_auth_token}".encode("utf-8")
    return "Basic " + b64encode(raw).decode("ascii")


def send_password_reset_sms(*, mobile_number: str, otp: str | None = None) -> None:
    """Send a password-reset OTP by SMS, or log it when no SMS provider is configured."""
    minutes = settings.password_reset_expire_minutes
    provider = (settings.sms_provider or "").strip().lower()

    if not provider:
        logger.info(
            "SMS not configured; password reset OTP for %s: %s",
            mobile_number,
            otp or "(none)",
        )
        return

    if provider == "fast2sms":
        if not otp:
            raise RuntimeError("Fast2SMS requires a local OTP value.")
        _send_fast2sms(mobile_number=mobile_number, otp=otp)
        return

    if provider == "twilio":
        if uses_twilio_verify():
            _send_twilio_verify(mobile_number=mobile_number)
            return
        if not otp:
            raise RuntimeError("Twilio Messages API requires a local OTP value.")
        message = (
            f"Your Assistify password reset code is {otp}. "
            f"It expires in {minutes} minutes. Do not share this code."
        )
        _send_twilio_message(mobile_number=mobile_number, body=message)
        return

    logger.warning("Unknown SMS provider %r; logging OTP for %s", provider, mobile_number)
    logger.info("Password reset OTP for %s: %s", mobile_number, otp or "(none)")


def check_password_reset_otp(*, mobile_number: str, otp: str) -> bool:
    """Validate an OTP with an external provider when configured."""
    if uses_twilio_verify():
        return _check_twilio_verify(mobile_number=mobile_number, otp=otp)
    return False


def _send_fast2sms(*, mobile_number: str, otp: str) -> None:
    if not settings.sms_api_key:
        raise RuntimeError("FAST2SMS requires SMS_API_KEY.")
    query = urlencode(
        {
            "authorization": settings.sms_api_key,
            "route": "otp",
            "variables_values": otp,
            "flash": "0",
            "numbers": mobile_number,
        }
    )
    url = f"https://www.fast2sms.com/dev/bulkV2?{query}"
    request = Request(url, method="GET")
    with urlopen(request, timeout=20) as response:  # noqa: S310
        body = response.read().decode("utf-8", errors="replace")
        if response.status >= 400:
            raise RuntimeError(f"Fast2SMS failed ({response.status}): {body}")
    logger.info("Password reset SMS (Fast2SMS) sent to %s", mobile_number)


def _send_twilio_message(*, mobile_number: str, body: str) -> None:
    if not (
        settings.twilio_account_sid
        and settings.twilio_auth_token
        and settings.twilio_from_number
    ):
        raise RuntimeError(
            "Twilio Messages API requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, "
            "and TWILIO_FROM_NUMBER. Trial accounts should set TWILIO_VERIFY_SERVICE_SID instead."
        )

    to_number = _e164_in(mobile_number)
    form = urlencode(
        {
            "To": to_number,
            "From": settings.twilio_from_number,
            "Body": body,
        }
    ).encode("utf-8")
    url = f"https://api.twilio.com/2010-04-01/Accounts/{settings.twilio_account_sid}/Messages.json"
    request = Request(
        url,
        data=form,
        method="POST",
        headers={
            "Authorization": _twilio_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:  # noqa: S310
            response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Twilio failed ({exc.code}): {detail}") from exc
    logger.info("Password reset SMS (Twilio Messages) sent to %s", to_number)


def _send_twilio_verify(*, mobile_number: str) -> None:
    to_number = _e164_in(mobile_number)
    form = urlencode({"To": to_number, "Channel": "sms"}).encode("utf-8")
    url = (
        "https://verify.twilio.com/v2/Services/"
        f"{settings.twilio_verify_service_sid}/Verifications"
    )
    request = Request(
        url,
        data=form,
        method="POST",
        headers={
            "Authorization": _twilio_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:  # noqa: S310
            response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Twilio Verify send failed ({exc.code}): {detail}") from exc
    logger.info("Password reset SMS (Twilio Verify) sent to %s", to_number)


def _check_twilio_verify(*, mobile_number: str, otp: str) -> bool:
    to_number = _e164_in(mobile_number)
    form = urlencode({"To": to_number, "Code": otp.strip()}).encode("utf-8")
    url = (
        "https://verify.twilio.com/v2/Services/"
        f"{settings.twilio_verify_service_sid}/VerificationCheck"
    )
    request = Request(
        url,
        data=form,
        method="POST",
        headers={
            "Authorization": _twilio_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:  # noqa: S310
            import json

            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        logger.warning("Twilio Verify check failed (%s): %s", exc.code, detail)
        return False
    status = str(payload.get("status", "")).lower()
    ok = status == "approved"
    if ok:
        logger.info("Twilio Verify approved for %s", to_number)
    else:
        logger.info("Twilio Verify status for %s: %s", to_number, status)
    return ok
