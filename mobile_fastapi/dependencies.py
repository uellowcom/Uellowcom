# -*- coding: utf-8 -*-
from typing import Annotated, Dict, Any, Optional
import logging

from odoo.api import Environment

from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer

from .security.jwt import decode_token, get_token_from_header

_logger = logging.getLogger(__name__)

# OAuth2 scheme for Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/mobile/v1/auth/login")


# Dependencies
def odoo_env():
    """Get the Odoo environment from the current request"""
    from odoo.http import request

    if not request:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Odoo request not available",
        )
    return request.env


def get_current_user(
    authorization: Annotated[str, Header()] = None,
    env: Annotated[Environment, Depends(odoo_env)] = Depends(odoo_env),
) -> Dict[str, Any]:
    """Get the current user from the JWT token"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = get_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(token)
    if "error" in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=payload["error"],
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = int(sub)
    mobile_user = env["mobile.user"].sudo().browse(user_id)

    if not mobile_user.exists() or not mobile_user.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "id": mobile_user.id,
        "username": mobile_user.username,
        "partner_id": mobile_user.partner_id.id,
        "user_id": mobile_user.user_id.id,
    }


def get_optional_user(
    authorization: Annotated[Optional[str], Header()] = None,
    env: Annotated[Environment, Depends(odoo_env)] = Depends(odoo_env),
) -> Optional[Dict[str, Any]]:
    """Get the current user from the JWT token if available, otherwise None"""
    if not authorization:
        return None

    token = get_token_from_header(authorization)
    if not token:
        return None

    payload = decode_token(token)
    if "error" in payload:
        return None

    sub = payload.get("sub")
    if not sub:
        return None

    user_id = int(sub)
    mobile_user = env["mobile.user"].sudo().browse(user_id)

    if not mobile_user.exists() or not mobile_user.active:
        return None

    return {
        "id": mobile_user.id,
        "username": mobile_user.username,
        "partner_id": mobile_user.partner_id.id,
        "user_id": mobile_user.user_id.id,
    }
