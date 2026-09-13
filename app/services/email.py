import logging
from email.message import EmailMessage

import aiosmtplib

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    async def send_otp(self, recipient: str, code: str, purpose: str) -> None:
        label = "verify your email" if purpose == "email_verification" else "reset your password"
        subject = f"{settings.app_name}: {label.title()}"
        body = f"Use code {code} to {label}. It expires in 10 minutes."

        if not settings.smtp_host:
            logger.warning("SMTP not configured; email to %s: %s", recipient, body)
            return

        message = EmailMessage()
        message["From"] = f"{settings.smtp_from_name} <{settings.smtp_from_email}>"
        message["To"] = recipient
        message["Subject"] = subject
        message.set_content(body)
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            start_tls=settings.smtp_use_tls,
        )


email_service = EmailService()
