# -*- coding: utf-8 -*-
"""
Application Configuration
Centralized configuration management using Pydantic settings
"""

import os
from typing import List, Optional, Dict, Any
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Basic Application Settings
    APP_NAME: str = "Yellow Mobile API"
    API_VERSION: str = "1"
    ENVIRONMENT: str = Field(
        "development", pattern="^(development|staging|production)$"
    )
    DEBUG: bool = True
    SECRET_KEY: str = Field(..., min_length=32)

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 1
    ALLOWED_HOSTS: List[str] = ["*"]

    # Database Configuration (Odoo)
    ODOO_DB_NAME: str = Field(..., description="Odoo database name")
    ODOO_DB_HOST: str = "localhost"
    ODOO_DB_PORT: int = 5432
    ODOO_DB_USER: str = "odoo"
    ODOO_DB_PASSWORD: str = Field(..., description="Odoo database password")

    # Redis Configuration (for caching and sessions)
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    CACHE_TTL: int = 3600  # 1 hour default

    # JWT Configuration
    JWT_SECRET_KEY: str = Field(..., min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ISSUER: str = "yellow-mobile-api"
    JWT_AUDIENCE: str = "yellow-mobile-app"

    # OAuth Configuration
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    FACEBOOK_APP_ID: Optional[str] = None
    FACEBOOK_APP_SECRET: Optional[str] = None
    APPLE_CLIENT_ID: Optional[str] = None
    APPLE_PRIVATE_KEY_PATH: Optional[str] = None
    APPLE_KEY_ID: Optional[str] = None
    APPLE_TEAM_ID: Optional[str] = None

    # Firebase Configuration
    FIREBASE_PROJECT_ID: Optional[str] = None
    FIREBASE_CREDENTIALS_PATH: Optional[str] = None
    FIREBASE_API_KEY: Optional[str] = None

    # Email Configuration
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_USE_TLS: bool = True
    FROM_EMAIL: Optional[str] = None

    # SMS Configuration (Twilio)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_PHONE_NUMBER: Optional[str] = None

    # File Upload Configuration
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_TYPES: List[str] = [
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
    ]
    ALLOWED_DOCUMENT_TYPES: List[str] = [
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    UPLOAD_PATH: str = "/tmp/uploads"

    # Payment Configuration
    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    PAYPAL_CLIENT_ID: Optional[str] = None
    PAYPAL_CLIENT_SECRET: Optional[str] = None
    PAYPAL_MODE: str = "sandbox"  # sandbox or live

    # API Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10

    # Logging Configuration
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_FILE: Optional[str] = None

    # Feature Flags
    ENABLE_PUSH_NOTIFICATIONS: bool = True
    ENABLE_EMAIL_VERIFICATION: bool = True
    ENABLE_SMS_VERIFICATION: bool = True
    ENABLE_SOCIAL_LOGIN: bool = True
    ENABLE_GUEST_CHECKOUT: bool = True
    ENABLE_WISHLIST: bool = True
    ENABLE_REVIEWS: bool = True
    ENABLE_WALLET: bool = True

    # Mobile App Configuration
    MOBILE_APP_VERSION: str = "1.0.0"
    FORCE_APP_UPDATE_VERSION: Optional[str] = None
    APP_STORE_URL: Optional[str] = None
    PLAY_STORE_URL: Optional[str] = None

    # Business Configuration
    DEFAULT_CURRENCY: str = "USD"
    SUPPORTED_CURRENCIES: List[str] = ["USD", "EUR", "SAR", "AED"]
    DEFAULT_LANGUAGE: str = "en"
    SUPPORTED_LANGUAGES: List[str] = ["en", "ar"]
    TIMEZONE: str = "UTC"

    # API Documentation
    DOCS_ENABLED: bool = True
    REDOC_ENABLED: bool = True

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v):
        """Validate environment setting"""
        if v not in ["development", "staging", "production"]:
            raise ValueError("Environment must be development, staging, or production")
        return v

    @field_validator("DEBUG")
    @classmethod
    def validate_debug_for_production(cls, v, info):
        """Ensure DEBUG is False in production"""
        if info.data.get("ENVIRONMENT") == "production" and v:
            raise ValueError("DEBUG cannot be True in production environment")
        return v

    @field_validator("ALLOWED_HOSTS")
    @classmethod
    def validate_allowed_hosts_for_production(cls, v, info):
        """Ensure ALLOWED_HOSTS is properly set in production"""
        if info.data.get("ENVIRONMENT") == "production" and v == ["*"]:
            raise ValueError("ALLOWED_HOSTS cannot be ['*'] in production environment")
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret_strength(cls, v):
        """Validate JWT secret key strength"""
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

        @classmethod
        def customise_sources(cls, init_settings, env_settings, file_secret_settings):
            """Customize settings sources priority"""
            return (
                init_settings,
                env_settings,
                file_secret_settings,
            )


class DevelopmentSettings(Settings):
    """Development environment specific settings"""

    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    DOCS_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 1000  # More lenient for development

    # Provide default values for required fields in development
    SECRET_KEY: str = "development-secret-key-change-in-production-32chars"
    JWT_SECRET_KEY: str = "jwt-development-secret-key-change-in-production-32chars"
    ODOO_DB_NAME: str = "uellow_test"
    ODOO_DB_PASSWORD: str = "odoo"


class ProductionSettings(Settings):
    """Production environment specific settings"""

    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    DOCS_ENABLED: bool = False
    ALLOWED_HOSTS: List[str] = Field(
        ..., description="Must specify allowed hosts in production"
    )

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_production_secret(cls, v):
        """Ensure production secret is strong"""
        if v == "your-super-secret-key-change-this":
            raise ValueError("Must change default SECRET_KEY in production")
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)"""
    environment = os.getenv("ENVIRONMENT", "development").lower()

    if environment == "production":
        return ProductionSettings()
    elif environment == "staging":
        # You can create StagingSettings if needed
        return Settings(ENVIRONMENT="staging", DEBUG=False)
    else:
        return DevelopmentSettings()


# Create settings instance
settings = get_settings()

# Export commonly used settings
__all__ = [
    "Settings",
    "DevelopmentSettings",
    "ProductionSettings",
    "get_settings",
    "settings",
]
