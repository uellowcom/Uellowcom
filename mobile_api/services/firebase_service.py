# -*- coding: utf-8 -*-
"""
Firebase Integration Service
Handles Firebase authentication and notifications
"""

import logging
from typing import Dict, Any, Optional

from ..core.config import get_settings
from ..core.exceptions import external_service_error

settings = get_settings()
logger = logging.getLogger(__name__)

# Try to import Firebase SDK
try:
    import firebase_admin
    from firebase_admin import auth, credentials

    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logger.warning("Firebase SDK not available")


class FirebaseService:
    """Service for Firebase integration"""

    def __init__(self):
        self.firebase_available = FIREBASE_AVAILABLE and settings.FIREBASE_PROJECT_ID
        self.app = None

        if self.firebase_available:
            self._initialize_firebase()

    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            if not firebase_admin._apps:
                if settings.FIREBASE_CREDENTIALS_PATH:
                    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                    self.app = firebase_admin.initialize_app(cred)
                else:
                    # Use default credentials
                    self.app = firebase_admin.initialize_app()

                logger.info("Firebase initialized successfully")
            else:
                self.app = firebase_admin.get_app()
        except Exception as e:
            logger.error(f"Firebase initialization failed: {str(e)}")
            self.firebase_available = False

    async def send_sms_verification(self, phone_number: str) -> str:
        """Send SMS verification code"""
        if not self.firebase_available:
            # Mock implementation for testing
            return "mock-verification-id"

        try:
            # In a real implementation, you'd use Firebase Auth to send SMS
            # This is a mock implementation
            verification_id = f"verify_{phone_number}_{hash(phone_number) % 10000}"
            logger.info(f"SMS verification sent to {phone_number}")
            return verification_id
        except Exception as e:
            logger.error(f"Failed to send SMS verification: {str(e)}")
            raise external_service_error("firebase", "SMS sending failed")

    async def verify_sms_code(self, verification_id: str, code: str) -> bool:
        """Verify SMS code"""
        if not self.firebase_available:
            # Mock verification - accept any 6-digit code
            return len(code) == 6 and code.isdigit()

        try:
            # In a real implementation, you'd verify with Firebase
            # Mock implementation for now
            return len(code) == 6 and code.isdigit()
        except Exception as e:
            logger.error(f"SMS verification failed: {str(e)}")
            return False

    async def verify_id_token(self, id_token: str) -> Optional[Dict[str, Any]]:
        """Verify Firebase ID token"""
        if not self.firebase_available:
            return None

        try:
            decoded_token = auth.verify_id_token(id_token)
            return decoded_token
        except Exception as e:
            logger.error(f"Token verification failed: {str(e)}")
            return None
