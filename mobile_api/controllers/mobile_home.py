# -*- coding: utf-8 -*-
"""Mobile Home Controller using Odoo HTTP"""

import json
import logging
from datetime import datetime, timedelta

from odoo import http, fields
from odoo.http import request

from ..services.jwt_service import JWTService

_logger = logging.getLogger(__name__)


class MobileHomeController(http.Controller):
    """Mobile Home HTTP Controller"""

    def _get_current_user(self):
        """Get current authenticated user from JWT token"""
        try:
            auth_header = request.httprequest.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                return None

            token = auth_header.split(' ')[1]
            jwt_service = JWTService()
            payload = jwt_service.decode_token(token)
            partner_id = payload.get('sub')
            
            if partner_id:
                partner = request.env['res.partner'].sudo().browse(int(partner_id))
                return partner if partner.exists() else None
            return None
        except:
            return None

    def _create_response(self, data=None, error=None, status=200):
        """Create standardized JSON response"""
        if error:
            response_data = {
                'success': False,
                'error': error,
                'data': None
            }
            status = status or 400
        else:
            response_data = {
                'success': True,
                'error': None,
                'data': data or {}
            }
        
        return request.make_response(
            json.dumps(response_data),
            headers={'Content-Type': 'application/json'},
            status=status
        )

    def _format_product_summary(self, product):
        """Format product for home page display"""
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        image_url = f"{base_url}/web/image/product.product/{product.id}/image_1920" if product.image_1920 else None
        
        return {
            'id': product.id,
            'name': product.name,
            'list_price': product.list_price,
            'currency': product.currency_id.name,
            'image_url': image_url,
            'category': product.categ_id.name if product.categ_id else ''
        }

    @http.route('/mobile/v1/home', auth='public', methods=['GET'], type='http', csrf=False)
    def get_home_data(self):
        """Get home page data including banners, featured products, categories"""
        try:
            current_user = self._get_current_user()

            # Get featured products (top selling or marked as featured)
            featured_products = request.env['product.product'].sudo().search([
                ('sale_ok', '=', True),
                ('active', '=', True)
            ], limit=8, order='create_date desc')

            # Get categories with products
            categories = request.env['product.category'].sudo().search([])
            categories_data = []
            for category in categories[:6]:  # Limit to 6 categories
                product_count = request.env['product.product'].sudo().search_count([
                    ('categ_id', '=', category.id),
                    ('sale_ok', '=', True),
                    ('active', '=', True)
                ])
                if product_count > 0:
                    categories_data.append({
                        'id': category.id,
                        'name': category.name,
                        'product_count': product_count
                    })

            # Get recently viewed products for authenticated users
            recently_viewed = []
            if current_user:
                recent_views = request.env['mobile.product.view'].sudo().search([
                    ('partner_id', '=', current_user.id)
                ], limit=6, order='viewed_at desc')
                
                for view in recent_views:
                    if view.product_id.active and view.product_id.sale_ok:
                        recently_viewed.append(self._format_product_summary(view.product_id))

            # Get new arrivals (products created in last 30 days)
            thirty_days_ago = fields.Datetime.now() - timedelta(days=30)
            new_arrivals = request.env['product.product'].sudo().search([
                ('sale_ok', '=', True),
                ('active', '=', True),
                ('create_date', '>=', thirty_days_ago)
            ], limit=8, order='create_date desc')

            # Get best sellers (placeholder logic - you can implement proper sales tracking)
            best_sellers = request.env['product.product'].sudo().search([
                ('sale_ok', '=', True),
                ('active', '=', True)
            ], limit=8, order='list_price desc')

            # Get promotional banners (you can create a custom model for this)
            banners = [
                {
                    'id': 1,
                    'title': 'Summer Sale',
                    'subtitle': 'Up to 50% off',
                    'image_url': None,
                    'action_type': 'category',
                    'action_value': '1'
                }
            ]

            response_data = {
                'banners': banners,
                'featured_products': [self._format_product_summary(p) for p in featured_products],
                'categories': categories_data,
                'recently_viewed': recently_viewed,
                'new_arrivals': [self._format_product_summary(p) for p in new_arrivals],
                'best_sellers': [self._format_product_summary(p) for p in best_sellers],
                'user_info': {
                    'is_authenticated': bool(current_user),
                    'name': current_user.name if current_user else None,
                    'wishlist_count': len(current_user.mobile_wishlist_ids) if current_user else 0
                }
            }

            return self._create_response(response_data)

        except Exception as e:
            _logger.error(f"Get home data error: {str(e)}")
            return self._create_response(error="Failed to fetch home data", status=500)

    @http.route('/mobile/v1/home/search/trending', auth='public', methods=['GET'], type='http', csrf=False)
    def get_trending_searches(self):
        """Get trending search terms"""
        try:
            # Placeholder implementation - you can track actual search terms
            trending_searches = [
                'smartphone',
                'laptop',
                'headphones',
                'camera',
                'watch'
            ]

            return self._create_response({'trending_searches': trending_searches})

        except Exception as e:
            _logger.error(f"Get trending searches error: {str(e)}")
            return self._create_response(error="Failed to fetch trending searches", status=500)

    @http.route('/mobile/v1/home/recommendations', auth='public', methods=['GET'], type='http', csrf=False)
    def get_recommendations(self):
        """Get personalized product recommendations"""
        try:
            current_user = self._get_current_user()
            
            if not current_user:
                # For anonymous users, return popular products
                products = request.env['product.product'].sudo().search([
                    ('sale_ok', '=', True),
                    ('active', '=', True)
                ], limit=12, order='list_price desc')
            else:
                # For authenticated users, get recommendations based on wishlist and views
                viewed_categories = []
                wishlist_categories = []
                
                # Get categories from recently viewed products
                recent_views = request.env['mobile.product.view'].sudo().search([
                    ('partner_id', '=', current_user.id)
                ], limit=10, order='viewed_at desc')
                
                for view in recent_views:
                    if view.product_id.categ_id:
                        viewed_categories.append(view.product_id.categ_id.id)

                # Get categories from wishlist
                for wishlist_item in current_user.mobile_wishlist_ids:
                    if wishlist_item.product_id.categ_id:
                        wishlist_categories.append(wishlist_item.product_id.categ_id.id)

                # Combine and deduplicate categories
                interested_categories = list(set(viewed_categories + wishlist_categories))
                
                if interested_categories:
                    # Get products from interested categories
                    products = request.env['product.product'].sudo().search([
                        ('sale_ok', '=', True),
                        ('active', '=', True),
                        ('categ_id', 'in', interested_categories)
                    ], limit=12, order='create_date desc')
                else:
                    # Fallback to popular products
                    products = request.env['product.product'].sudo().search([
                        ('sale_ok', '=', True),
                        ('active', '=', True)
                    ], limit=12, order='list_price desc')

            recommendations = [self._format_product_summary(p) for p in products]
            
            return self._create_response({'recommendations': recommendations})

        except Exception as e:
            _logger.error(f"Get recommendations error: {str(e)}")
            return self._create_response(error="Failed to fetch recommendations", status=500)

    @http.route('/mobile/v1/home/deals', auth='public', methods=['GET'], type='http', csrf=False)
    def get_deals(self):
        """Get current deals and offers"""
        try:
            # Get products with discounts (if you have a discount/sale price field)
            # For now, we'll return products ordered by price (placeholder)
            deals = request.env['product.product'].sudo().search([
                ('sale_ok', '=', True),
                ('active', '=', True),
                ('list_price', '>', 0)
            ], limit=10, order='list_price')

            deals_data = []
            for product in deals:
                product_data = self._format_product_summary(product)
                # Add deal information (placeholder)
                product_data['discount_percentage'] = 20  # Placeholder
                product_data['original_price'] = product.list_price * 1.25  # Placeholder
                deals_data.append(product_data)

            return self._create_response({'deals': deals_data})

        except Exception as e:
            _logger.error(f"Get deals error: {str(e)}")
            return self._create_response(error="Failed to fetch deals", status=500)
