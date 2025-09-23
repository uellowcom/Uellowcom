# -*- coding: utf-8 -*-
"""
Rate Limiting Middleware
Implements rate limiting to prevent API abuse
"""

import logging
import time
from typing import Callable, Dict, List
from collections import defaultdict, deque

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from ..core.config import get_settings
from ..core.exceptions import RateLimitException

settings = get_settings()
logger = logging.getLogger(__name__)


class RateLimitStore:
    """In-memory rate limit store using sliding window"""

    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.last_cleanup = time.time()

    def is_allowed(self, key: str, limit: int, window: int) -> tuple[bool, int, int]:
        """
        Check if request is allowed within rate limit
        Returns: (allowed, remaining_requests, reset_time)
        """
        now = int(time.time())
        window_start = now - window

        # Clean old entries
        self._cleanup_expired(key, window_start)

        # Get current request count
        current_requests = len(self.requests[key])

        # Check if limit exceeded
        if current_requests >= limit:
            # Find when oldest request will expire
            if self.requests[key]:
                reset_time = int(self.requests[key][0]) + window
            else:
                reset_time = now + window

            return False, 0, reset_time

        # Add current request
        self.requests[key].append(now)
        remaining = limit - current_requests - 1
        reset_time = now + window

        return True, remaining, reset_time

    def _cleanup_expired(self, key: str, window_start: int):
        """Remove expired entries for a key"""
        while self.requests[key] and self.requests[key][0] <= window_start:
            self.requests[key].popleft()

        # Remove empty queues to save memory
        if not self.requests[key]:
            del self.requests[key]

    def cleanup_all(self, max_age: int = 3600):
        """Clean up all expired entries (called periodically)"""
        now = time.time()

        # Only run cleanup every 5 minutes
        if now - self.last_cleanup < 300:
            return

        cutoff = now - max_age
        keys_to_remove = []

        for key, requests in self.requests.items():
            # Remove old entries
            while requests and requests[0] <= cutoff:
                requests.popleft()

            # Mark empty queues for removal
            if not requests:
                keys_to_remove.append(key)

        # Remove empty queues
        for key in keys_to_remove:
            del self.requests[key]

        self.last_cleanup = now

        if keys_to_remove:
            logger.debug(f"Cleaned up {len(keys_to_remove)} expired rate limit entries")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with configurable limits per endpoint
    """

    def __init__(self, app):
        super().__init__(app)
        self.store = RateLimitStore()

        # Default rate limits (requests per minute)
        self.default_limit = settings.RATE_LIMIT_PER_MINUTE
        self.default_window = 60  # 1 minute

        # Custom limits for specific paths
        self.custom_limits = {
            "/api/v1/auth/login": (10, 60),  # 10 requests per minute
            "/api/v1/auth/register": (5, 60),  # 5 requests per minute
            "/api/v1/auth/forgot-password": (3, 300),  # 3 requests per 5 minutes
            "/api/v1/auth/reset-password": (5, 300),  # 5 requests per 5 minutes
            "/api/v1/auth/firebase/sms": (10, 60),  # 10 SMS per minute
            "/api/v1/orders": (30, 60),  # 30 orders per minute
            "/api/v1/payments": (20, 60),  # 20 payment attempts per minute
        }

        # Paths to skip rate limiting
        self.skip_paths = {"/health", "/docs", "/redoc", "/openapi.json"}

    def _get_rate_limit_key(self, request: Request) -> str:
        """Generate rate limit key based on client identification"""
        # Try to use authenticated user ID first
        if hasattr(request.state, "user_id") and request.state.user_id:
            return f"user:{request.state.user_id}"

        # Fall back to IP address
        client_ip = getattr(request.state, "client_ip", "unknown")
        return f"ip:{client_ip}"

    def _get_rate_limit_config(self, path: str) -> tuple[int, int]:
        """Get rate limit configuration for a path"""
        # Check for exact match
        if path in self.custom_limits:
            return self.custom_limits[path]

        # Check for prefix matches
        for custom_path, config in self.custom_limits.items():
            if path.startswith(custom_path):
                return config

        # Return default
        return self.default_limit, self.default_window

    def _should_skip_rate_limit(self, path: str) -> bool:
        """Check if rate limiting should be skipped"""
        return path in self.skip_paths

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Apply rate limiting to requests"""

        path = request.url.path

        # Skip rate limiting for certain paths
        if self._should_skip_rate_limit(path):
            return await call_next(request)

        # Periodic cleanup
        self.store.cleanup_all()

        # Get rate limit configuration
        limit, window = self._get_rate_limit_config(path)

        # Generate rate limit key
        key = self._get_rate_limit_key(request)

        # Check rate limit
        allowed, remaining, reset_time = self.store.is_allowed(key, limit, window)

        if not allowed:
            # Rate limit exceeded
            retry_after = reset_time - int(time.time())

            logger.warning(
                f"Rate limit exceeded for {key} on {request.method} {path}. "
                f"Limit: {limit}/{window}s, Reset in: {retry_after}s"
            )

            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded. Try again in {retry_after} seconds.",
                        "details": {
                            "limit": limit,
                            "window": window,
                            "retry_after": retry_after,
                        },
                    },
                    "data": None,
                },
                headers={
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_time),
                    "Retry-After": str(retry_after),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response
