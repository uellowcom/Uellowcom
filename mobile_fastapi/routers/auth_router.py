# -*- coding: utf-8 -*-
from typing import Annotated, Dict, Any
from datetime import datetime, timedelta

from odoo.api import Environment

from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, EmailStr

from ..security.jwt import create_access_token, create_refresh_token, decode_token
from ..dependencies import odoo_env, get_current_user

# Define the router
router = APIRouter(prefix="/mobile/v1/auth", tags=["auth"])

# Models for request/response
class UserSignup(BaseModel):
    username: str
    password: str
    name: str
    email: EmailStr = None
    phone: str = None
    device_id: str = None
    device_token: str = None
    device_platform: str = None

class UserLogin(BaseModel):
    username: str
    password: str
    device_id: str = None
    device_token: str = None
    device_platform: str = None

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 minutes

class RefreshRequest(BaseModel):
    refresh_token: str

class UserResponse(BaseModel):
    id: int
    username: str
    name: str
    email: str = None
    phone: str = None

class ApiResponse(BaseModel):
    success: bool = True
    error: str = None
    data: Dict[str, Any] = None


@router.post("/register", response_model=ApiResponse)
async def register(
    user_data: UserSignup,
    env: Annotated[Environment, Depends(odoo_env)]
):
    """Register a new mobile user"""
    try:
        # Create the mobile user
        mobile_user_model = env["mobile.user"]
        values = user_data.model_dump()
        
        mobile_user = mobile_user_model.signup(values)
        
        # Generate tokens
        user_data = {
            "sub": str(mobile_user.id),
            "username": mobile_user.username,
        }
        
        access_token = create_access_token(user_data)
        refresh_token = create_refresh_token(user_data)
        
        return {
            "success": True,
            "data": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": mobile_user.id,
                    "username": mobile_user.username,
                    "name": mobile_user.partner_id.name,
                    "email": mobile_user.partner_id.email,
                    "phone": mobile_user.partner_id.phone,
                }
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/login", response_model=ApiResponse)
async def login(
    login_data: UserLogin,
    env: Annotated[Environment, Depends(odoo_env)]
):
    """Login with username and password"""
    try:
        # Authenticate the user
        mobile_user_model = env["mobile.user"]
        mobile_user = mobile_user_model.authenticate(
            login_data.username, login_data.password
        )
        
        if not mobile_user:
            return {
                "success": False,
                "error": "Invalid username or password"
            }
        
        # Update device info if provided
        update_vals = {}
        if login_data.device_id:
            update_vals["device_id"] = login_data.device_id
        if login_data.device_token:
            update_vals["device_token"] = login_data.device_token
        if login_data.device_platform:
            update_vals["device_platform"] = login_data.device_platform
        
        if update_vals:
            mobile_user.write(update_vals)
        
        # Generate tokens
        user_data = {
            "sub": str(mobile_user.id),
            "username": mobile_user.username,
        }
        
        access_token = create_access_token(user_data)
        refresh_token = create_refresh_token(user_data)
        
        return {
            "success": True,
            "data": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": 1800,
                "user": {
                    "id": mobile_user.id,
                    "username": mobile_user.username,
                    "name": mobile_user.partner_id.name,
                    "email": mobile_user.partner_id.email,
                    "phone": mobile_user.partner_id.phone,
                }
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/refresh", response_model=ApiResponse)
async def refresh_token(
    refresh_data: RefreshRequest,
    env: Annotated[Environment, Depends(odoo_env)]
):
    """Refresh access token using refresh token"""
    try:
        # Decode the refresh token
        payload = decode_token(refresh_data.refresh_token)
        
        if "error" in payload:
            return {
                "success": False,
                "error": payload["error"]
            }
        
        # Get the user ID from the token
        user_id = int(payload.get("sub"))
        
        # Check if the user exists
        mobile_user_model = env["mobile.user"]
        mobile_user = mobile_user_model.browse(user_id)
        
        if not mobile_user.exists() or not mobile_user.active:
            return {
                "success": False,
                "error": "Invalid user"
            }
        
        # Generate new tokens
        user_data = {
            "sub": str(mobile_user.id),
            "username": mobile_user.username,
        }
        
        access_token = create_access_token(user_data)
        refresh_token = create_refresh_token(user_data)
        
        return {
            "success": True,
            "data": {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": 1800
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/logout", response_model=ApiResponse)
async def logout(
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)]
):
    """Logout current user"""
    try:
        # Nothing to do here since JWT tokens are stateless
        # In a real-world scenario, you might want to blacklist the token
        return {
            "success": True,
            "data": {
                "message": "Logged out successfully"
            }
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/health", response_model=ApiResponse)
async def health_check():
    """Health check endpoint"""
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "service": "Yellow Mobile API",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat()
        }
    }
