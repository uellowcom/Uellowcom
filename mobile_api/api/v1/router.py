# -*- coding: utf-8 -*-
"""Main API router for v1 endpoints"""

from fastapi import APIRouter
from .endpoints import (
    auth, home, products, orders, users,
    blog, reviews, notifications, wallet,
    coupons, categories
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router)
api_router.include_router(home.router)
api_router.include_router(products.router)
api_router.include_router(orders.router)
api_router.include_router(users.router)
api_router.include_router(blog.router)
api_router.include_router(reviews.router)
api_router.include_router(notifications.router)
api_router.include_router(wallet.router)
api_router.include_router(coupons.router)
api_router.include_router(categories.router)
