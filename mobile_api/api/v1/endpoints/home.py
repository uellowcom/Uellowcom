# -*- coding: utf-8 -*-
"""Home page endpoints for Mobile API"""

from fastapi import APIRouter, Depends, Query
from typing import List, Optional, Dict, Any

from ....schemas.home_schemas import (
    IntroPageResponse, GeneralSettings, SliderItem,
    CategoryItem, FlashSaleResponse, MiniBanner,
    ExtendedProduct, PopularCategory
)
from ....services.home_service import HomeService
from ....core.security import get_current_user

router = APIRouter(prefix="/home", tags=["Home"])
home_service = HomeService()


@router.get("")
async def get_home_data(current_user: Optional[Dict] = Depends(get_current_user)):
    """Get complete home page data"""
    home_data = await home_service.get_home_data(
        user_id=current_user["user_id"] if current_user else None
    )
    return home_data


@router.get("/intro-page", response_model=IntroPageResponse)
async def get_intro_page():
    """Get splash screen and intro page data"""
    intro_data = await home_service.get_intro_page()
    return intro_data


@router.get("/general-settings", response_model=GeneralSettings)
async def get_general_settings():
    """Get general app settings and configuration"""
    settings = await home_service.get_general_settings()
    return settings


@router.get("/slider", response_model=List[SliderItem])
async def get_home_sliders():
    """Get home page slider/banner items"""
    sliders = await home_service.get_sliders()
    return sliders


@router.get("/categories", response_model=List[CategoryItem])
async def get_home_categories():
    """Get featured categories for home page"""
    categories = await home_service.get_featured_categories()
    return categories


@router.get("/flash-sale", response_model=FlashSaleResponse)
async def get_flash_sale():
    """Get current flash sale information"""
    flash_sale = await home_service.get_flash_sale()
    return flash_sale


@router.get("/mini-banner", response_model=List[MiniBanner])
async def get_mini_banners():
    """Get mini promotional banners"""
    banners = await home_service.get_mini_banners()
    return banners


@router.get("/extend-products", response_model=List[ExtendedProduct])
async def get_extended_products(
    category_id: Optional[int] = None,
    limit: int = Query(10, ge=1, le=50)
):
    """Get extended product recommendations"""
    products = await home_service.get_extended_products(
        category_id=category_id,
        limit=limit
    )
    return products


@router.get("/recent-view-products")
async def get_recent_view_products(
    current_user: Optional[Dict] = Depends(get_current_user),
    limit: int = Query(10, ge=1, le=20)
):
    """Get recently viewed products"""
    if not current_user:
        return []
    
    products = await home_service.get_recent_viewed_products(
        user_id=current_user["user_id"],
        limit=limit
    )
    return products


@router.get("/popular-categories", response_model=List[PopularCategory])
async def get_popular_categories():
    """Get popular/trending categories"""
    categories = await home_service.get_popular_categories()
    return categories


@router.get("/hit-products")
async def get_hit_products(limit: int = Query(10, ge=1, le=50)):
    """Get hit/bestselling products"""
    products = await home_service.get_hit_products(limit=limit)
    return products
