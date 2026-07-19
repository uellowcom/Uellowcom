# -*- coding: utf-8 -*-
"""
Main API v1 Router
Consolidates all API endpoints for version 1
"""

from fastapi import APIRouter

from .endpoints import (
    auth,
    products,
    categories,
    cart,
    orders,
    users,
    wallet,
    notifications,
    home,
    reviews,
    coupons,
    addresses,
    wishlist,
)

# Create main API router
api_v1_router = APIRouter()

# Include all endpoint routers with proper tags and prefixes
api_v1_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

api_v1_router.include_router(products.router, prefix="/products", tags=["Products"])

api_v1_router.include_router(
    categories.router, prefix="/categories", tags=["Categories"]
)

api_v1_router.include_router(cart.router, prefix="/cart", tags=["Shopping Cart"])

api_v1_router.include_router(orders.router, prefix="/orders", tags=["Orders"])

api_v1_router.include_router(users.router, prefix="/users", tags=["Users"])

api_v1_router.include_router(
    wallet.router, prefix="/wallet", tags=["Wallet & Payments"]
)

api_v1_router.include_router(
    notifications.router, prefix="/notifications", tags=["Notifications"]
)

api_v1_router.include_router(home.router, prefix="/home", tags=["Home & Dashboard"])

api_v1_router.include_router(
    reviews.router, prefix="/reviews", tags=["Reviews & Ratings"]
)

api_v1_router.include_router(
    coupons.router, prefix="/coupons", tags=["Coupons & Discounts"]
)

api_v1_router.include_router(addresses.router, prefix="/addresses", tags=["Addresses"])

api_v1_router.include_router(wishlist.router, prefix="/wishlist", tags=["Wishlist"])
