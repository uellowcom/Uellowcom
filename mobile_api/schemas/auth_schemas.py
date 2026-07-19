# -*- coding: utf-8 -*-
"""
Enhanced Authentication Schemas
Comprehensive request/response validation for authentication
"""

from typing import Optional, Dict, Any, Literal, Union
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, validator, root_validator
import re


# Request Schemas


class UserRegisterRequest(BaseModel):
    """Enhanced user registration schema"""

    # Basic info
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str

    # Personal info
    first_name: str = Field(..., min_length=1, max_length=50, description="First name")
    last_name: str = Field(..., min_length=1, max_length=50, description="Last name")
    date_of_birth: Optional[datetime] = None
    gender: Optional[Literal["male", "female", "other"]] = None

    # Location
    country_code: Optional[str] = Field(
        None, pattern=r"^[A-Z]{2}$", description="ISO country code"
    )
    city: Optional[str] = Field(None, max_length=100)

    # Preferences
    language: Optional[str] = Field("en", pattern=r"^(en|ar|fr|es)$")
    currency: Optional[str] = Field("USD", pattern=r"^[A-Z]{3}$")

    # Privacy & Marketing
    agree_to_terms: bool = Field(..., description="Must agree to terms")
    agree_to_privacy: bool = Field(..., description="Must agree to privacy policy")
    marketing_emails: bool = Field(False, description="Opt-in to marketing emails")
    marketing_sms: bool = Field(False, description="Opt-in to marketing SMS")

    # Device info (optional)
    device_id: Optional[str] = None
    device_type: Optional[Literal["ios", "android", "web"]] = None

    @root_validator
    def validate_contact_method(cls, values):
        """Ensure at least email or phone is provided"""
        email = values.get("email")
        phone = values.get("phone")

        if not email and not phone:
            raise ValueError("Either email or phone number is required")

        return values

    @validator("password")
    def validate_password_strength(cls, v):
        """Ensure password meets security requirements"""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v

    @validator("confirm_password")
    def passwords_match(cls, v, values):
        """Ensure passwords match"""
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
        return v

    @validator("agree_to_terms")
    def must_agree_to_terms(cls, v):
        """Must agree to terms"""
        if not v:
            raise ValueError("Must agree to terms and conditions")
        return v

    @validator("agree_to_privacy")
    def must_agree_to_privacy(cls, v):
        """Must agree to privacy policy"""
        if not v:
            raise ValueError("Must agree to privacy policy")
        return v


class UserLoginRequest(BaseModel):
    """Enhanced user login schema"""

    identifier: str = Field(..., description="Email or phone number")
    password: str = Field(..., min_length=1)
    remember_me: bool = Field(False, description="Extended session")
    device_id: Optional[str] = None
    device_type: Optional[Literal["ios", "android", "web"]] = None


class SocialLoginRequest(BaseModel):
    """Social login schema"""

    token: str = Field(..., description="OAuth token from social provider")
    device_id: Optional[str] = None
    device_type: Optional[Literal["ios", "android", "web"]] = None


class FirebaseSMSRequest(BaseModel):
    """Firebase SMS authentication schema"""

    phone_number: str = Field(..., pattern=r"^\+?[1-9]\d{1,14}$")
    verification_code: Optional[str] = Field(None, min_length=6, max_length=6)
    verification_id: Optional[str] = None


class PasswordResetRequest(BaseModel):
    """Password reset initiation schema"""

    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    method: Literal["email", "sms"] = "email"

    @root_validator
    def validate_identifier(cls, values):
        """Ensure correct identifier for method"""
        method = values.get("method")
        email = values.get("email")
        phone = values.get("phone")

        if method == "email" and not email:
            raise ValueError("Email required for email reset")
        elif method == "sms" and not phone:
            raise ValueError("Phone required for SMS reset")

        return values


class PasswordUpdateRequest(BaseModel):
    """Password reset completion schema"""

    token: Optional[str] = None
    verification_code: Optional[str] = None
    identifier: Optional[str] = None  # email or phone
    new_password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str

    @root_validator
    def validate_reset_method(cls, values):
        """Ensure token or code is provided"""
        token = values.get("token")
        code = values.get("verification_code")

        if not token and not code:
            raise ValueError("Token or verification code required")

        return values

    @validator("confirm_password")
    def passwords_match(cls, v, values):
        """Ensure passwords match"""
        if "new_password" in values and v != values["new_password"]:
            raise ValueError("Passwords do not match")
        return v


class RefreshTokenRequest(BaseModel):
    """Refresh token request"""

    refresh_token: str = Field(..., description="Valid refresh token")


class VerificationRequest(BaseModel):
    """Email/phone verification schema"""

    token: Optional[str] = None
    code: Optional[str] = None
    identifier: Optional[str] = None  # email or phone

    @root_validator
    def validate_verification_data(cls, values):
        """Ensure token or code is provided"""
        token = values.get("token")
        code = values.get("code")

        if not token and not code:
            raise ValueError("Token or verification code required")

        return values


class ResendVerificationRequest(BaseModel):
    """Resend verification request"""

    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$")
    method: Literal["email", "sms"] = "email"

    @root_validator
    def validate_resend_data(cls, values):
        """Validate resend request data"""
        method = values.get("method")
        email = values.get("email")
        phone = values.get("phone")

        if method == "email" and not email:
            raise ValueError("Email required for email verification")
        elif method == "sms" and not phone:
            raise ValueError("Phone required for SMS verification")

        return values


# Response Schemas


class UserProfileResponse(BaseModel):
    """User profile response schema"""

    id: int
    email: Optional[str]
    phone: Optional[str]
    first_name: str
    last_name: str
    full_name: str
    avatar_url: Optional[str]
    date_of_birth: Optional[datetime]
    gender: Optional[str]

    # Verification status
    email_verified: bool = False
    phone_verified: bool = False

    # Location
    country_code: Optional[str]
    city: Optional[str]

    # Preferences
    language: str = "en"
    currency: str = "USD"
    timezone: Optional[str]

    # Privacy settings
    marketing_emails: bool = False
    marketing_sms: bool = False

    # Account info
    account_type: str = "customer"
    is_active: bool = True
    last_login: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class TokenResponse(BaseModel):
    """JWT token response"""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int
    scope: Optional[str] = None


class AuthResponse(BaseModel):
    """Complete authentication response"""

    success: bool = True
    message: str
    user: UserProfileResponse
    tokens: TokenResponse
    requires_verification: bool = False
    verification_methods: Optional[list] = None


class SessionResponse(BaseModel):
    """Session validation response"""

    valid: bool
    user_id: Optional[int] = None
    expires_at: Optional[datetime] = None
    token_type: Optional[str] = None


class PasswordStrengthResponse(BaseModel):
    """Password strength validation response"""

    strength: Literal["weak", "fair", "good", "strong"]
    score: int = Field(..., ge=0, le=4)
    feedback: list
    requirements_met: Dict[str, bool]


# Export all schemas
__all__ = [
    # Request schemas
    "UserRegisterRequest",
    "UserLoginRequest",
    "SocialLoginRequest",
    "FirebaseSMSRequest",
    "PasswordResetRequest",
    "PasswordUpdateRequest",
    "RefreshTokenRequest",
    "VerificationRequest",
    "ResendVerificationRequest",
    # Response schemas
    "UserProfileResponse",
    "TokenResponse",
    "AuthResponse",
    "SessionResponse",
    "PasswordStrengthResponse",
]
