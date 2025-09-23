# -*- coding: utf-8 -*-
"""
SMS Service
Handles SMS sending functionality
"""

import logging
from typing import Optional

from ..core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Try to import Twilio SDK
try:
    from twilio.rest import Client

    TWILIO_AVAILABLE = True
except ImportError:
    TWILIO_AVAILABLE = False
    logger.warning("Twilio SDK not available")


class SMSService:
    """Service for sending SMS"""

    def __init__(self):
        self.twilio_available = (
            TWILIO_AVAILABLE
            and settings.TWILIO_ACCOUNT_SID
            and settings.TWILIO_AUTH_TOKEN
        )
        self.client = None

        if self.twilio_available:
            self.client = Client(
                settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN
            )

    async def send_verification_sms(self, phone: str, code: str):
        """Send SMS verification code"""
        if not self.twilio_available:
            logger.warning("SMS not configured - SMS not sent")
            return

        try:
            message = f"Your verification code is: {code}"

            self.client.messages.create(
                body=message, from_=settings.TWILIO_PHONE_NUMBER, to=phone
            )

            logger.info(f"Verification SMS sent to {phone}")

        except Exception as e:
            logger.error(f"Failed to send SMS: {str(e)}")
            raise
