# -*- coding: utf-8 -*-
from typing import Annotated, Dict, Any, List, Optional
from datetime import datetime

from odoo.api import Environment

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ..dependencies import odoo_env, get_current_user, get_optional_user

# Define the router
router = APIRouter(prefix="/mobile/v1/home", tags=["home"])


# Models for response
class Banner(BaseModel):
    id: int
    name: str
    image_url: str
    target_type: str
    target_id: Optional[int] = None
    sequence: int = 0


class Category(BaseModel):
    id: int
    name: str
    image_url: Optional[str] = None


class Product(BaseModel):
    id: int
    name: str
    image_url: Optional[str] = None
    price: float
    currency_symbol: str
    discount_percentage: Optional[float] = None


class HomeSection(BaseModel):
    id: int
    name: str
    section_type: str
    items: List[Any] = []


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


def format_simple_product(env, product):
    """Format a product for simple display in home sections"""
    currency = env.company.currency_id
    currency_symbol = currency.symbol

    # Calculate prices
    price = product.list_price
    list_price = product.list_price

    # Calculate discount percentage
    discount_percentage = None
    if list_price > price and list_price > 0:
        discount_percentage = round((1 - (price / list_price)) * 100, 2)

    return {
        "id": product.id,
        "name": product.name,
        "image_url": get_image_url(env, product),
        "price": price,
        "currency_symbol": currency_symbol,
        "discount_percentage": discount_percentage,
    }


@router.get("", response_model=ApiResponse)
async def get_home_data(
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Optional[Dict[str, Any]], Depends(get_optional_user)],
):
    """Get home page data"""
    try:
        result = {"banners": [], "sections": []}

        # Get banners
        if hasattr(env, "ref") and env.ref(
            "website.carousel_snippet_options", raise_if_not_found=False
        ):
            # If website module is installed, get banners from website carousel
            carousel_slides = (
                env["website.carousel.slide"]
                .sudo()
                .search([("is_published", "=", True)], order="sequence")
            )

            for slide in carousel_slides:
                target_type = "none"
                target_id = None

                # Check if slide has a link to a product or category
                if slide.url and "/product/" in slide.url:
                    try:
                        product_id = int(slide.url.split("/product/")[1].split("/")[0])
                        product = env["product.template"].sudo().browse(product_id)
                        if product.exists():
                            target_type = "product"
                            target_id = product_id
                    except:
                        pass
                elif slide.url and "/category/" in slide.url:
                    try:
                        category_id = int(
                            slide.url.split("/category/")[1].split("/")[0]
                        )
                        category = (
                            env["product.public.category"].sudo().browse(category_id)
                        )
                        if category.exists():
                            target_type = "category"
                            target_id = category_id
                    except:
                        pass

                result["banners"].append(
                    {
                        "id": slide.id,
                        "name": slide.name,
                        "image_url": get_image_url(env, slide, "image"),
                        "target_type": target_type,
                        "target_id": target_id,
                        "sequence": slide.sequence,
                    }
                )

        # Get featured categories
        categories = (
            env["product.public.category"].sudo().search([], limit=10, order="sequence")
        )

        if categories:
            category_items = []
            for category in categories:
                category_items.append(
                    {
                        "id": category.id,
                        "name": category.name,
                        "image_url": get_image_url(env, category),
                    }
                )

            if category_items:
                result["sections"].append(
                    {
                        "id": 1,
                        "name": "Featured Categories",
                        "section_type": "categories",
                        "items": category_items,
                    }
                )

        # Get featured products
        featured_products = (
            env["product.template"]
            .sudo()
            .search(
                [("website_published", "=", True), ("featured_in_app", "=", True)],
                limit=10,
                order="id desc",
            )
        )

        # If no products with featured_in_app flag, get newest products
        if not featured_products:
            featured_products = (
                env["product.template"]
                .sudo()
                .search([("website_published", "=", True)], limit=10, order="id desc")
            )

        if featured_products:
            product_items = []
            for product in featured_products:
                product_items.append(format_simple_product(env, product))

            if product_items:
                result["sections"].append(
                    {
                        "id": 2,
                        "name": "Featured Products",
                        "section_type": "products",
                        "items": product_items,
                    }
                )

        # Get best selling products
        best_selling = (
            env["product.template"]
            .sudo()
            .search(
                [("website_published", "=", True), ("sales_count", ">", 0)],
                limit=10,
                order="sales_count desc",
            )
        )

        if best_selling:
            product_items = []
            for product in best_selling:
                product_items.append(format_simple_product(env, product))

            if product_items:
                result["sections"].append(
                    {
                        "id": 3,
                        "name": "Best Selling",
                        "section_type": "products",
                        "items": product_items,
                    }
                )

        # Get discounted products
        discounted_products = (
            env["product.template"]
            .sudo()
            .search(
                [("website_published", "=", True), ("list_price", ">", 0)], limit=20
            )
        )

        if discounted_products:
            product_items = []
            for product in discounted_products:
                if product.list_price > product.price and product.list_price > 0:
                    discount = round(
                        (1 - (product.price / product.list_price)) * 100, 2
                    )
                    if discount > 5:  # Only include products with >5% discount
                        product_items.append(format_simple_product(env, product))
                        if len(product_items) >= 10:
                            break

            if product_items:
                result["sections"].append(
                    {
                        "id": 4,
                        "name": "Special Offers",
                        "section_type": "products",
                        "items": product_items,
                    }
                )

        return {"success": True, "data": result}
    except Exception as e:
        return {"success": False, "error": str(e)}


@router.get("/search-suggestions", response_model=ApiResponse)
async def get_search_suggestions(
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Optional[Dict[str, Any]], Depends(get_optional_user)],
):
    """Get search suggestions for the home page"""
    try:
        # Get popular categories
        categories = (
            env["product.public.category"].sudo().search([], limit=5, order="sequence")
        )

        category_suggestions = []
        for category in categories:
            category_suggestions.append(
                {"id": category.id, "name": category.name, "type": "category"}
            )

        # Get popular products
        products = (
            env["product.template"]
            .sudo()
            .search(
                [("website_published", "=", True), ("sales_count", ">", 0)],
                limit=5,
                order="sales_count desc",
            )
        )

        product_suggestions = []
        for product in products:
            product_suggestions.append(
                {"id": product.id, "name": product.name, "type": "product"}
            )

        # Combine suggestions
        suggestions = category_suggestions + product_suggestions

        return {"success": True, "data": {"suggestions": suggestions}}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_trending_searches(env):
    """Get trending search terms"""
    # This will be implemented later
    return {"success": True, "data": {"searches": []}}
