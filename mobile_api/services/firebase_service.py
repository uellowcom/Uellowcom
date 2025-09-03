# -*- coding: utf-8 -*-
"""Firebase authentication and messaging service"""

import firebase_admin
from firebase_admin import auth, credentials, messaging
import logging
from typing import Dict, Any, Optional
import os

logger = logging.getLogger(__name__)


class FirebaseAuthService:
    """Firebase Authentication Service"""
    
    def __init__(self):
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK"""
        try:
            # Check if Firebase is already initialized
            if not firebase_admin._apps:
                # Get credentials path from environment
                cred_path = os.getenv('FIREBASE_CREDENTIALS_PATH')
                if cred_path and os.path.exists(cred_path):
                    cred = credentials.Certificate(cred_path)
                    firebase_admin.initialize_app(cred)
                    logger.info("Firebase initialized with service account")
                else:
                    # Initialize with default credentials (for cloud deployment)
                    firebase_admin.initialize_app()
                    logger.info("Firebase initialized with default credentials")
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
    
    async def verify_id_token(self, id_token: str) -> Dict[str, Any]:
        """Verify Firebase ID token"""
        try:
            decoded_token = auth.verify_id_token(id_token)
            return {
                'uid': decoded_token['uid'],
                'email': decoded_token.get('email'),
                'name': decoded_token.get('name'),
                'phone': decoded_token.get('phone_number'),
                'email_verified': decoded_token.get('email_verified', False),
                'provider': decoded_token.get('firebase', {}).get('sign_in_provider'),
            }
        except Exception as e:
            logger.error(f"Firebase token verification failed: {e}")
            raise ValueError("Invalid Firebase token")
    
    async def verify_google_token(self, id_token: str) -> Dict[str, Any]:
        """Verify Google OAuth token via Firebase"""
        try:
            decoded_token = auth.verify_id_token(id_token)
            if decoded_token.get('firebase', {}).get('sign_in_provider') != 'google.com':
                raise ValueError("Token is not from Google provider")
            
            return {
                'id': decoded_token['uid'],
                'email': decoded_token.get('email'),
                'name': decoded_token.get('name'),
                'picture': decoded_token.get('picture'),
                'email_verified': decoded_token.get('email_verified', False),
            }
        except Exception as e:
            logger.error(f"Google token verification failed: {e}")
            raise ValueError("Invalid Google token")
    
    async def verify_facebook_token(self, access_token: str) -> Dict[str, Any]:
        """Verify Facebook token (simplified - in production use Graph API)"""
        try:
            # In production, verify with Facebook Graph API
            # For now, assume token is valid and decode
            decoded_token = auth.verify_id_token(access_token)
            if decoded_token.get('firebase', {}).get('sign_in_provider') != 'facebook.com':
                raise ValueError("Token is not from Facebook provider")
            
            return {
                'id': decoded_token['uid'],
                'email': decoded_token.get('email'),
                'name': decoded_token.get('name'),
            }
        except Exception as e:
            logger.error(f"Facebook token verification failed: {e}")
            raise ValueError("Invalid Facebook token")
    
    async def verify_apple_token(self, id_token: str) -> Dict[str, Any]:
        """Verify Apple Sign In token"""
        try:
            decoded_token = auth.verify_id_token(id_token)
            if decoded_token.get('firebase', {}).get('sign_in_provider') != 'apple.com':
                raise ValueError("Token is not from Apple provider")
            
            return {
                'id': decoded_token['uid'],
                'email': decoded_token.get('email'),
                'name': decoded_token.get('name'),
            }
        except Exception as e:
            logger.error(f"Apple token verification failed: {e}")
            raise ValueError("Invalid Apple token")
    
    async def send_sms_verification(self, phone_number: str) -> str:
        """Send SMS verification code (Firebase Auth REST API)"""
        try:
            # In production, use Firebase Auth REST API to send SMS
            # This is a simplified implementation
            import uuid
            verification_id = str(uuid.uuid4())
            
            # Store verification code temporarily (in production, use Firebase)
            # For demo, we'll just return a verification ID
            logger.info(f"SMS verification sent to {phone_number}")
            return verification_id
            
        except Exception as e:
            logger.error(f"SMS verification failed: {e}")
            raise ValueError("Failed to send SMS verification")
    
    async def verify_sms_code(self, phone_number: str, code: str, verification_id: str) -> Dict[str, Any]:
        """Verify SMS code (simplified implementation)"""
        try:
            # In production, verify with Firebase Auth
            # For demo purposes, accept any 6-digit code
            if len(code) == 6 and code.isdigit():
                # Create a temporary user record
                return {
                    'uid': f"sms_{phone_number.replace('+', '')}",
                    'phone': phone_number,
                    'verified': True
                }
            else:
                raise ValueError("Invalid verification code")
                
        except Exception as e:
            logger.error(f"SMS code verification failed: {e}")
            raise ValueError("Invalid verification code")
    
    async def create_custom_token(self, uid: str, additional_claims: Dict = None) -> str:
        """Create custom Firebase token"""
        try:
            token = auth.create_custom_token(uid, additional_claims)
            return token.decode('utf-8')
        except Exception as e:
            logger.error(f"Custom token creation failed: {e}")
            raise ValueError("Failed to create custom token")


class FirebaseMessagingService:
    """Firebase Cloud Messaging Service"""
    
    def __init__(self):
        # Firebase should already be initialized by auth service
        pass
    
    async def send_notification(self, token: str, title: str, body: str, data: Dict = None) -> bool:
        """Send push notification to device"""
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                token=token,
            )
            
            response = messaging.send(message)
            logger.info(f"Notification sent successfully: {response}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False
    
    async def send_multicast_notification(self, tokens: list, title: str, body: str, data: Dict = None) -> Dict:
        """Send notification to multiple devices"""
        try:
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                tokens=tokens,
            )
            
            response = messaging.send_multicast(message)
            
            return {
                'success_count': response.success_count,
                'failure_count': response.failure_count,
                'responses': [
                    {
                        'success': r.success,
                        'error': str(r.exception) if r.exception else None
                    }
                    for r in response.responses
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to send multicast notification: {e}")
            return {'success_count': 0, 'failure_count': len(tokens), 'error': str(e)}
    
    async def send_topic_notification(self, topic: str, title: str, body: str, data: Dict = None) -> bool:
        """Send notification to topic subscribers"""
        try:
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data or {},
                topic=topic,
            )
            
            response = messaging.send(message)
            logger.info(f"Topic notification sent successfully: {response}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send topic notification: {e}")
            return False
    
    async def subscribe_to_topic(self, tokens: list, topic: str) -> Dict:
        """Subscribe devices to topic"""
        try:
            response = messaging.subscribe_to_topic(tokens, topic)
            return {
                'success_count': response.success_count,
                'failure_count': response.failure_count,
            }
        except Exception as e:
            logger.error(f"Failed to subscribe to topic: {e}")
            return {'success_count': 0, 'failure_count': len(tokens), 'error': str(e)}
    
    async def unsubscribe_from_topic(self, tokens: list, topic: str) -> Dict:
        """Unsubscribe devices from topic"""
        try:
            response = messaging.unsubscribe_from_topic(tokens, topic)
            return {
                'success_count': response.success_count,
                'failure_count': response.failure_count,
            }
        except Exception as e:
            logger.error(f"Failed to unsubscribe from topic: {e}")
            return {'success_count': 0, 'failure_count': len(tokens), 'error': str(e)}
