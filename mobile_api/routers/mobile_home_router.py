# -*- coding: utf-8 -*-
"""Mobile Home Router using Odoo models"""

from typing import Annotated, List, Optional
import logging

from odoo.api import Environment
from odoo.addons.fastapi.dependencies import odoo_env
from odoo.addons.base.models.res_partner import Partner

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from ..dependencies import get_optional_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mobile/v1/home", tags=["Mobile Home"])


# Pydantic Models
class SliderItem(BaseModel):
    id: int
    title: str
    description: str = None
    image_url: str
    action_type: str  # product, category, url
    action_value: str
    is_active: bool


class CategoryItem(BaseModel):
    id: int
    name: str
    image_url: str = None
    product_count: int
    parent_id: int = None


class FlashSaleItem(BaseModel):
    id: int
    name: str
    original_price: float
    sale_price: float
    discount_percentage: float
    image_url: str = None
    end_time: str
    stock_quantity: int


@router.get("")
async def get_home_data(
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Partner, Depends(get_optional_user)] = None
):
    """Get complete home page data"""
    try:
        # Get featured categories
        featured_categories = env['product.category'].search([
            ('parent_id', '=', False)  # Top-level categories
        ], limit=8)
        
        categories = []
        for category in featured_categories:
            product_count = env['product.product'].search_count([
                ('categ_id', 'child_of', category.id),
                ('sale_ok', '=', True),
                ('active', '=', True)
            ])
            
            categories.append({
                'id': category.id,
                'name': category.name,
                'image_url': f'/web/image/product.category/{category.id}/image' if hasattr(category, 'image') else None,
                'product_count': product_count
            })
        
        # Get flash sale products (products with active pricelist items)
        flash_sale_products = []
        if hasattr(env['product.product'], 'pricelist_item_ids'):
            products_on_sale = env['product.product'].search([
                ('sale_ok', '=', True),
                ('active', '=', True),
                ('pricelist_item_ids', '!=', False)
            ], limit=10)
            
            for product in products_on_sale:
                if product.pricelist_item_ids:
                    pricelist_item = product.pricelist_item_ids[0]
                    if pricelist_item.fixed_price < product.list_price:
                        discount_pct = ((product.list_price - pricelist_item.fixed_price) / product.list_price) * 100
                        flash_sale_products.append({
                            'id': product.id,
                            'name': product.name,
                            'original_price': product.list_price,
                            'sale_price': pricelist_item.fixed_price,
                            'discount_percentage': round(discount_pct, 1),
                            'image_url': f'/web/image/product.product/{product.id}/image_1920' if product.image_1920 else None,
                            'stock_quantity': product.qty_available,
                        })
        
        # Get hit products (most viewed or bestselling)
        hit_products = env['product.product'].search([
            ('sale_ok', '=', True),
            ('active', '=', True)
        ], limit=8, order='mobile_view_count desc')
        
        hit_products_data = []
        for product in hit_products:
            in_wishlist = False
            if current_user:
                in_wishlist = env['mobile.wishlist'].is_in_wishlist(current_user.id, product.id)
            
            hit_products_data.append({
                'id': product.id,
                'name': product.name,
                'list_price': product.list_price,
                'currency': product.currency_id.name,
                'image_url': f'/web/image/product.product/{product.id}/image_1920' if product.image_1920 else None,
                'in_stock': product.qty_available > 0,
                'category': product.categ_id.name,
                'in_wishlist': in_wishlist,
                'view_count': product.mobile_view_count or 0
            })
        
        # Get recent viewed products for authenticated user
        recent_products = []
        if current_user:
            recent_products = env['mobile.product.view'].get_recent_viewed(current_user.id, limit=6)
        
        return {
            'categories': categories,
            'flash_sale': flash_sale_products,
            'hit_products': hit_products_data,
            'recent_products': recent_products,
            'user_authenticated': current_user is not None,
            'user_name': current_user.name if current_user else None
        }
        
    except Exception as e:
        logger.error(f"Error fetching home data: {e}")
        return {
            'categories': [],
            'flash_sale': [],
            'hit_products': [],
            'recent_products': [],
            'user_authenticated': False,
            'error': 'Failed to load home data'
        }


@router.get("/intro-page")
async def get_intro_page(
    env: Annotated[Environment, Depends(odoo_env)]
):
    """Get splash screen and intro page data"""
    try:
        # Get app configuration from ir.config_parameter
        config = env['ir.config_parameter'].sudo()
        
        intro_data = {
            'app_name': config.get_param('mobile_api.app_name', 'Yellow'),
            'app_version': config.get_param('mobile_api.app_version', '1.0.0'),
            'splash_logo': config.get_param('mobile_api.splash_logo', '/mobile/static/logo.png'),
            'intro_slides': [
                {
                    'title': 'Welcome to Yellow',
                    'description': 'Your ultimate shopping destination',
                    'image': '/mobile/static/intro1.png'
                },
                {
                    'title': 'Easy Shopping',
                    'description': 'Browse and buy with just a few taps',
                    'image': '/mobile/static/intro2.png'
                },
                {
                    'title': 'Fast Delivery',
                    'description': 'Get your orders delivered quickly',
                    'image': '/mobile/static/intro3.png'
                }
            ],
            'skip_intro': config.get_param('mobile_api.skip_intro', 'false') == 'true'
        }
        
        return intro_data
        
    except Exception as e:
        logger.error(f"Error fetching intro data: {e}")
        return {
            'app_name': 'Yellow',
            'app_version': '1.0.0',
            'intro_slides': []
        }


@router.get("/general-settings")
async def get_general_settings(
    env: Annotated[Environment, Depends(odoo_env)]
):
    """Get general app settings and configuration"""
    try:
        config = env['ir.config_parameter'].sudo()
        company = env.company
        
        settings = {
            'app_name': config.get_param('mobile_api.app_name', 'Yellow'),
            'currency': company.currency_id.name,
            'currency_symbol': company.currency_id.symbol,
            'company_name': company.name,
            'support_email': config.get_param('mobile_api.support_email', 'support@yellow.com'),
            'support_phone': config.get_param('mobile_api.support_phone', '+1234567890'),
            'terms_url': config.get_param('mobile_api.terms_url', '/terms'),
            'privacy_url': config.get_param('mobile_api.privacy_url', '/privacy'),
            'social_links': {
                'facebook': config.get_param('mobile_api.facebook_url', ''),
                'twitter': config.get_param('mobile_api.twitter_url', ''),
                'instagram': config.get_param('mobile_api.instagram_url', ''),
            },
            'features': {
                'wallet_enabled': config.get_param('mobile_api.wallet_enabled', 'true') == 'true',
                'reviews_enabled': config.get_param('mobile_api.reviews_enabled', 'true') == 'true',
                'wishlist_enabled': config.get_param('mobile_api.wishlist_enabled', 'true') == 'true',
                'notifications_enabled': config.get_param('mobile_api.notifications_enabled', 'true') == 'true',
            }
        }
        
        return settings
        
    except Exception as e:
        logger.error(f"Error fetching general settings: {e}")
        return {
            'app_name': 'Yellow',
            'currency': 'USD',
            'features': {
                'wallet_enabled': True,
                'reviews_enabled': True,
                'wishlist_enabled': True,
                'notifications_enabled': True,
            }
        }


@router.get("/categories")
async def get_featured_categories(
    env: Annotated[Environment, Depends(odoo_env)],
    limit: int = Query(8, ge=1, le=20)
):
    """Get featured categories for home page"""
    try:
        categories = env['product.category'].search([
            ('parent_id', '=', False)  # Top-level categories
        ], limit=limit)
        
        result = []
        for category in categories:
            product_count = env['product.product'].search_count([
                ('categ_id', 'child_of', category.id),
                ('sale_ok', '=', True),
                ('active', '=', True)
            ])
            
            result.append(CategoryItem(
                id=category.id,
                name=category.name,
                image_url=f'/web/image/product.category/{category.id}/image' if hasattr(category, 'image') else None,
                product_count=product_count,
                parent_id=category.parent_id.id if category.parent_id else None
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching featured categories: {e}")
        return []


@router.get("/popular-categories")
async def get_popular_categories(
    env: Annotated[Environment, Depends(odoo_env)],
    limit: int = Query(6, ge=1, le=15)
):
    """Get popular/trending categories"""
    try:
        # Get categories with most products
        categories = env['product.category'].search([])
        category_data = []
        
        for category in categories:
            product_count = env['product.product'].search_count([
                ('categ_id', 'child_of', category.id),
                ('sale_ok', '=', True),
                ('active', '=', True)
            ])
            
            if product_count > 0:
                category_data.append({
                    'category': category,
                    'product_count': product_count
                })
        
        # Sort by product count and take top categories
        category_data.sort(key=lambda x: x['product_count'], reverse=True)
        top_categories = category_data[:limit]
        
        result = []
        for item in top_categories:
            category = item['category']
            result.append({
                'id': category.id,
                'name': category.name,
                'product_count': item['product_count'],
                'image_url': f'/web/image/product.category/{category.id}/image' if hasattr(category, 'image') else None,
                'complete_name': category.complete_name
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching popular categories: {e}")
        return []


@router.get("/hit-products")
async def get_hit_products(
    env: Annotated[Environment, Depends(odoo_env)],
    current_user: Annotated[Partner, Depends(get_optional_user)] = None,
    limit: int = Query(10, ge=1, le=50)
):
    """Get hit/bestselling products"""
    try:
        # Get products ordered by mobile view count
        products = env['product.product'].search([
            ('sale_ok', '=', True),
            ('active', '=', True)
        ], limit=limit, order='mobile_view_count desc')
        
        result = []
        for product in products:
            in_wishlist = False
            if current_user:
                in_wishlist = env['mobile.wishlist'].is_in_wishlist(current_user.id, product.id)
            
            result.append({
                'id': product.id,
                'name': product.name,
                'list_price': product.list_price,
                'currency': product.currency_id.name,
                'image_url': f'/web/image/product.product/{product.id}/image_1920' if product.image_1920 else None,
                'in_stock': product.qty_available > 0,
                'category': product.categ_id.name,
                'brand': product.product_brand_id.name if hasattr(product, 'product_brand_id') and product.product_brand_id else None,
                'rating': product.rating_avg if hasattr(product, 'rating_avg') else 0,
                'in_wishlist': in_wishlist,
                'view_count': product.mobile_view_count or 0
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error fetching hit products: {e}")
        return []
