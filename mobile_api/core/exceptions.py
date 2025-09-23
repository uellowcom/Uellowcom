# -*- coding: utf-8 -*-
"""
Custom Exception Classes
Centralized exception handling for consistent API responses
"""

from typing import Any, Dict, List, Optional, Union
from fastapi import status


class APIException(Exception):
    """Base API exception class"""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "API_ERROR",
        details: Optional[Union[Dict[str, Any], List[Any], str]] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details
        super().__init__(self.message)


class ValidationException(APIException):
    """Validation error exception"""

    def __init__(
        self,
        message: str = "Validation failed",
        errors: Optional[List[Dict[str, Any]]] = None,
        field: Optional[str] = None,
    ):
        self.errors = errors or []
        self.field = field
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            details=(
                {"errors": self.errors, "field": field}
                if field
                else {"errors": self.errors}
            ),
        )


class AuthenticationException(APIException):
    """Authentication error exception"""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_ERROR",
        )


class AuthorizationException(APIException):
    """Authorization error exception"""

    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="AUTHORIZATION_ERROR",
        )


class NotFoundException(APIException):
    """Resource not found exception"""

    def __init__(
        self, message: str = "Resource not found", resource: Optional[str] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND_ERROR",
            details={"resource": resource} if resource else None,
        )


class ConflictException(APIException):
    """Conflict error exception (e.g., duplicate resource)"""

    def __init__(
        self, message: str = "Resource conflict", resource: Optional[str] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="CONFLICT_ERROR",
            details={"resource": resource} if resource else None,
        )


class RateLimitException(APIException):
    """Rate limit exceeded exception"""

    def __init__(
        self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="RATE_LIMIT_ERROR",
            details={"retry_after": retry_after} if retry_after else None,
        )


class PaymentException(APIException):
    """Payment processing error exception"""

    def __init__(
        self,
        message: str = "Payment processing failed",
        payment_error_code: Optional[str] = None,
        gateway: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            error_code="PAYMENT_ERROR",
            details=(
                {"payment_error_code": payment_error_code, "gateway": gateway}
                if payment_error_code or gateway
                else None
            ),
        )


class ExternalServiceException(APIException):
    """External service error exception"""

    def __init__(
        self,
        message: str = "External service error",
        service: Optional[str] = None,
        service_error: Optional[str] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="EXTERNAL_SERVICE_ERROR",
            details=(
                {"service": service, "service_error": service_error}
                if service or service_error
                else None
            ),
        )


class BusinessRuleException(APIException):
    """Business rule violation exception"""

    def __init__(
        self,
        message: str,
        rule_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="BUSINESS_RULE_ERROR",
            details=(
                {"rule_code": rule_code, "context": context}
                if rule_code or context
                else None
            ),
        )


class DatabaseException(APIException):
    """Database operation error exception"""

    def __init__(self, message: str = "Database operation failed"):
        super().__init__(
            message=message,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="DATABASE_ERROR",
        )


class FileException(APIException):
    """File operation error exception"""

    def __init__(
        self,
        message: str,
        file_type: Optional[str] = None,
        max_size: Optional[int] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            error_code="FILE_ERROR",
            details=(
                {"file_type": file_type, "max_size": max_size}
                if file_type or max_size
                else None
            ),
        )


# Common exception factory functions


def validation_error(
    message: str, field: Optional[str] = None, errors: Optional[List] = None
) -> ValidationException:
    """Create a validation exception"""
    return ValidationException(message=message, field=field, errors=errors or [])


def not_found_error(
    resource: str, identifier: Optional[Union[str, int]] = None
) -> NotFoundException:
    """Create a not found exception"""
    message = f"{resource} not found"
    if identifier:
        message += f" with identifier: {identifier}"
    return NotFoundException(message=message, resource=resource)


def auth_error(message: str = "Authentication required") -> AuthenticationException:
    """Create an authentication exception"""
    return AuthenticationException(message=message)


def permission_error(
    message: str = "Insufficient permissions",
) -> AuthorizationException:
    """Create an authorization exception"""
    return AuthorizationException(message=message)


def conflict_error(resource: str, message: Optional[str] = None) -> ConflictException:
    """Create a conflict exception"""
    if not message:
        message = f"{resource} already exists"
    return ConflictException(message=message, resource=resource)


def business_error(
    message: str, rule_code: Optional[str] = None, **context
) -> BusinessRuleException:
    """Create a business rule exception"""
    return BusinessRuleException(
        message=message, rule_code=rule_code, context=context if context else None
    )


def payment_error(
    message: str = "Payment failed",
    error_code: Optional[str] = None,
    gateway: Optional[str] = None,
) -> PaymentException:
    """Create a payment exception"""
    return PaymentException(
        message=message, payment_error_code=error_code, gateway=gateway
    )


def external_service_error(
    service: str, message: Optional[str] = None, error: Optional[str] = None
) -> ExternalServiceException:
    """Create an external service exception"""
    if not message:
        message = f"{service} service is currently unavailable"
    return ExternalServiceException(
        message=message, service=service, service_error=error
    )


# Export all exceptions and factory functions
__all__ = [
    # Exception classes
    "APIException",
    "ValidationException",
    "AuthenticationException",
    "AuthorizationException",
    "NotFoundException",
    "ConflictException",
    "RateLimitException",
    "PaymentException",
    "ExternalServiceException",
    "BusinessRuleException",
    "DatabaseException",
    "FileException",
    # Factory functions
    "validation_error",
    "not_found_error",
    "auth_error",
    "permission_error",
    "conflict_error",
    "business_error",
    "payment_error",
    "external_service_error",
]
