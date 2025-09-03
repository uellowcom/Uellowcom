# -*- coding: utf-8 -*-
"""Dependencies for Mobile API endpoints"""

from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from odoo.api import Environment
from odoo.addons.fastapi.dependencies import odoo_env
from odoo.addons.base.models.res_partner import Partner

from .services.jwt_service import JWTService
from .services.firebase_service import FirebaseAuthService

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    env: Annotated[Environment, Depends(odoo_env)]
) -> Partner:
    """Get current authenticated user from JWT token"""
    try:
        jwt_service = JWTService()
        payload = jwt_service.decode_token(credentials.credentials)
        partner_id = payload.get('sub')
        
        if not partner_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        partner = env['res.partner'].browse(int(partner_id))
        if not partner.exists():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        return partner
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


async def get_optional_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)] = None,
    env: Annotated[Environment, Depends(odoo_env)] = None
) -> Partner:
    """Get current user if authenticated, otherwise return None"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, env)
    except:
        return None


def firebase_auth() -> FirebaseAuthService:
    """Get Firebase authentication service"""
    return FirebaseAuthService()


def jwt_service() -> JWTService:
    """Get JWT service"""
    return JWTService()
