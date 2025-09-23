# -*- coding: utf-8 -*-
"""
Logging Middleware
Request/response logging and performance monitoring
"""

import logging
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Logging middleware for request/response monitoring
    Adds request ID and tracks performance metrics
    """

    def __init__(self, app):
        super().__init__(app)
        self.sensitive_headers = {
            "authorization",
            "x-api-key",
            "cookie",
            "x-auth-token",
        }
        self.skip_paths = {"/health", "/docs", "/redoc", "/openapi.json"}

    def _should_skip_logging(self, path: str) -> bool:
        """Check if logging should be skipped for this path"""
        return path in self.skip_paths

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request"""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fall back to direct client IP
        if request.client:
            return request.client.host

        return "unknown"

    def _filter_headers(self, headers: dict) -> dict:
        """Filter sensitive headers for logging"""
        filtered = {}
        for key, value in headers.items():
            if key.lower() in self.sensitive_headers:
                filtered[key] = "***REDACTED***"
            else:
                filtered[key] = value
        return filtered

    def _log_request(self, request: Request, request_id: str, client_ip: str):
        """Log incoming request details"""
        if settings.LOG_LEVEL == "DEBUG":
            headers = self._filter_headers(dict(request.headers))
            logger.debug(
                f"[{request_id}] Incoming request: "
                f"{request.method} {request.url.path} "
                f"from {client_ip} "
                f"with headers: {headers}"
            )
        else:
            logger.info(
                f"[{request_id}] {request.method} {request.url.path} "
                f"from {client_ip}"
            )

    def _log_response(
        self,
        request_id: str,
        method: str,
        path: str,
        status_code: int,
        duration: float,
        client_ip: str,
    ):
        """Log response details"""
        log_level = "INFO"

        # Adjust log level based on status code
        if status_code >= 500:
            log_level = "ERROR"
        elif status_code >= 400:
            log_level = "WARNING"

        message = (
            f"[{request_id}] {method} {path} "
            f"returned {status_code} "
            f"in {duration:.3f}s "
            f"for {client_ip}"
        )

        getattr(logger, log_level.lower())(message)

        # Log slow requests
        if duration > 2.0:  # Requests taking more than 2 seconds
            logger.warning(
                f"[{request_id}] Slow request detected: "
                f"{method} {path} took {duration:.3f}s"
            )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with logging"""

        # Generate unique request ID
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # Get client IP
        client_ip = self._get_client_ip(request)
        request.state.client_ip = client_ip

        # Skip logging for certain paths
        if self._should_skip_logging(request.url.path):
            return await call_next(request)

        # Log incoming request
        start_time = time.time()
        self._log_request(request, request_id, client_ip)

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            self._log_response(
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                duration,
                client_ip,
            )

            # Add response headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration:.3f}s"

            return response

        except Exception as e:
            # Log error
            duration = time.time() - start_time
            logger.error(
                f"[{request_id}] {request.method} {request.url.path} "
                f"failed with error: {str(e)} "
                f"in {duration:.3f}s "
                f"for {client_ip}",
                exc_info=True,
            )

            # Re-raise the exception
            raise
