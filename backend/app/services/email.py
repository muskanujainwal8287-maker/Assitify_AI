from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from backend.app.core.config import settings

logger = logging.getLogger(__name__)


def send_password_reset_email(*, to_email: str, reset_url: str) -> None:
    """Send a password-reset email, or log the link when SMTP is not configured."""
    subject = "Reset your AssistifyAI Account password"
    body = (
        "We received a request to reset your AssistifyAI account password.\n\n"
        f"Open this link to choose a new password (expires in "
        f"{settings.password_reset_expire_minutes} minutes):\n\n"
        f"{reset_url}\n\n"
        "If you did not request this, you can ignore this email.\n"
    )

    if not settings.smtp_host:
        logger.info(
            "SMTP not configured; password reset link for %s: %s",
            to_email,
            reset_url,
        )
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.smtp_from or settings.smtp_user or "noreply@assistify.local"
    message["To"] = to_email
    message.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_user:
                smtp.login(settings.smtp_user, settings.smtp_password)
            smtp.send_message(message)
        logger.info("Password reset email sent to %s", to_email)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to send password reset email to %s: %s", to_email, exc)
        raise
