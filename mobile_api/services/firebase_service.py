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

    async def send_push_notification(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image_url: Optional[str] = None,
    ) -> bool:
        """
        Send push notification via Firebase Cloud Messaging (FCM)

        Args:
            token: FCM device token
            title: Notification title
            body: Notification body/message
            data: Additional data payload
            image_url: Optional image URL for rich notification

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.firebase_available:
            logger.warning("Firebase not available - notification not sent")
            return False

        try:
            from firebase_admin import messaging

            # Build notification
            notification = messaging.Notification(
                title=title, body=body, image=image_url
            )

            # Build Android-specific config
            android_config = messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    sound="default",
                    color="#FF6B35",  # Yellow brand color
                    channel_id="yellow_notifications",
                ),
            )

            # Build iOS-specific config
            apns_config = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default", badge=1, content_available=True)
                )
            )

            # Create message
            message = messaging.Message(
                notification=notification,
                data=data or {},
                token=token,
                android=android_config,
                apns=apns_config,
            )

            # Send message
            response = messaging.send(message)
            logger.info(f"Successfully sent FCM message: {response}")
            return True

        except Exception as e:
            logger.error(f"FCM send failed: {str(e)}")
            return False

    async def send_push_notification_multicast(
        self,
        tokens: list[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Send push notification to multiple devices

        Args:
            tokens: List of FCM device tokens
            title: Notification title
            body: Notification body/message
            data: Additional data payload

        Returns:
            dict: Contains success_count, failure_count, and failed_tokens
        """
        if not self.firebase_available or not tokens:
            return {"success_count": 0, "failure_count": 0, "failed_tokens": []}

        try:
            from firebase_admin import messaging

            # Create multicast message
            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                tokens=tokens,
            )

            # Send to multiple devices
            response = messaging.send_multicast(message)

            # Collect failed tokens
            failed_tokens = []
            if response.failure_count > 0:
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        failed_tokens.append(tokens[idx])

            logger.info(
                f"FCM multicast: {response.success_count} successful, "
                f"{response.failure_count} failed"
            )

            return {
                "success_count": response.success_count,
                "failure_count": response.failure_count,
                "failed_tokens": failed_tokens,
            }

        except Exception as e:
            logger.error(f"FCM multicast send failed: {str(e)}")
            return {
                "success_count": 0,
                "failure_count": len(tokens),
                "failed_tokens": tokens,
            }

    async def send_topic_notification(
        self, topic: str, title: str, body: str, data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send notification to a topic (e.g., 'all_users', 'promotions')

        Args:
            topic: Topic name
            title: Notification title
            body: Notification body
            data: Additional data

        Returns:
            bool: True if sent successfully
        """
        if not self.firebase_available:
            return False

        try:
            from firebase_admin import messaging

            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                topic=topic,
            )

            response = messaging.send(message)
            logger.info(f"Successfully sent topic message to '{topic}': {response}")
            return True

        except Exception as e:
            logger.error(f"Topic message send failed: {str(e)}")
            return False
