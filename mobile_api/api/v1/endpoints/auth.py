# -*- coding: utf-8 -*-
"""Authentication endpoints for Mobile API"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import HTTPBearer
from typing import Dict, Any

from ....schemas.auth_schemas import (
    UserRegister, UserLogin, SocialLogin, FirebaseSMSAuth,
    FirebaseTokenAuth, ForgotPassword, ResetPassword,
    RefreshToken, TokenResponse, AuthResponse
)
from ....services.auth_service import AuthService
from ....core.security import SecurityManager

router = APIRouter(prefix="/auth", tags=["Authentication"])
auth_service = AuthService()


@router.post("/register", response_model=AuthResponse)
async def register(user_data: UserRegister):
    """Register a new user account"""
    try:
        result = await auth_service.register_user(user_data)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=AuthResponse)
async def login(credentials: UserLogin):
    """Login with email and password"""
    try:
        result = await auth_service.login(credentials)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@router.post("/logout")
async def logout(current_user: Dict = Depends(SecurityManager.get_current_user)):
    """Logout current user"""
    await auth_service.logout(current_user["user_id"])
    return {"message": "Logged out successfully"}


@router.post("/refresh-token", response_model=TokenResponse)
async def refresh_token(token_data: RefreshToken):
    """Refresh access token using refresh token"""
    try:
        result = await auth_service.refresh_access_token(token_data.refresh_token)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )


@router.post("/forgot-password")
async def forgot_password(data: ForgotPassword):
    """Send password reset email"""
    await auth_service.send_password_reset(data.email)
    return {"message": "Password reset email sent if account exists"}


@router.post("/reset-password")
async def reset_password(data: ResetPassword):
    """Reset password with token"""
    try:
        await auth_service.reset_password(data)
        return {"message": "Password reset successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/firebase/sms")
async def firebase_sms_auth(data: FirebaseSMSAuth):
    """Authenticate using Firebase SMS"""
    try:
        if data.verification_code:
            # Verify the code
            result = await auth_service.verify_firebase_sms(
                data.phone_number,
                data.verification_code,
                data.verification_id
            )
            return result
        else:
            # Send verification code
            verification_id = await auth_service.send_firebase_sms(data.phone_number)
            return {"verification_id": verification_id, "message": "Verification code sent"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/firebase/token", response_model=AuthResponse)
async def firebase_token_auth(data: FirebaseTokenAuth):
    """Authenticate using Firebase token"""
    try:
        result = await auth_service.authenticate_firebase_token(data.firebase_token)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Firebase token"
        )


@router.post("/social/google", response_model=AuthResponse)
async def google_login(data: SocialLogin):
    """Login with Google OAuth"""
    try:
        result = await auth_service.google_login(data.id_token)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Google authentication failed"
        )


@router.post("/social/facebook", response_model=AuthResponse)
async def facebook_login(data: SocialLogin):
    """Login with Facebook OAuth"""
    try:
        result = await auth_service.facebook_login(data.id_token)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Facebook authentication failed"
        )


@router.post("/social/apple", response_model=AuthResponse)
async def apple_login(data: SocialLogin):
    """Login with Apple Sign In"""
    try:
        result = await auth_service.apple_login(data.id_token)
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Apple authentication failed"
        )


@router.get("/cookie")
async def get_auth_cookie(response: Response, current_user: Dict = Depends(SecurityManager.get_current_user)):
    """Get authentication cookie for web session"""
    cookie_value = await auth_service.create_session_cookie(current_user["user_id"])
    response.set_cookie(
        key="session",
        value=cookie_value,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=3600 * 24 * 7  # 7 days
    )
    return {"message": "Cookie set successfully"}
