# -*- coding: utf-8 -*-
"""
Odoo Integration Service
Handles all interactions with Odoo backend
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# Note: These imports would work in an Odoo environment
# For standalone testing, you'd need to mock these
try:
    from odoo import api, models, fields, _
    from odoo.exceptions import ValidationError, AccessError, UserError
    from odoo.http import request

    ODOO_AVAILABLE = True
except ImportError:
    # Fallback for development/testing without full Odoo
    ODOO_AVAILABLE = False

from ..core.config import get_settings
from ..core.exceptions import (
    DatabaseException,
    NotFoundException,
    ConflictException,
    ValidationException,
    BusinessRuleException,
)

settings = get_settings()
logger = logging.getLogger(__name__)


class OdooService:
    """Service for interacting with Odoo backend"""

    def __init__(self):
        self.odoo_available = ODOO_AVAILABLE
        if not self.odoo_available:
            logger.warning("Odoo not available - using mock mode")

    def _get_env(self):
        """Get Odoo environment"""
        if not self.odoo_available:
            raise DatabaseException("Odoo environment not available")

        if hasattr(request, "env"):
            return request.env
        else:
            # For background tasks, you'd need to create environment differently
            raise DatabaseException("No active Odoo environment")

    # User Management

    async def find_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find user by email address"""
        if not self.odoo_available:
            return None

        try:
            env = self._get_env()
            partner = env["res.partner"].sudo().search([("email", "=", email)], limit=1)

            if partner:
                return {
                    "id": partner.id,
                    "email": partner.email,
                    "name": partner.name,
                    "phone": partner.phone,
                    "is_company": partner.is_company,
                    "active": partner.active,
                }

            return None

        except Exception as e:
            logger.error(f"Error finding user by email: {str(e)}")
            raise DatabaseException(f"Database query failed: {str(e)}")

    async def find_user_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Find user by phone number"""
        if not self.odoo_available:
            return None

        try:
            env = self._get_env()
            partner = env["res.partner"].sudo().search([("phone", "=", phone)], limit=1)

            if partner:
                return {
                    "id": partner.id,
                    "email": partner.email,
                    "name": partner.name,
                    "phone": partner.phone,
                    "is_company": partner.is_company,
                    "active": partner.active,
                }

            return None

        except Exception as e:
            logger.error(f"Error finding user by phone: {str(e)}")
            raise DatabaseException(f"Database query failed: {str(e)}")

    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user/partner in Odoo"""
        if not self.odoo_available:
            raise DatabaseException("Odoo not available")

        try:
            env = self._get_env()

            # Prepare partner data
            partner_vals = {
                "name": f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip(),
                "email": user_data.get("email"),
                "phone": user_data.get("phone"),
                "is_company": False,
                "customer_rank": 1,  # Mark as customer
                "mobile_user": True,  # Custom field for mobile users
                "country_id": (
                    self._get_country_id(user_data.get("country_code"))
                    if user_data.get("country_code")
                    else None
                ),
                "lang": user_data.get("language", "en_US"),
                "tz": user_data.get("timezone", "UTC"),
            }

            # Remove None values
            partner_vals = {k: v for k, v in partner_vals.items() if v is not None}

            # Create partner
            partner = env["res.partner"].sudo().create(partner_vals)

            # Create user account if email is provided
            user = None
            if user_data.get("email"):
                try:
                    user_vals = {
                        "partner_id": partner.id,
                        "login": user_data["email"],
                        "groups_id": [(6, 0, [env.ref("base.group_portal").id])],
                    }
                    user = env["res.users"].sudo().create(user_vals)
                except Exception as e:
                    logger.warning(f"Failed to create user account: {str(e)}")

            # Create mobile device record if provided
            if user_data.get("device_id"):
                self._create_mobile_device(partner.id, user_data)

            return {
                "id": partner.id,
                "user_id": user.id if user else None,
                "email": partner.email,
                "name": partner.name,
                "phone": partner.phone,
                "created_at": partner.create_date,
            }

        except ValidationError as e:
            raise ValidationException(str(e))
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise DatabaseException(f"User creation failed: {str(e)}")

    async def get_user_details(self, user_id: int) -> Dict[str, Any]:
        """Get detailed user information"""
        if not self.odoo_available:
            return {"id": user_id, "name": "Mock User", "email": "mock@example.com"}

        try:
            env = self._get_env()
            partner = env["res.partner"].sudo().browse(user_id)

            if not partner.exists():
                raise NotFoundException(f"User with ID {user_id} not found")

            return {
                "id": partner.id,
                "email": partner.email,
                "phone": partner.phone,
                "first_name": partner.name.split()[0] if partner.name else "",
                "last_name": (
                    " ".join(partner.name.split()[1:])
                    if partner.name and len(partner.name.split()) > 1
                    else ""
                ),
                "full_name": partner.name,
                "avatar_url": (
                    f"/web/image/res.partner/{partner.id}/image_1920"
                    if partner.image_1920
                    else None
                ),
                "country_code": partner.country_id.code if partner.country_id else None,
                "city": partner.city,
                "language": partner.lang or "en_US",
                "timezone": partner.tz,
                "is_active": partner.active,
                "created_at": partner.create_date,
                "updated_at": partner.write_date,
            }

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error getting user details: {str(e)}")
            raise DatabaseException(f"Failed to fetch user details: {str(e)}")

    async def update_user(
        self, user_id: int, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user information"""
        if not self.odoo_available:
            return {"id": user_id, "updated": True}

        try:
            env = self._get_env()
            partner = env["res.partner"].sudo().browse(user_id)

            if not partner.exists():
                raise NotFoundException(f"User with ID {user_id} not found")

            # Prepare update values
            update_vals = {}

            if "first_name" in update_data or "last_name" in update_data:
                first_name = update_data.get(
                    "first_name", partner.name.split()[0] if partner.name else ""
                )
                last_name = update_data.get(
                    "last_name",
                    (
                        " ".join(partner.name.split()[1:])
                        if partner.name and len(partner.name.split()) > 1
                        else ""
                    ),
                )
                update_vals["name"] = f"{first_name} {last_name}".strip()

            if "email" in update_data:
                update_vals["email"] = update_data["email"]

            if "phone" in update_data:
                update_vals["phone"] = update_data["phone"]

            if "city" in update_data:
                update_vals["city"] = update_data["city"]

            if "country_code" in update_data:
                update_vals["country_id"] = self._get_country_id(
                    update_data["country_code"]
                )

            # Update partner
            if update_vals:
                partner.sudo().write(update_vals)

            return await self.get_user_details(user_id)

        except NotFoundException:
            raise
        except Exception as e:
            logger.error(f"Error updating user: {str(e)}")
            raise DatabaseException(f"User update failed: {str(e)}")

    # Product Management

    async def get_products(
        self,
        page: int = 1,
        limit: int = 20,
        search: Optional[str] = None,
        category_id: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Get products with pagination and filters"""
        if not self.odoo_available:
            return {"products": [], "total": 0, "page": page, "limit": limit}

        try:
            env = self._get_env()
            domain = [("sale_ok", "=", True), ("active", "=", True)]

            # Add search filter
            if search:
                domain.extend(
                    [
                        "|",
                        "|",
                        ("name", "ilike", search),
                        ("description", "ilike", search),
                        ("default_code", "ilike", search),
                    ]
                )

            # Add category filter
            if category_id:
                domain.append(("categ_id", "=", category_id))

            # Add additional filters
            if filters:
                if filters.get("min_price") is not None:
                    domain.append(("list_price", ">=", filters["min_price"]))
                if filters.get("max_price") is not None:
                    domain.append(("list_price", "<=", filters["max_price"]))
                if filters.get("in_stock"):
                    domain.append(("qty_available", ">", 0))

            # Count total
            total = env["product.product"].sudo().search_count(domain)

            # Get products with pagination
            offset = (page - 1) * limit
            products = (
                env["product.product"]
                .sudo()
                .search(domain, limit=limit, offset=offset, order="name asc")
            )

            # Format product data
            product_data = []
            for product in products:
                product_data.append(
                    {
                        "id": product.id,
                        "name": product.name,
                        "description": product.description_sale or product.description,
                        "price": product.list_price,
                        "currency": env.company.currency_id.name,
                        "sku": product.default_code,
                        "category": product.categ_id.name if product.categ_id else None,
                        "category_id": (
                            product.categ_id.id if product.categ_id else None
                        ),
                        "image_url": (
                            f"/web/image/product.product/{product.id}/image_1920"
                            if product.image_1920
                            else None
                        ),
                        "in_stock": product.qty_available > 0,
                        "stock_quantity": product.qty_available,
                        "rating": 0.0,  # Would implement rating system
                        "review_count": 0,  # Would implement review system
                    }
                )

            return {
                "products": product_data,
                "total": total,
                "page": page,
                "limit": limit,
                "pages": (total + limit - 1) // limit,
            }

        except Exception as e:
            logger.error(f"Error getting products: {str(e)}")
            raise DatabaseException(f"Product query failed: {str(e)}")

    # Utility methods

    def _get_country_id(self, country_code: str) -> Optional[int]:
        """Get country ID from country code"""
        if not self.odoo_available:
            return None

        try:
            env = self._get_env()
            country = (
                env["res.country"]
                .sudo()
                .search([("code", "=", country_code.upper())], limit=1)
            )
            return country.id if country else None
        except:
            return None

    def _create_mobile_device(self, partner_id: int, device_data: Dict[str, Any]):
        """Create mobile device record"""
        if not self.odoo_available:
            return

        try:
            env = self._get_env()

            # Check if mobile.device model exists
            if "mobile.device" not in env:
                logger.warning(
                    "mobile.device model not found - skipping device creation"
                )
                return

            device_vals = {
                "partner_id": partner_id,
                "device_id": device_data.get("device_id"),
                "device_type": device_data.get("device_type", "unknown"),
                "is_active": True,
                "last_used": fields.Datetime.now(),
            }

            env["mobile.device"].sudo().create(device_vals)

        except Exception as e:
            logger.warning(f"Failed to create mobile device: {str(e)}")

    async def validate_user_credentials(
        self, identifier: str, password: str
    ) -> Optional[Dict[str, Any]]:
        """Validate user credentials"""
        if not self.odoo_available:
            return {"id": 1, "email": identifier, "valid": True}

        try:
            env = self._get_env()

            # Find user by email or phone
            user = (
                env["res.users"]
                .sudo()
                .search(
                    [
                        "|",
                        ("login", "=", identifier),
                        ("partner_id.phone", "=", identifier),
                    ],
                    limit=1,
                )
            )

            if not user:
                return None

            # Validate password
            try:
                user.sudo().check_credentials(password)
                return {
                    "id": user.partner_id.id,
                    "user_id": user.id,
                    "email": user.login,
                    "name": user.name,
                    "active": user.active,
                }
            except:
                return None

        except Exception as e:
            logger.error(f"Error validating credentials: {str(e)}")
            return None
