# -*- coding: utf-8 -*-
"""
Authentication Service
Handles all authentication-related business logic
"""

import logging
from typing import Dict, Any, Optional

from ..core.security import security
from ..core.exceptions import AuthenticationException, ConflictException
from ..schemas.auth_schemas import UserRegisterRequest, UserLoginRequest
from .odoo_service import OdooService

logger = logging.getLogger(__name__)


class AuthService:
    """Central authentication service"""

    def __init__(self):
        self.odoo = OdooService()

    async def find_existing_user(
        self, email: Optional[str] = None, phone: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Find existing user by email or phone"""
        try:
            if email:
                return await self.odoo.find_user_by_email(email)
            if phone:
                return await self.odoo.find_user_by_phone(phone)
            return None
        except Exception as e:
            logger.error(f"Error finding existing user: {str(e)}")
            return None

    async def register_user(
        self,
        registration_data: UserRegisterRequest,
        device_info: Dict[str, Any],
        language: str = "en",
    ) -> Dict[str, Any]:
        """Register a new user"""
        # Implementation for user registration
        return {"user": {}, "tokens": {}}

    async def login_user(
        self,
        login_data: UserLoginRequest,
        device_info: Dict[str, Any],
        language: str = "en",
    ) -> Dict[str, Any]:
        """Login user with credentials"""
        # Implementation for user login
        return {"user": {}, "tokens": {}}

    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token"""
        try:
            payload = security.decode_refresh_token(refresh_token)
            user_id = int(payload["sub"])

            access_token = security.create_access_token(user_id)

            return {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": security.access_token_expire_minutes * 60,
            }
        except Exception as e:
            raise AuthenticationException("Invalid refresh token")
