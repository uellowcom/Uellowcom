# -*- coding: utf-8 -*-
from typing import Annotated, Dict, Any, List, Optional
from datetime import datetime

from odoo.api import Environment
from odoo.http import request

from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel

from ..dependencies import (
    odoo_env,
    get_current_user,
    get_optional_user,
    get_authenticated_partner_env,
)

# Define the router
router = APIRouter(prefix="/mobile/v1/products", tags=["products"])


# Models for response
class ProductCategory(BaseModel):
    id: int
    name: str
    image_url: Optional[str] = None
    parent_id: Optional[int] = None
    child_count: int = 0


class ProductImage(BaseModel):
    id: int
    image_url: str
    sequence: int = 0


class ProductVariant(BaseModel):
    id: int
    name: str
    attribute_value_ids: List[int] = []
    attribute_values: List[str] = []
    price: float
    list_price: float
    currency_symbol: str
    in_stock: bool = True
    qty_available: float = 0


class Product(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    short_description: Optional[str] = None
    price: float
    list_price: float
    currency_symbol: str
    discount_percentage: Optional[float] = None
    rating: Optional[float] = None
    review_count: int = 0
    in_stock: bool = True
    qty_available: float = 0
    images: List[ProductImage] = []
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    variants: List[ProductVariant] = []
    is_in_wishlist: bool = False


class ProductListResponse(BaseModel):
    products: List[Product]
    total_count: int
    offset: int
    limit: int


class ApiResponse(BaseModel):
    success: bool = True
    error: Optional[str] = None
    data: Optional[Dict[str, Any]] = None


def get_image_url(env, record, field="image_1920", size=None):
    """Get the image URL for a record"""
    if not record or not record[field]:
        return None

    base_url = env["ir.config_parameter"].sudo().get_param("web.base.url")
    if size:
        return f"{base_url}/web/image?model={record._name}&id={record.id}&field={field}&size={size}"
    else:
        return f"{base_url}/web/image?model={record._name}&id={record.id}&field={field}"


def format_product(env, product, partner=None, include_variants=False):
    """Format a product for API response"""
    currency = env.company.currency_id
    currency_symbol = currency.symbol

    # Calculate prices
    price = product.list_price
    list_price = product.list_price

    # Check if product is in stock
    in_stock = product.sudo().qty_available > 0 if product.type != "service" else True

    # Calculate discount percentage
    discount_percentage = None
    if list_price > price and list_price > 0:
        discount_percentage = round((1 - (price / list_price)) * 100, 2)

    # Get product images
    images = []
    if product.image_1920:
        images.append(
            {"id": product.id, "image_url": get_image_url(env, product), "sequence": 0}
        )

    # Get product variants if requested
    variants = []
    if (
        include_variants
        and product.product_variant_ids
        and len(product.product_variant_ids) > 1
    ):
        for variant in product.product_variant_ids:
            variant_price = variant.list_price
            variant_list_price = variant.list_price

            # Format attribute values
            attribute_values = []
            attribute_value_ids = []
            for value in variant.product_template_attribute_value_ids:
                attribute_values.append(value.name)
                attribute_value_ids.append(value.id)

            variants.append(
                {
                    "id": variant.id,
                    "name": variant.display_name,
                    "attribute_value_ids": attribute_value_ids,
                    "attribute_values": attribute_values,
                    "price": variant_price,
                    "list_price": variant_list_price,
                    "currency_symbol": currency_symbol,
                    "in_stock": (
                        variant.sudo().qty_available > 0
                        if variant.type != "service"
                        else True
                    ),
                    "qty_available": (
                        variant.sudo().qty_available if variant.type != "service" else 0
                    ),
                }
            )

    # Check if product is in wishlist
    is_in_wishlist = False
    if partner:
        wishlist = (
            env["product.wishlist"]
            .sudo()
            .search(
                [("product_id", "=", product.id), ("partner_id", "=", partner.id)],
                limit=1,
            )
        )
        is_in_wishlist = bool(wishlist)

    # Get product category
    category_id = None
    category_name = None
    if product.public_categ_ids:
        category = product.public_categ_ids[0]
        category_id = category.id
        category_name = category.name

    # Format product data
    return {
        "id": product.id,
        "name": product.name,
        "description": product.description_sale or "",
        "short_description": product.description or "",
        "price": price,
        "list_price": list_price,
        "currency_symbol": currency_symbol,
        "discount_percentage": discount_percentage,
        "rating": product.rating_avg if hasattr(product, "rating_avg") else None,
        "review_count": product.rating_count if hasattr(product, "rating_count") else 0,
        "in_stock": in_stock,
        "qty_available": (
            product.sudo().qty_available if product.type != "service" else 0
        ),
        "images": images,
        "category_id": category_id,
        "category_name": category_name,
        "variants": variants,
        "is_in_wishlist": is_in_wishlist,
    }


@router.get("/categories", response_model=ApiResponse)
async def get_categories(
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Optional[Dict[str, Any]], Depends(get_optional_user)],
):
    """Get product categories"""
    try:
        # Get all public categories
        category_model = env["product.public.category"].sudo()
        categories = category_model.search([])

        result = []
        for category in categories:
            child_count = category_model.search_count([("parent_id", "=", category.id)])

            result.append(
                {
                    "id": category.id,
                    "name": category.name,
                    "image_url": get_image_url(env, category, "image_1920"),
                    "parent_id": category.parent_id.id if category.parent_id else None,
                    "child_count": child_count,
                }
            )

        return {"success": True, "data": {"categories": result}}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("", response_model=ApiResponse)
async def get_products(
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Optional[Dict[str, Any]], Depends(get_optional_user)],
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
    """Get products with optional filtering"""
    try:
        # Get partner from current user if available
        partner = None
        if current_user:
            partner = env["res.partner"].browse(current_user.get("partner_id"))

        # Build domain for product search
        domain = [("website_published", "=", True)]

        # Add category filter if provided
        if category_id:
            domain.append(("public_categ_ids", "child_of", category_id))

        # Add search filter if provided
        if search:
            domain.append(("name", "ilike", search))

        # Get products
        product_model = env["product.template"].sudo()
        products = product_model.search(domain, limit=limit, offset=offset)
        total_count = product_model.search_count(domain)

        # Format products for response
        result = []
        for product in products:
            result.append(format_product(env, product, partner))

        return {
            "success": True,
            "data": {
                "products": result,
                "total_count": total_count,
                "offset": offset,
                "limit": limit,
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/{product_id}", response_model=ApiResponse)
async def get_product_detail(
    product_id: int,
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Optional[Dict[str, Any]], Depends(get_optional_user)],
):
    """Get product detail by ID"""
    try:
        # Get partner from current user if available
        partner = None
        if current_user:
            partner = env["res.partner"].browse(current_user.get("partner_id"))

        # Get product
        product = env["product.template"].sudo().browse(product_id)
        if not product.exists() or not product.website_published:
            return {"success": False, "error": "Product not found"}

        # Format product for response with variants
        product_data = format_product(env, product, partner, include_variants=True)

        return {"success": True, "data": {"product": product_data}}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.post("/wishlist/{product_id}", response_model=ApiResponse)
async def toggle_wishlist(
    product_id: int,
    env: Annotated[Environment, Depends(get_authenticated_partner_env)],
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
):
    """Toggle product in wishlist"""
    try:
        # Get partner from current user
        partner_id = current_user.get("partner_id")
        if not partner_id:
            return {"success": False, "error": "User has no associated partner"}

        # Get product
        product = env["product.template"].sudo().browse(product_id)
        if not product.exists() or not product.website_published:
            return {"success": False, "error": "Product not found"}

        # Get product variant (first one if template)
        product_id = (
            product.product_variant_id.id
            if product.product_variant_id
            else product.product_variant_ids[0].id
        )

        # Check if product is already in wishlist
        wishlist_model = env["product.wishlist"].sudo()
        wishlist = wishlist_model.search(
            [("product_id", "=", product_id), ("partner_id", "=", partner_id)], limit=1
        )

        if wishlist:
            # Remove from wishlist
            wishlist.unlink()
            return {"success": True, "data": {"in_wishlist": False}}
        else:
            # Add to wishlist
            wishlist_model.create(
                {
                    "product_id": product_id,
                    "partner_id": partner_id,
                    "pricelist_id": env.user.partner_id.property_product_pricelist.id,
                }
            )
            return {"success": True, "data": {"in_wishlist": True}}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/wishlist", response_model=ApiResponse)
async def get_wishlist(
    env: Annotated[Environment, Depends(get_authenticated_partner_env)],
    current_user: Annotated[Dict[str, Any], Depends(get_current_user)],
):
    """Get user's wishlist"""
    try:
        # Get partner from current user
        partner_id = current_user.get("partner_id")
        if not partner_id:
            return {"success": False, "error": "User has no associated partner"}

        # Get wishlist items
        wishlist_model = env["product.wishlist"].sudo()
        wishlist_items = wishlist_model.search([("partner_id", "=", partner_id)])

        # Get products from wishlist
        products = []
        for item in wishlist_items:
            product = item.product_id.product_tmpl_id
            if product.exists() and product.website_published:
                products.append(format_product(env, product))

        return {
            "success": True,
            "data": {"products": products, "total_count": len(products)},
        }
    except Exception as e:
        return {"success": False, "error": str(e)}
