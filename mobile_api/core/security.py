# -*- coding: utf-8 -*-
"""
Security utilities and authentication handlers
JWT token management, password hashing, and auth dependencies
"""

import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from passlib.context import CryptContext
from passlib.handlers.pbkdf2 import pbkdf2_sha256

from .config import get_settings
from .exceptions import AuthenticationException, AuthorizationException

# Initialize settings
settings = get_settings()

# Password context for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer scheme for JWT
bearer_scheme = HTTPBearer(auto_error=False)


class SecurityManager:
    """Central security manager for authentication and authorization"""

    def __init__(self):
        self.settings = settings
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire_minutes = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire_days = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS

    # Password utilities
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt"""
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash"""
        return pwd_context.verify(plain_password, hashed_password)

    def generate_password(self, length: int = 12) -> str:
        """Generate a secure random password"""
        alphabet = (
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*"
        )
        return "".join(secrets.choice(alphabet) for _ in range(length))

    # Token utilities
    def create_access_token(
        self, user_id: int, additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a JWT access token"""
        now = datetime.utcnow()
        expire = now + timedelta(minutes=self.access_token_expire_minutes)

        payload = {
            "sub": str(user_id),
            "iat": now.timestamp(),
            "exp": expire.timestamp(),
            "type": "access",
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
        }

        if additional_claims:
            payload.update(additional_claims)

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, user_id: int) -> str:
        """Create a JWT refresh token"""
        now = datetime.utcnow()
        expire = now + timedelta(days=self.refresh_token_expire_days)

        payload = {
            "sub": str(user_id),
            "iat": now.timestamp(),
            "exp": expire.timestamp(),
            "type": "refresh",
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate a JWT token"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience=settings.JWT_AUDIENCE,
                issuer=settings.JWT_ISSUER,
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationException("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationException("Invalid token")

    def decode_refresh_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate a refresh token"""
        payload = self.decode_token(token)

        if payload.get("type") != "refresh":
            raise AuthenticationException("Invalid refresh token")

        return payload

    def create_reset_token(self, user_id: int, expire_minutes: int = 15) -> str:
        """Create a password reset token"""
        now = datetime.utcnow()
        expire = now + timedelta(minutes=expire_minutes)

        payload = {
            "sub": str(user_id),
            "iat": now.timestamp(),
            "exp": expire.timestamp(),
            "type": "reset",
            "iss": settings.JWT_ISSUER,
            "aud": settings.JWT_AUDIENCE,
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_reset_token(self, token: str) -> Dict[str, Any]:
        """Decode and validate a password reset token"""
        payload = self.decode_token(token)

        if payload.get("type") != "reset":
            raise AuthenticationException("Invalid reset token")

        return payload

    # Authentication dependencies
    async def get_current_user(
        self, credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)
    ) -> Dict[str, Any]:
        """Get current authenticated user from JWT token"""
        if not credentials:
            raise AuthenticationException("Authentication credentials required")

        try:
            payload = self.decode_token(credentials.credentials)
            user_id = payload.get("sub")

            if not user_id:
                raise AuthenticationException("Invalid token payload")

            # Here you would typically fetch user from database
            # For now, we'll return the payload with user_id
            return {"user_id": int(user_id), "token_payload": payload}

        except AuthenticationException:
            raise
        except Exception as e:
            raise AuthenticationException(f"Token validation failed: {str(e)}")

    async def get_current_active_user(
        self, current_user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """Get current active user (extend with database check)"""
        # Here you would check if user is active in database
        # For now, we'll assume user is active
        return current_user

    async def get_optional_current_user(
        self,
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    ) -> Optional[Dict[str, Any]]:
        """Get current user if authenticated, None otherwise"""
        if not credentials:
            return None

        try:
            return await self.get_current_user(credentials)
        except AuthenticationException:
            return None

    # Utility functions
    def generate_api_key(self, user_id: int, length: int = 32) -> str:
        """Generate an API key for a user"""
        timestamp = str(int(datetime.utcnow().timestamp()))
        user_str = str(user_id)
        random_part = secrets.token_hex(length // 2)

        raw_key = f"{user_str}:{timestamp}:{random_part}"
        api_key = hashlib.sha256(raw_key.encode()).hexdigest()[:length]

        return f"ym_{api_key}"

    def validate_api_key(self, api_key: str) -> bool:
        """Validate an API key format"""
        return api_key.startswith("ym_") and len(api_key) == 35  # ym_ + 32 chars

    def generate_session_id(self) -> str:
        """Generate a secure session ID"""
        return secrets.token_urlsafe(32)

    def generate_verification_code(self, length: int = 6) -> str:
        """Generate a numeric verification code"""
        return "".join(secrets.choice("0123456789") for _ in range(length))


# Create global security manager instance
security = SecurityManager()


# Convenience dependency functions
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Dict[str, Any]:
    """Dependency to get current authenticated user"""
    return await security.get_current_user(credentials)


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Dependency to get current active user"""
    return await security.get_current_active_user(current_user)


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[Dict[str, Any]]:
    """Dependency to optionally get current user"""
    return await security.get_optional_current_user(credentials)


# Permission checking utilities
class PermissionChecker:
    """Permission checking utilities"""

    def __init__(self, required_permissions: Union[str, list] = None):
        self.required_permissions = (
            required_permissions
            if isinstance(required_permissions, list)
            else [required_permissions] if required_permissions else []
        )

    def __call__(
        self, current_user: Dict[str, Any] = Depends(get_current_user)
    ) -> Dict[str, Any]:
        """Check if user has required permissions"""
        # Here you would implement permission checking logic
        # For now, we'll just return the user

        if self.required_permissions:
            # Implement permission checking logic here
            user_permissions = current_user.get("permissions", [])
            for permission in self.required_permissions:
                if permission not in user_permissions:
                    raise AuthorizationException(f"Required permission: {permission}")

        return current_user


def require_permissions(*permissions) -> PermissionChecker:
    """Create a permission checker dependency"""
    return PermissionChecker(list(permissions))


# Rate limiting utilities
class RateLimiter:
    """Simple in-memory rate limiter"""

    def __init__(self):
        self.requests = {}

    def is_allowed(self, identifier: str, limit: int = 60, window: int = 60) -> bool:
        """Check if request is within rate limit"""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window)

        # Clean old entries
        if identifier in self.requests:
            self.requests[identifier] = [
                req_time
                for req_time in self.requests[identifier]
                if req_time > window_start
            ]
        else:
            self.requests[identifier] = []

        # Check limit
        if len(self.requests[identifier]) >= limit:
            return False

        # Add current request
        self.requests[identifier].append(now)
        return True


# Global rate limiter
rate_limiter = RateLimiter()

# Export main components
__all__ = [
    "SecurityManager",
    "security",
    "get_current_user",
    "get_current_active_user",
    "get_optional_current_user",
    "PermissionChecker",
    "require_permissions",
    "RateLimiter",
    "rate_limiter",
]
