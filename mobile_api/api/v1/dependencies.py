# -*- coding: utf-8 -*-
"""
API Dependencies
Common dependencies for API endpoints
"""

from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, Query, Request, status

from ...core.security import get_current_user, get_optional_current_user
from ...core.exceptions import ValidationException
from ...services.odoo_service import OdooService


class PaginationParams:
    """Pagination parameters for list endpoints"""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="Page number"),
        limit: int = Query(20, ge=1, le=100, description="Items per page"),
        offset: Optional[int] = Query(None, ge=0, description="Offset for pagination"),
    ):
        self.page = page
        self.limit = limit
        self.offset = offset if offset is not None else (page - 1) * limit

    @property
    def dict(self) -> Dict[str, int]:
        return {"page": self.page, "limit": self.limit, "offset": self.offset}


class SortParams:
    """Sorting parameters for list endpoints"""

    def __init__(
        self,
        sort_by: Optional[str] = Query(None, description="Field to sort by"),
        sort_order: str = Query(
            "asc", pattern="^(asc|desc)$", description="Sort order"
        ),
    ):
        self.sort_by = sort_by
        self.sort_order = sort_order

    @property
    def dict(self) -> Dict[str, str]:
        return {"sort_by": self.sort_by, "sort_order": self.sort_order}


class FilterParams:
    """Common filter parameters"""

    def __init__(
        self,
        search: Optional[str] = Query(None, description="Search query"),
        category_id: Optional[int] = Query(None, description="Filter by category"),
        brand: Optional[str] = Query(None, description="Filter by brand"),
        min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
        max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
        in_stock: Optional[bool] = Query(
            None, description="Filter by stock availability"
        ),
        featured: Optional[bool] = Query(None, description="Filter featured items"),
        on_sale: Optional[bool] = Query(None, description="Filter items on sale"),
    ):
        self.search = search
        self.category_id = category_id
        self.brand = brand
        self.min_price = min_price
        self.max_price = max_price
        self.in_stock = in_stock
        self.featured = featured
        self.on_sale = on_sale

    @property
    def dict(self) -> Dict[str, Any]:
        return {
            k: v
            for k, v in {
                "search": self.search,
                "category_id": self.category_id,
                "brand": self.brand,
                "min_price": self.min_price,
                "max_price": self.max_price,
                "in_stock": self.in_stock,
                "featured": self.featured,
                "on_sale": self.on_sale,
            }.items()
            if v is not None
        }


# Dependency functions
async def get_pagination(params: PaginationParams = Depends()) -> Dict[str, int]:
    """Get pagination parameters"""
    return params.dict


async def get_sorting(params: SortParams = Depends()) -> Dict[str, str]:
    """Get sorting parameters"""
    return params.dict


async def get_filters(params: FilterParams = Depends()) -> Dict[str, Any]:
    """Get filter parameters"""
    return params.dict


async def get_odoo_service() -> OdooService:
    """Get Odoo service instance"""
    return OdooService()


async def get_current_user_context(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get current user context with additional info from Odoo"""
    odoo = OdooService()

    try:
        # Get full user details from Odoo
        user_details = await odoo.get_user_details(current_user["user_id"])

        return {**current_user, **user_details, "is_authenticated": True}
    except Exception:
        # Fallback to basic user info
        return {**current_user, "is_authenticated": True}


async def get_optional_user_context(
    current_user: Optional[Dict[str, Any]] = Depends(get_optional_current_user),
) -> Optional[Dict[str, Any]]:
    """Get optional user context"""
    if not current_user:
        return None

    return await get_current_user_context(current_user)


async def require_authentication(
    current_user: Dict[str, Any] = Depends(get_current_user),
) -> Dict[str, Any]:
    """Require user authentication"""
    return current_user


async def get_device_info(request: Request) -> Dict[str, Any]:
    """Extract device information from request headers"""
    headers = request.headers

    return {
        "user_agent": headers.get("user-agent", ""),
        "device_id": headers.get("x-device-id"),
        "device_type": headers.get("x-device-type", "unknown"),
        "app_version": headers.get("x-app-version"),
        "platform_version": headers.get("x-platform-version"),
        "client_ip": getattr(request.state, "client_ip", "unknown"),
    }


def validate_language(lang: str = Query("en", description="Language code")) -> str:
    """Validate and return language code"""
    supported_languages = ["en", "ar", "fr", "es"]

    if lang not in supported_languages:
        raise ValidationException(
            message=f"Unsupported language: {lang}",
            field="lang",
            errors=[
                {
                    "field": "lang",
                    "message": f"Language must be one of: {', '.join(supported_languages)}",
                }
            ],
        )

    return lang


def validate_currency(currency: str = Query("USD", description="Currency code")) -> str:
    """Validate and return currency code"""
    supported_currencies = ["USD", "EUR", "SAR", "AED"]

    if currency not in supported_currencies:
        raise ValidationException(
            message=f"Unsupported currency: {currency}",
            field="currency",
            errors=[
                {
                    "field": "currency",
                    "message": f"Currency must be one of: {', '.join(supported_currencies)}",
                }
            ],
        )

    return currency


# Export commonly used dependencies
__all__ = [
    "PaginationParams",
    "SortParams",
    "FilterParams",
    "get_pagination",
    "get_sorting",
    "get_filters",
    "get_odoo_service",
    "get_current_user_context",
    "get_optional_user_context",
    "require_authentication",
    "get_device_info",
    "validate_language",
    "validate_currency",
]
