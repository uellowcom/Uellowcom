# -*- coding: utf-8 -*-
"""Mobile Authentication Router using Odoo models and Firebase"""

from typing import Annotated, Optional
from datetime import datetime, timedelta
import logging

from odoo.api import Environment
from odoo.exceptions import ValidationError, AccessError
from odoo.addons.base.models.res_partner import Partner

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field

from ..dependencies import odoo_env, firebase_auth
from ..services.firebase_service import FirebaseService
from ..services.jwt_service import JWTService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mobile/v1/auth", tags=["Mobile Authentication"])
security = HTTPBearer()


# Pydantic Models for Request/Response
class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1)
    phone: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    device_id: Optional[str] = None
    device_type: Optional[str] = Field(None, pattern=r"^(ios|android)$")


class FirebaseSMSAuth(BaseModel):
    phone_number: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")
    verification_code: Optional[str] = None
    verification_id: Optional[str] = None


class SocialLogin(BaseModel):
    provider: str = Field(..., pattern=r"^(google|facebook|apple)$")
    id_token: str
    device_info: Optional[dict] = None


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: dict


@router.post("/register", response_model=AuthResponse)
async def register(
    env: Annotated[Environment, Depends(odoo_env)], user_data: UserRegister
):
    """Register a new user with email and password"""
    try:
        # Check if user already exists
        existing_user = env["res.partner"].search(
            [("email", "=", user_data.email)], limit=1
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Create new user
        partner_vals = {
            "name": user_data.name,
            "email": user_data.email,
            "phone": user_data.phone,
            "is_company": False,
            "customer_rank": 1,
            "mobile_verified": False,
        }

        # Create user with password
        user = env["res.users"].create(
            {
                "partner_id": env["res.partner"].create(partner_vals).id,
                "login": user_data.email,
                "password": user_data.password,
            }
        )

        # Generate JWT tokens
        jwt_service = JWTService()
        tokens = jwt_service.create_tokens(user.partner_id.id, user_data.email)

        return AuthResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_in=1800,  # 30 minutes
            user={
                "id": user.partner_id.id,
                "name": user.partner_id.name,
                "email": user.partner_id.email,
                "phone": user.partner_id.phone,
                "mobile_verified": user.partner_id.mobile_verified,
            },
        )

    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/login", response_model=AuthResponse)
async def login(env: Annotated[Environment, Depends(odoo_env)], credentials: UserLogin):
    """Login with email and password"""
    try:
        # Authenticate user
        user_id = env["res.users"].authenticate(
            env.cr.dbname, credentials.email, credentials.password, {}
        )

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )

        user = env["res.users"].browse(user_id)
        partner = user.partner_id

        # Register device if provided
        if credentials.device_id:
            env["mobile.device"].register_device(
                partner.id,
                {
                    "device_id": credentials.device_id,
                    "device_type": credentials.device_type,
                },
            )

        # Update last login
        partner.mobile_last_login = datetime.now()

        # Generate JWT tokens
        jwt_service = JWTService()
        tokens = jwt_service.create_tokens(partner.id, partner.email)

        return AuthResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_in=1800,
            user={
                "id": partner.id,
                "name": partner.name,
                "email": partner.email,
                "phone": partner.phone,
                "mobile_verified": partner.mobile_verified,
                "wallet_balance": partner.wallet_balance,
            },
        )

    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
        )


@router.post("/firebase/sms")
async def firebase_sms_auth(
    env: Annotated[Environment, Depends(odoo_env)], data: FirebaseSMSAuth
):
    """Authenticate using Firebase SMS"""
    try:
        firebase_service = FirebaseService()

        if data.verification_code:
            # Verify the SMS code
            firebase_user = await firebase_service.verify_sms_code(
                data.phone_number, data.verification_code, data.verification_id
            )

            # Find or create user
            partner = env["res.partner"].find_or_create_by_firebase(
                firebase_user["uid"],
                {
                    "name": f"User {data.phone_number}",
                    "phone": data.phone_number,
                },
            )

            # Generate JWT tokens
            jwt_service = JWTService()
            tokens = jwt_service.create_tokens(
                partner.id, partner.email or data.phone_number
            )

            return AuthResponse(
                access_token=tokens["access_token"],
                refresh_token=tokens["refresh_token"],
                expires_in=1800,
                user={
                    "id": partner.id,
                    "name": partner.name,
                    "phone": partner.phone,
                    "mobile_verified": True,
                    "wallet_balance": partner.wallet_balance,
                },
            )
        else:
            # Send SMS verification code
            verification_id = await firebase_service.send_sms_verification(
                data.phone_number
            )
            return {"verification_id": verification_id, "message": "SMS sent"}

    except Exception as e:
        logger.error(f"Firebase SMS auth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="SMS authentication failed"
        )


@router.post("/social/{provider}", response_model=AuthResponse)
async def social_login(
    env: Annotated[Environment, Depends(odoo_env)], provider: str, data: SocialLogin
):
    """Login with social providers (Google, Facebook, Apple)"""
    try:
        firebase_service = FirebaseService()

        # Verify social login token
        if provider == "google":
            user_data = await firebase_service.verify_google_token(data.id_token)
        elif provider == "facebook":
            user_data = await firebase_service.verify_facebook_token(data.id_token)
        elif provider == "apple":
            user_data = await firebase_service.verify_apple_token(data.id_token)
        else:
            raise HTTPException(status_code=400, detail="Invalid provider")

        # Find or create user
        partner = env["res.partner"].find_or_create_by_social(
            provider,
            user_data["id"],
            {
                "name": user_data.get("name", f"{provider.title()} User"),
                "email": user_data.get("email"),
            },
        )

        # Generate JWT tokens
        jwt_service = JWTService()
        tokens = jwt_service.create_tokens(partner.id, partner.email)

        return AuthResponse(
            access_token=tokens["access_token"],
            refresh_token=tokens["refresh_token"],
            expires_in=1800,
            user={
                "id": partner.id,
                "name": partner.name,
                "email": partner.email,
                "mobile_verified": True,
                "wallet_balance": partner.wallet_balance,
            },
        )

    except Exception as e:
        logger.error(f"Social login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{provider.title()} authentication failed",
        )


@router.post("/refresh")
async def refresh_token(
    env: Annotated[Environment, Depends(odoo_env)], refresh_token: str
):
    """Refresh access token"""
    try:
        jwt_service = JWTService()
        new_tokens = jwt_service.refresh_access_token(refresh_token)
        return new_tokens
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )


@router.post("/logout")
async def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    env: Annotated[Environment, Depends(odoo_env)],
):
    """Logout current user"""
    try:
        jwt_service = JWTService()
        payload = jwt_service.decode_token(credentials.credentials)
        partner_id = payload.get("sub")

        if partner_id:
            partner = env["res.partner"].browse(int(partner_id))
            partner.mobile_last_login = datetime.now()

        return {"message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Logout error: {e}")
        return {"message": "Logged out"}


# Dependency to get current authenticated user
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    env: Annotated[Environment, Depends(odoo_env)],
) -> Partner:
    """Get current authenticated user from JWT token"""
    try:
        jwt_service = JWTService()
        payload = jwt_service.decode_token(credentials.credentials)
        partner_id = payload.get("sub")

        if not partner_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )

        partner = env["res.partner"].browse(int(partner_id))
        if not partner.exists():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
            )

        return partner
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication failed"
        )
