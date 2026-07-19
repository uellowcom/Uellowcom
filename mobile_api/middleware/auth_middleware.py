# -*- coding: utf-8 -*-
"""
Authentication Middleware
Handles JWT token validation and user context
"""

import logging
from typing import Callable, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.security import security
from ..core.exceptions import AuthenticationException

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware for JWT token validation
    Adds user context to request state for authenticated requests
    """

    def __init__(self, app, skip_paths: Optional[list] = None):
        super().__init__(app)
        self.skip_paths = skip_paths or [
            "/docs",
            "/redoc",
            "/openapi.json",
            "/health",
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/refresh",
            "/api/v1/auth/forgot-password",
            "/api/v1/auth/reset-password",
            "/api/v1/auth/firebase",
            "/api/v1/auth/social",
            "/api/v1/products",  # Allow browsing products without auth
            "/api/v1/categories",  # Allow browsing categories without auth
        ]

    def _should_skip_auth(self, path: str) -> bool:
        """Check if authentication should be skipped for this path"""
        return any(path.startswith(skip_path) for skip_path in self.skip_paths)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add authentication context"""

        # Skip authentication for certain paths
        if self._should_skip_auth(request.url.path):
            return await call_next(request)

        # Extract authorization header
        auth_header = request.headers.get("authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]

            try:
                # Validate token and get user info
                payload = security.decode_token(token)
                user_id = payload.get("sub")

                if user_id:
                    # Add user context to request state
                    request.state.user_id = int(user_id)
                    request.state.user_payload = payload
                    request.state.is_authenticated = True

                    logger.debug(f"User {user_id} authenticated for {request.url.path}")
                else:
                    request.state.is_authenticated = False

            except AuthenticationException:
                # Invalid token, but don't block request
                # Let the endpoint decide if auth is required
                request.state.is_authenticated = False
                logger.debug(f"Invalid token for {request.url.path}")

            except Exception as e:
                logger.error(f"Auth middleware error: {str(e)}")
                request.state.is_authenticated = False

        else:
            # No authorization header
            request.state.is_authenticated = False

        # Add default user context if not set
        if not hasattr(request.state, "user_id"):
            request.state.user_id = None
            request.state.user_payload = None
            request.state.is_authenticated = False

        response = await call_next(request)
        return response
