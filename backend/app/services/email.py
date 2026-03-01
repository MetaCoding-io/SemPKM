"""Async email delivery service for SemPKM.

Uses aiosmtplib for non-blocking SMTP delivery. Falls back gracefully
when SMTP is not configured (send functions return False).
"""

import logging
from email.message import EmailMessage

import aiosmtplib

from app.config import settings

logger = logging.getLogger(__name__)


async def send_magic_link_email(email: str, token: str, base_url: str) -> bool:
    """Send a magic link login email via SMTP.

    Constructs an email with the verification URL and sends it via the
    configured SMTP server. Returns True if sent successfully, False
    on error (logged, not raised). Caller handles the fallback.

    Args:
        email: Recipient email address.
        token: Magic link verification token.
        base_url: Application base URL (e.g., http://localhost:3000).

    Returns:
        True if sent successfully, False on error.
    """
    if not settings.smtp_host:
        logger.debug("SMTP not configured, skipping email send")
        return False

    message = EmailMessage()
    message["From"] = settings.smtp_from_email or f"noreply@{settings.smtp_host}"
    message["To"] = email
    message["Subject"] = "SemPKM Login Link"

    verify_url = f"{base_url}/login.html?token={token}"
    message.set_content(
        f"Click the link below to log in to SemPKM:\n\n{verify_url}\n\n"
        "This link expires in 10 minutes.\n\n"
        "If you did not request this link, you can safely ignore this email."
    )

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user or None,
            password=settings.smtp_password or None,
            start_tls=True,
        )
        logger.info("Magic link email sent to %s", email)
        return True
    except aiosmtplib.SMTPException:
        logger.error("Failed to send magic link email to %s", email, exc_info=True)
        return False
