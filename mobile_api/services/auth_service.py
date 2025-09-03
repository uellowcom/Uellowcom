# -*- coding: utf-8 -*-
"""Authentication service implementation"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from ..core.security import SecurityManager
from ..schemas.auth_schemas import UserRegister, UserLogin, ResetPassword
from ..database.repositories.user_repository import UserRepository
from ..services.external_services.firebase_service import FirebaseService
from ..services.external_services.google_auth_service import GoogleAuthService
from ..services.external_services.facebook_auth_service import FacebookAuthService
from ..services.external_services.apple_auth_service import AppleAuthService
from ..services.cache_service import CacheService

logger = logging.getLogger(__name__)


class AuthService:
    """Handles all authentication business logic"""
    
    def __init__(self):
        self.user_repo = UserRepository()
        self.cache = CacheService()
        self.firebase = FirebaseService()
        self.google_auth = GoogleAuthService()
        self.facebook_auth = FacebookAuthService()
        self.apple_auth = AppleAuthService()
    
    async def register_user(self, user_data: UserRegister) -> Dict[str, Any]:
        """Register a new user"""
        # Check if user exists
        existing_user = await self.user_repo.get_by_email(user_data.email)
        if existing_user:
            raise ValueError("Email already registered")
        
        # Hash password
        hashed_password = SecurityManager.get_password_hash(user_data.password)
        
        # Create user
        user = await self.user_repo.create({
            "email": user_data.email,
            "password": hashed_password,
            "first_name": user_data.first_name,
            "last_name": user_data.last_name,
            "phone": user_data.phone,
            "is_verified": False,
            "created_at": datetime.utcnow()
        })
        
        # Generate tokens
        tokens = self._generate_tokens(user)
        
        # Send verification email
        await self._send_verification_email(user["email"])
        
        return {
            "user": user,
            "tokens": tokens,
            "message": "Registration successful. Please verify your email."
        }
    
    async def login(self, credentials: UserLogin) -> Dict[str, Any]:
        """Authenticate user with email and password"""
        # Get user
        user = await self.user_repo.get_by_email(credentials.email)
        if not user:
            raise ValueError("Invalid credentials")
        
        # Verify password
        if not SecurityManager.verify_password(credentials.password, user["password"]):
            raise ValueError("Invalid credentials")
        
        # Update last login
        await self.user_repo.update(user["id"], {
            "last_login": datetime.utcnow(),
            "device_id": credentials.device_id,
            "device_type": credentials.device_type
        })
        
        # Generate tokens
        tokens = self._generate_tokens(user)
        
        # Cache session
        await self.cache.set(
            f"session:{user['id']}",
            {"tokens": tokens, "device_id": credentials.device_id},
            expire=3600 * 24
        )
        
        return {
            "user": user,
            "tokens": tokens
        }
    
    async def logout(self, user_id: int):
        """Logout user and invalidate session"""
        await self.cache.delete(f"session:{user_id}")
        await self.user_repo.update(user_id, {"last_logout": datetime.utcnow()})
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Generate new access token from refresh token"""
        payload = SecurityManager.decode_token(refresh_token)
        
        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")
        
        user_id = payload.get("sub")
        user = await self.user_repo.get_by_id(user_id)
        
        if not user:
            raise ValueError("User not found")
        
        return self._generate_tokens(user)
    
    async def send_password_reset(self, email: str):
        """Send password reset email"""
        user = await self.user_repo.get_by_email(email)
        if not user:
            return  # Don't reveal if email exists
        
        # Generate reset token
        reset_token = SecurityManager.create_access_token(
            {"sub": user["id"], "email": email, "type": "password_reset"},
            expires_delta=timedelta(hours=1)
        )
        
        # Store token in cache
        await self.cache.set(
            f"password_reset:{user['id']}",
            reset_token,
            expire=3600
        )
        
        # Send email (implement email service)
        await self._send_reset_email(email, reset_token)
    
    async def reset_password(self, data: ResetPassword):
        """Reset user password with token"""
        payload = SecurityManager.decode_token(data.token)
        
        if payload.get("type") != "password_reset":
            raise ValueError("Invalid token")
        
        user_id = payload.get("sub")
        
        # Verify token in cache
        cached_token = await self.cache.get(f"password_reset:{user_id}")
        if cached_token != data.token:
            raise ValueError("Invalid or expired token")
        
        # Update password
        hashed_password = SecurityManager.get_password_hash(data.new_password)
        await self.user_repo.update(user_id, {"password": hashed_password})
        
        # Clear reset token
        await self.cache.delete(f"password_reset:{user_id}")
    
    async def send_firebase_sms(self, phone_number: str) -> str:
        """Send SMS verification via Firebase"""
        return await self.firebase.send_sms_verification(phone_number)
    
    async def verify_firebase_sms(self, phone_number: str, code: str, verification_id: str) -> Dict[str, Any]:
        """Verify Firebase SMS code"""
        firebase_user = await self.firebase.verify_sms_code(phone_number, code, verification_id)
        
        # Get or create user
        user = await self.user_repo.get_by_phone(phone_number)
        if not user:
            user = await self.user_repo.create({
                "phone": phone_number,
                "firebase_uid": firebase_user["uid"],
                "is_verified": True,
                "created_at": datetime.utcnow()
            })
        
        tokens = self._generate_tokens(user)
        return {"user": user, "tokens": tokens}
    
    async def authenticate_firebase_token(self, firebase_token: str) -> Dict[str, Any]:
        """Authenticate with Firebase ID token"""
        firebase_user = await self.firebase.verify_id_token(firebase_token)
        
        # Get or create user
        user = await self.user_repo.get_by_firebase_uid(firebase_user["uid"])
        if not user:
            user = await self.user_repo.create({
                "email": firebase_user.get("email"),
                "firebase_uid": firebase_user["uid"],
                "is_verified": True,
                "created_at": datetime.utcnow()
            })
        
        tokens = self._generate_tokens(user)
        return {"user": user, "tokens": tokens}
    
    async def google_login(self, id_token: str) -> Dict[str, Any]:
        """Authenticate with Google"""
        google_user = await self.google_auth.verify_token(id_token)
        
        # Get or create user
        user = await self.user_repo.get_by_email(google_user["email"])
        if not user:
            user = await self.user_repo.create({
                "email": google_user["email"],
                "first_name": google_user.get("given_name"),
                "last_name": google_user.get("family_name"),
                "avatar_url": google_user.get("picture"),
                "google_id": google_user["sub"],
                "is_verified": True,
                "created_at": datetime.utcnow()
            })
        
        tokens = self._generate_tokens(user)
        return {"user": user, "tokens": tokens}
    
    async def facebook_login(self, access_token: str) -> Dict[str, Any]:
        """Authenticate with Facebook"""
        fb_user = await self.facebook_auth.verify_token(access_token)
        
        # Get or create user
        user = await self.user_repo.get_by_email(fb_user["email"])
        if not user:
            user = await self.user_repo.create({
                "email": fb_user["email"],
                "first_name": fb_user.get("first_name"),
                "last_name": fb_user.get("last_name"),
                "facebook_id": fb_user["id"],
                "is_verified": True,
                "created_at": datetime.utcnow()
            })
        
        tokens = self._generate_tokens(user)
        return {"user": user, "tokens": tokens}
    
    async def apple_login(self, id_token: str) -> Dict[str, Any]:
        """Authenticate with Apple"""
        apple_user = await self.apple_auth.verify_token(id_token)
        
        # Get or create user
        user = await self.user_repo.get_by_email(apple_user["email"])
        if not user:
            user = await self.user_repo.create({
                "email": apple_user["email"],
                "apple_id": apple_user["sub"],
                "is_verified": True,
                "created_at": datetime.utcnow()
            })
        
        tokens = self._generate_tokens(user)
        return {"user": user, "tokens": tokens}
    
    async def create_session_cookie(self, user_id: int) -> str:
        """Create session cookie for web authentication"""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise ValueError("User not found")
        
        session_token = SecurityManager.create_access_token(
            {"sub": user_id, "email": user["email"], "type": "session"},
            expires_delta=timedelta(days=7)
        )
        
        await self.cache.set(
            f"cookie_session:{user_id}",
            session_token,
            expire=3600 * 24 * 7
        )
        
        return session_token
    
    def _generate_tokens(self, user: Dict[str, Any]) -> Dict[str, Any]:
        """Generate access and refresh tokens"""
        access_token = SecurityManager.create_access_token({
            "sub": user["id"],
            "email": user["email"],
            "scopes": user.get("scopes", [])
        })
        
        refresh_token = SecurityManager.create_refresh_token({
            "sub": user["id"],
            "email": user["email"]
        })
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 1800  # 30 minutes
        }
    
    async def _send_verification_email(self, email: str):
        """Send email verification (implement email service)"""
        logger.info(f"Sending verification email to {email}")
        # TODO: Implement email service
    
    async def _send_reset_email(self, email: str, token: str):
        """Send password reset email"""
        logger.info(f"Sending password reset email to {email}")
        # TODO: Implement email service
