# -*- coding: utf-8 -*-
"""Mobile Product Controller using Odoo HTTP"""

import json
import logging
from datetime import datetime

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import ValidationError, AccessError

from ..services.jwt_service import JWTService

_logger = logging.getLogger(__name__)


class MobileProductController(http.Controller):
    """Mobile Product HTTP Controller"""

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

    def _format_product(self, product, partner=None):
        """Format product data for API response"""
        # Get product images
        images = []
        if product.image_1920:
            base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            images.append(f"{base_url}/web/image/product.product/{product.id}/image_1920")

        # Check if product is in wishlist
        in_wishlist = False
        if partner:
            wishlist = request.env['mobile.wishlist'].sudo().search([
                ('partner_id', '=', partner.id),
                ('product_id', '=', product.id)
            ], limit=1)
            in_wishlist = bool(wishlist)

        # Get stock quantity
        stock_quantity = product.with_context(location=product.env.user.company_id.id).qty_available

        return {
            'id': product.id,
            'name': product.name,
            'list_price': product.list_price,
            'currency': product.currency_id.name,
            'image_url': images[0] if images else None,
            'images': images,
            'in_stock': stock_quantity > 0,
            'stock_quantity': stock_quantity,
            'category': product.categ_id.name if product.categ_id else '',
            'brand': product.product_brand_id.name if hasattr(product, 'product_brand_id') and product.product_brand_id else None,
            'description': product.description_sale or product.description,
            'sku': product.default_code,
            'barcode': product.barcode,
            'weight': product.weight,
            'rating': 4.5,  # Placeholder - implement proper rating system
            'in_wishlist': in_wishlist
        }

    @http.route('/mobile/v1/products', auth='public', methods=['GET'], type='http', csrf=False)
    def get_products(self, **kwargs):
        """Get list of products with filtering and pagination"""
        try:
            # Extract query parameters
            limit = int(kwargs.get('limit', 20))
            offset = int(kwargs.get('offset', 0))
            category_id = kwargs.get('category_id')
            search = kwargs.get('search', '').strip()
            min_price = kwargs.get('min_price')
            max_price = kwargs.get('max_price')
            sort_by = kwargs.get('sort_by', 'name')  # name, price, rating
            
            # Get current user for wishlist
            current_user = self._get_current_user()

            # Build domain for product search
            domain = [
                ('sale_ok', '=', True),
                ('active', '=', True)
            ]

            # Add search filter
            if search:
                domain.append('|')
                domain.append(('name', 'ilike', search))
                domain.append(('description_sale', 'ilike', search))

            # Add category filter
            if category_id:
                domain.append(('categ_id', '=', int(category_id)))

            # Add price filters
            if min_price:
                domain.append(('list_price', '>=', float(min_price)))
            if max_price:
                domain.append(('list_price', '<=', float(max_price)))

            # Define sorting
            order = 'name'
            if sort_by == 'price':
                order = 'list_price'
            elif sort_by == 'rating':
                order = 'name'  # Placeholder until rating system implemented

            # Search products
            products = request.env['product.product'].sudo().search(
                domain, 
                limit=limit, 
                offset=offset, 
                order=order
            )

            # Format products for response
            products_data = []
            for product in products:
                products_data.append(self._format_product(product, current_user))

            # Get total count for pagination
            total_count = request.env['product.product'].sudo().search_count(domain)

            response_data = {
                'products': products_data,
                'pagination': {
                    'total': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total_count
                }
            }

            return self._create_response(response_data)

        except Exception as e:
            _logger.error(f"Get products error: {str(e)}")
            return self._create_response(error="Failed to fetch products", status=500)

    @http.route('/mobile/v1/products/<int:product_id>', auth='public', methods=['GET'], type='http', csrf=False)
    def get_product_detail(self, product_id):
        """Get detailed product information"""
        try:
            # Get current user for wishlist
            current_user = self._get_current_user()

            # Find product
            product = request.env['product.product'].sudo().browse(product_id)
            if not product.exists() or not product.active or not product.sale_ok:
                return self._create_response(error="Product not found", status=404)

            # Format product data
            product_data = self._format_product(product, current_user)

            # Add related products
            related_products = request.env['product.product'].sudo().search([
                ('categ_id', '=', product.categ_id.id),
                ('id', '!=', product.id),
                ('sale_ok', '=', True),
                ('active', '=', True)
            ], limit=4)

            product_data['related_products'] = [
                self._format_product(related, current_user) for related in related_products
            ]

            # Record product view
            if current_user:
                view_vals = {
                    'partner_id': current_user.id,
                    'product_id': product.id,
                    'viewed_at': fields.Datetime.now()
                }
                request.env['mobile.product.view'].sudo().create(view_vals)

            return self._create_response(product_data)

        except Exception as e:
            _logger.error(f"Get product detail error: {str(e)}")
            return self._create_response(error="Failed to fetch product details", status=500)

    @http.route('/mobile/v1/products/categories', auth='public', methods=['GET'], type='http', csrf=False)
    def get_categories(self):
        """Get product categories"""
        try:
            categories = request.env['product.category'].sudo().search([])
            
            categories_data = []
            for category in categories:
                categories_data.append({
                    'id': category.id,
                    'name': category.name,
                    'parent_id': category.parent_id.id if category.parent_id else None,
                    'product_count': request.env['product.product'].sudo().search_count([
                        ('categ_id', '=', category.id),
                        ('sale_ok', '=', True),
                        ('active', '=', True)
                    ])
                })

            return self._create_response({'categories': categories_data})

        except Exception as e:
            _logger.error(f"Get categories error: {str(e)}")
            return self._create_response(error="Failed to fetch categories", status=500)

    @http.route('/mobile/v1/products/search/suggestions', auth='public', methods=['GET'], type='http', csrf=False)
    def get_search_suggestions(self, **kwargs):
        """Get search suggestions based on query"""
        try:
            query = kwargs.get('q', '').strip()
            if not query or len(query) < 2:
                return self._create_response({'suggestions': []})

            # Search products for suggestions
            products = request.env['product.product'].sudo().search([
                ('name', 'ilike', query),
                ('sale_ok', '=', True),
                ('active', '=', True)
            ], limit=5)

            suggestions = []
            for product in products:
                suggestions.append({
                    'id': product.id,
                    'name': product.name,
                    'category': product.categ_id.name if product.categ_id else ''
                })

            return self._create_response({'suggestions': suggestions})

        except Exception as e:
            _logger.error(f"Get search suggestions error: {str(e)}")
            return self._create_response(error="Failed to fetch suggestions", status=500)

    @http.route('/mobile/v1/products/<int:product_id>/wishlist', auth='public', methods=['POST'], type='json', csrf=False)
    def toggle_wishlist(self, product_id):
        """Add or remove product from wishlist"""
        try:
            # Get current user
            current_user = self._get_current_user()
            if not current_user:
                return self._create_response(error="Authentication required", status=401)

            # Check if product exists
            product = request.env['product.product'].sudo().browse(product_id)
            if not product.exists():
                return self._create_response(error="Product not found", status=404)

            # Check if already in wishlist
            wishlist_item = request.env['mobile.wishlist'].sudo().search([
                ('partner_id', '=', current_user.id),
                ('product_id', '=', product_id)
            ], limit=1)

            if wishlist_item:
                # Remove from wishlist
                wishlist_item.unlink()
                message = "Product removed from wishlist"
                in_wishlist = False
            else:
                # Add to wishlist
                wishlist_vals = {
                    'partner_id': current_user.id,
                    'product_id': product_id,
                    'added_date': fields.Datetime.now()
                }
                request.env['mobile.wishlist'].sudo().create(wishlist_vals)
                message = "Product added to wishlist"
                in_wishlist = True

            return self._create_response({
                'message': message,
                'in_wishlist': in_wishlist
            })

        except Exception as e:
            _logger.error(f"Toggle wishlist error: {str(e)}")
            return self._create_response(error="Failed to update wishlist", status=500)

    @http.route('/mobile/v1/products/wishlist', auth='public', methods=['GET'], type='http', csrf=False)
    def get_wishlist(self, **kwargs):
        """Get user's wishlist"""
        try:
            # Get current user
            current_user = self._get_current_user()
            if not current_user:
                return self._create_response(error="Authentication required", status=401)

            # Extract pagination parameters
            limit = int(kwargs.get('limit', 20))
            offset = int(kwargs.get('offset', 0))

            # Get wishlist items
            wishlist_items = request.env['mobile.wishlist'].sudo().search([
                ('partner_id', '=', current_user.id)
            ], limit=limit, offset=offset, order='added_date desc')

            products_data = []
            for item in wishlist_items:
                product_data = self._format_product(item.product_id, current_user)
                product_data['added_date'] = item.added_date.isoformat() if item.added_date else None
                products_data.append(product_data)

            # Get total count
            total_count = request.env['mobile.wishlist'].sudo().search_count([
                ('partner_id', '=', current_user.id)
            ])

            response_data = {
                'products': products_data,
                'pagination': {
                    'total': total_count,
                    'limit': limit,
                    'offset': offset,
                    'has_more': offset + limit < total_count
                }
            }

            return self._create_response(response_data)

        except Exception as e:
            _logger.error(f"Get wishlist error: {str(e)}")
            return self._create_response(error="Failed to fetch wishlist", status=500)
