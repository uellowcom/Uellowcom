# -*- coding: utf-8 -*-
"""
Authentication API Endpoints
Consolidated authentication system with multiple providers
"""

import logging
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPBearer

from ....core.exceptions import (
    AuthenticationException,
    ValidationException,
    ConflictException,
    BusinessRuleException,
    external_service_error,
)
from ....schemas.auth_schemas import (
    UserRegisterRequest,
    UserLoginRequest,
    SocialLoginRequest,
    FirebaseSMSRequest,
    PasswordResetRequest,
    PasswordUpdateRequest,
    RefreshTokenRequest,
    AuthResponse,
    TokenResponse,
    UserProfileResponse,
    VerificationRequest,
    ResendVerificationRequest,
)
from ....services.auth_service import AuthService
from ....services.firebase_service import FirebaseService
from ....services.odoo_service import OdooService
from ..dependencies import get_device_info, validate_language, require_authentication

# Initialize logger and services
logger = logging.getLogger(__name__)
router = APIRouter()

# HTTP Bearer scheme
bearer_scheme = HTTPBearer(auto_error=False)


@router.post(
    "/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    request: UserRegisterRequest,
    device_info: Dict[str, Any] = Depends(get_device_info),
    lang: str = Depends(validate_language),
):
    """
    Register a new user account

    Supports multiple registration methods:
    - Email and password
    - Phone number with SMS verification
    - Social provider registration
    """
    auth_service = AuthService()

    try:
        # Check if user already exists
        existing_user = await auth_service.find_existing_user(
            email=request.email, phone=request.phone
        )

        if existing_user:
            if existing_user.get("email") == request.email:
                raise ConflictException("Email address already registered")
            if existing_user.get("phone") == request.phone:
                raise ConflictException("Phone number already registered")

        # Create user account
        result = await auth_service.register_user(
            registration_data=request, device_info=device_info, language=lang
        )

        logger.info(f"New user registered: {result['user']['id']} - {request.email}")

        return AuthResponse(
            success=True,
            message="Registration successful",
            user=result["user"],
            tokens=result["tokens"],
            requires_verification=result.get("requires_verification", False),
        )

    except ConflictException:
        raise
    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Registration error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed. Please try again.",
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    request: UserLoginRequest,
    device_info: Dict[str, Any] = Depends(get_device_info),
    lang: str = Depends(validate_language),
):
    """
    Login with email/phone and password

    Supports:
    - Email and password
    - Phone and password
    - Remember me functionality
    """
    auth_service = AuthService()

    try:
        result = await auth_service.login_user(
            login_data=request, device_info=device_info, language=lang
        )

        logger.info(f"User logged in: {result['user']['id']} - {request.identifier}")

        return AuthResponse(
            success=True,
            message="Login successful",
            user=result["user"],
            tokens=result["tokens"],
            requires_verification=result.get("requires_verification", False),
        )

    except AuthenticationException as e:
        logger.warning(f"Login failed for {request.identifier}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )
    except BusinessRuleException as e:
        # Handle business rules like account suspension
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except Exception as e:
        logger.error(f"Login error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed. Please try again.",
        )


@router.post("/social/{provider}", response_model=AuthResponse)
async def social_login(
    provider: str,
    request: SocialLoginRequest,
    device_info: Dict[str, Any] = Depends(get_device_info),
    lang: str = Depends(validate_language),
):
    """
    Social login with various providers

    Supported providers:
    - google
    - facebook
    - apple
    - twitter (if configured)
    """
    if provider not in ["google", "facebook", "apple", "twitter"]:
        raise ValidationException("Unsupported social provider")

    auth_service = AuthService()

    try:
        result = await auth_service.social_login(
            provider=provider,
            token=request.token,
            device_info=device_info,
            language=lang,
        )

        logger.info(f"Social login successful: {provider} - {result['user']['id']}")

        return AuthResponse(
            success=True,
            message=f"{provider.title()} login successful",
            user=result["user"],
            tokens=result["tokens"],
        )

    except AuthenticationException as e:
        logger.warning(f"Social login failed for {provider}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"{provider.title()} authentication failed",
        )
    except Exception as e:
        logger.error(f"Social login error for {provider}: {str(e)}", exc_info=True)
        raise external_service_error(provider, f"{provider.title()} login failed")


@router.post("/firebase/sms", response_model=Dict[str, Any])
async def firebase_sms_auth(
    request: FirebaseSMSRequest,
    device_info: Dict[str, Any] = Depends(get_device_info),
    lang: str = Depends(validate_language),
):
    """
    Firebase SMS authentication

    Two-step process:
    1. Send SMS verification code
    2. Verify code and authenticate
    """
    firebase_service = FirebaseService()
    auth_service = AuthService()

    try:
        if request.verification_code and request.verification_id:
            # Step 2: Verify code and authenticate
            is_valid = await firebase_service.verify_sms_code(
                verification_id=request.verification_id, code=request.verification_code
            )

            if not is_valid:
                raise AuthenticationException("Invalid verification code")

            # Authenticate or create user with phone number
            result = await auth_service.phone_auth(
                phone_number=request.phone_number,
                device_info=device_info,
                language=lang,
            )

            logger.info(f"SMS authentication successful: {request.phone_number}")

            return AuthResponse(
                success=True,
                message="SMS authentication successful",
                user=result["user"],
                tokens=result["tokens"],
            )

        else:
            # Step 1: Send verification code
            verification_id = await firebase_service.send_sms_verification(
                phone_number=request.phone_number
            )

            logger.info(f"SMS verification sent to: {request.phone_number}")

            return {
                "success": True,
                "message": "Verification code sent",
                "verification_id": verification_id,
                "expires_in": 300,  # 5 minutes
            }

    except AuthenticationException:
        raise
    except Exception as e:
        logger.error(f"Firebase SMS error: {str(e)}", exc_info=True)
        raise external_service_error("firebase", "SMS authentication failed")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(request: RefreshTokenRequest):
    """
    Refresh access token using refresh token
    """
    auth_service = AuthService()

    try:
        result = await auth_service.refresh_access_token(request.refresh_token)

        return TokenResponse(
            access_token=result["access_token"],
            token_type="Bearer",
            expires_in=result["expires_in"],
        )

    except AuthenticationException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        )


@router.post("/logout")
async def logout(
    response: Response,
    current_user: Dict[str, Any] = Depends(require_authentication),
    device_info: Dict[str, Any] = Depends(get_device_info),
):
    """
    Logout current user and invalidate tokens
    """
    auth_service = AuthService()

    try:
        await auth_service.logout_user(
            user_id=current_user["user_id"], device_info=device_info
        )

        # Clear any cookies
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        logger.info(f"User logged out: {current_user['user_id']}")

        return {"success": True, "message": "Logout successful"}

    except Exception as e:
        logger.error(f"Logout error: {str(e)}", exc_info=True)
        # Return success anyway for logout
        return {"success": True, "message": "Logout successful"}


@router.post("/forgot-password")
async def forgot_password(
    request: PasswordResetRequest, lang: str = Depends(validate_language)
):
    """
    Send password reset email or SMS
    """
    auth_service = AuthService()

    try:
        result = await auth_service.initiate_password_reset(
            identifier=request.email or request.phone,
            method=request.method,
            language=lang,
        )

        logger.info(f"Password reset initiated for: {request.email or request.phone}")

        return {
            "success": True,
            "message": "Password reset instructions sent",
            "method": result["method"],
            "expires_in": result["expires_in"],
        }

    except Exception as e:
        logger.error(f"Password reset error: {str(e)}", exc_info=True)
        # Always return success for security
        return {
            "success": True,
            "message": "If the account exists, password reset instructions have been sent",
        }


@router.post("/reset-password")
async def reset_password(request: PasswordUpdateRequest):
    """
    Reset password with token or code
    """
    auth_service = AuthService()

    try:
        await auth_service.reset_password(
            token_or_code=request.token or request.verification_code,
            new_password=request.new_password,
            identifier=request.identifier,
        )

        logger.info(f"Password reset completed for token/code")

        return {"success": True, "message": "Password reset successful"}

    except AuthenticationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except ValidationException:
        raise
    except Exception as e:
        logger.error(f"Password reset completion error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed",
        )


@router.post("/verify-email")
async def verify_email(request: VerificationRequest):
    """
    Verify email address with token
    """
    auth_service = AuthService()

    try:
        result = await auth_service.verify_email(token=request.token, code=request.code)

        logger.info(f"Email verified for user: {result['user_id']}")

        return {
            "success": True,
            "message": "Email verified successfully",
            "verified": True,
        }

    except AuthenticationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/verify-phone")
async def verify_phone(request: VerificationRequest):
    """
    Verify phone number with SMS code
    """
    auth_service = AuthService()

    try:
        result = await auth_service.verify_phone(
            token=request.token, code=request.code, phone_number=request.identifier
        )

        logger.info(f"Phone verified for user: {result['user_id']}")

        return {
            "success": True,
            "message": "Phone verified successfully",
            "verified": True,
        }

    except AuthenticationException as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/resend-verification")
async def resend_verification(
    request: ResendVerificationRequest, lang: str = Depends(validate_language)
):
    """
    Resend verification email or SMS
    """
    auth_service = AuthService()

    try:
        result = await auth_service.resend_verification(
            identifier=request.email or request.phone,
            method=request.method,
            language=lang,
        )

        return {
            "success": True,
            "message": f"Verification {request.method} sent",
            "expires_in": result["expires_in"],
        }

    except Exception as e:
        logger.error(f"Resend verification error: {str(e)}", exc_info=True)
        return {
            "success": True,
            "message": f"Verification {request.method} sent if account exists",
        }


@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: Dict[str, Any] = Depends(require_authentication),
    lang: str = Depends(validate_language),
):
    """
    Get current user profile information
    """
    odoo_service = OdooService()

    try:
        profile = await odoo_service.get_user_profile(
            user_id=current_user["user_id"], language=lang
        )

        return UserProfileResponse(**profile)

    except Exception as e:
        logger.error(f"Get profile error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user profile",
        )


@router.get("/session/validate")
async def validate_session(
    current_user: Dict[str, Any] = Depends(require_authentication),
):
    """
    Validate current session and return user info
    """
    return {
        "success": True,
        "valid": True,
        "user_id": current_user["user_id"],
        "expires_at": current_user.get("token_payload", {}).get("exp"),
    }
