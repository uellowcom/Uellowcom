# -*- coding: utf-8 -*-
"""Authentication schemas for request/response validation"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator
import re


class UserRegister(BaseModel):
    """User registration schema"""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str
    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    phone: Optional[str] = Field(None, regex=r'^\+?[1-9]\d{1,14}$')
    
    @validator('password')
    def validate_password_strength(cls, v):
        """Ensure password meets security requirements"""
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain at least one digit')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Password must contain at least one special character')
        return v
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Ensure passwords match"""
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords do not match')
        return v


class UserLogin(BaseModel):
    """User login schema"""
    email: EmailStr
    password: str
    device_id: Optional[str] = None
    device_type: Optional[str] = Field(None, regex=r'^(ios|android|web)$')


class SocialLogin(BaseModel):
    """Social login schema"""
    provider: str = Field(..., regex=r'^(google|facebook|apple)$')
    id_token: str
    device_id: Optional[str] = None
    device_type: Optional[str] = Field(None, regex=r'^(ios|android|web)$')


class FirebaseSMSAuth(BaseModel):
    """Firebase SMS authentication schema"""
    phone_number: str = Field(..., regex=r'^\+?[1-9]\d{1,14}$')
    verification_code: Optional[str] = None
    verification_id: Optional[str] = None


class FirebaseTokenAuth(BaseModel):
    """Firebase token authentication"""
    firebase_token: str
    device_id: Optional[str] = None


class ForgotPassword(BaseModel):
    """Forgot password request schema"""
    email: EmailStr


class ResetPassword(BaseModel):
    """Reset password schema"""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)
    confirm_password: str
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        """Ensure passwords match"""
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v


class RefreshToken(BaseModel):
    """Refresh token request"""
    refresh_token: str


class TokenResponse(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: Dict[str, Any]


class UserResponse(BaseModel):
    """User response schema"""
    id: int
    email: str
    first_name: str
    last_name: str
    phone: Optional[str]
    avatar_url: Optional[str]
    is_verified: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class AuthResponse(BaseModel):
    """Authentication response"""
    user: UserResponse
    tokens: TokenResponse
    message: str = "Authentication successful"
