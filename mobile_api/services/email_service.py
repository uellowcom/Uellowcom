# -*- coding: utf-8 -*-
"""
Email Service
Handles email sending functionality
"""

import logging
from typing import Dict, Any, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ..core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails"""

    def __init__(self):
        self.smtp_available = bool(settings.SMTP_HOST and settings.FROM_EMAIL)

    async def send_verification_email(self, email: str, token: str):
        """Send email verification"""
        if not self.smtp_available:
            logger.warning("SMTP not configured - email not sent")
            return

        try:
            verification_url = f"{settings.API_BASE_URL}/verify-email?token={token}"

            subject = "Verify your email address"
            html_body = f"""
            <html>
                <body>
                    <h2>Email Verification</h2>
                    <p>Please click the link below to verify your email address:</p>
                    <a href="{verification_url}">Verify Email</a>
                    <p>If you didn't request this, please ignore this email.</p>
                </body>
            </html>
            """

            await self._send_email(email, subject, html_body)
            logger.info(f"Verification email sent to {email}")

        except Exception as e:
            logger.error(f"Failed to send verification email: {str(e)}")

    async def _send_email(self, to_email: str, subject: str, html_body: str):
        """Send email via SMTP"""
        if not self.smtp_available:
            return

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.FROM_EMAIL
            msg["To"] = to_email

            html_part = MIMEText(html_body, "html")
            msg.attach(html_part)

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                if settings.SMTP_USERNAME:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)

        except Exception as e:
            logger.error(f"SMTP error: {str(e)}")
            raise
