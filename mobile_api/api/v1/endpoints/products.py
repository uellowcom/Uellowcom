# -*- coding: utf-8 -*-
"""Product endpoints for Mobile API"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional, Dict, Any

from ....schemas.product_schemas import (
    ProductResponse,
    ProductDetail,
    ProductSearch,
    ProductReview,
    CreateReview,
    WishlistItem,
    ProductVariation,
    FilterAttribute,
)
from ....services.product_service import ProductService
from ....core.security import get_current_user

router = APIRouter(prefix="/products", tags=["Products"])
product_service = ProductService()


@router.get("", response_model=List[ProductResponse])
async def get_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category_id: Optional[int] = None,
    search: Optional[str] = None,
    sort_by: Optional[str] = Query("name", pattern="^(name|price|rating|created_at)$"),
    order: Optional[str] = Query("asc", pattern="^(asc|desc)$"),
):
    """Get list of products with pagination and filters"""
    products = await product_service.get_products(
        page=page,
        limit=limit,
        category_id=category_id,
        search=search,
        sort_by=sort_by,
        order=order,
    )
    return products


@router.get("/categories", response_model=List[Dict[str, Any]])
async def get_product_categories():
    """Get all product categories"""
    categories = await product_service.get_categories()
    return categories


@router.get("/flash-sale", response_model=List[ProductResponse])
async def get_flash_sale_products():
    """Get current flash sale products"""
    products = await product_service.get_flash_sale_products()
    return products


@router.get("/hit-products", response_model=List[ProductResponse])
async def get_hit_products():
    """Get trending/hit products"""
    products = await product_service.get_hit_products()
    return products


@router.get("/recent-view", response_model=List[ProductResponse])
async def get_recent_view_products(current_user: Dict = Depends(get_current_user)):
    """Get recently viewed products for current user"""
    products = await product_service.get_recent_viewed(current_user["user_id"])
    return products


@router.get("/search")
async def search_products(
    q: str = Query(..., min_length=2),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Search products by name, description, or SKU"""
    results = await product_service.search_products(q, page, limit)
    return results


@router.get("/barcode/{barcode}")
async def get_product_by_barcode(barcode: str):
    """Get product by barcode"""
    product = await product_service.get_by_barcode(barcode)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return product


@router.get("/filter-attributes")
async def get_filter_attributes(category_id: Optional[int] = None):
    """Get available filter attributes for category"""
    attributes = await product_service.get_filter_attributes(category_id)
    return attributes


@router.get("/discount-rules")
async def get_discount_rules():
    """Get active discount rules"""
    rules = await product_service.get_discount_rules()
    return rules


@router.get("/{product_id}", response_model=ProductDetail)
async def get_product_detail(
    product_id: int, current_user: Optional[Dict] = Depends(get_current_user)
):
    """Get detailed product information"""
    product = await product_service.get_product_detail(product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    # Track view if user is authenticated
    if current_user:
        await product_service.track_product_view(current_user["user_id"], product_id)

    return product


@router.get("/{product_id}/variations")
async def get_product_variations(product_id: int):
    """Get product variations (size, color, etc.)"""
    variations = await product_service.get_product_variations(product_id)
    return variations


@router.get("/{product_id}/reviews", response_model=List[ProductReview])
async def get_product_reviews(
    product_id: int, page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=50)
):
    """Get product reviews with pagination"""
    reviews = await product_service.get_product_reviews(product_id, page, limit)
    return reviews


@router.post("/{product_id}/reviews", response_model=ProductReview)
async def create_product_review(
    product_id: int,
    review_data: CreateReview,
    current_user: Dict = Depends(get_current_user),
):
    """Create a review for a product"""
    # Check if user has purchased the product
    has_purchased = await product_service.user_has_purchased(
        current_user["user_id"], product_id
    )

    if not has_purchased:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must purchase this product before reviewing",
        )

    review = await product_service.create_review(
        user_id=current_user["user_id"], product_id=product_id, review_data=review_data
    )
    return review


# Wishlist endpoints
@router.get("/wishlist", response_model=List[WishlistItem])
async def get_wishlist(current_user: Dict = Depends(get_current_user)):
    """Get user's wishlist"""
    wishlist = await product_service.get_wishlist(current_user["user_id"])
    return wishlist


@router.post("/wishlist/check")
async def check_wishlist_item(
    product_id: int, current_user: Dict = Depends(get_current_user)
):
    """Check if product is in wishlist"""
    is_in_wishlist = await product_service.is_in_wishlist(
        current_user["user_id"], product_id
    )
    return {"product_id": product_id, "in_wishlist": is_in_wishlist}


@router.post("/wishlist/add")
async def add_to_wishlist(
    product_id: int, current_user: Dict = Depends(get_current_user)
):
    """Add product to wishlist"""
    await product_service.add_to_wishlist(current_user["user_id"], product_id)
    return {"message": "Product added to wishlist"}


@router.delete("/wishlist/remove")
async def remove_from_wishlist(
    product_id: int, current_user: Dict = Depends(get_current_user)
):
    """Remove product from wishlist"""
    await product_service.remove_from_wishlist(current_user["user_id"], product_id)
    return {"message": "Product removed from wishlist"}


# Stock notification
@router.post("/notify-stock")
async def notify_when_in_stock(
    product_id: int,
    email: Optional[str] = None,
    current_user: Optional[Dict] = Depends(get_current_user),
):
    """Subscribe to stock notifications for a product"""
    if not email and not current_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or authentication required",
        )

    notification_email = email or current_user.get("email")
    await product_service.subscribe_stock_notification(product_id, notification_email)
    return {"message": "You will be notified when product is back in stock"}
