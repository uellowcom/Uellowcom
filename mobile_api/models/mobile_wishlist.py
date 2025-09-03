# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MobileWishlist(models.Model):
    _name = 'mobile.wishlist'
    _description = 'Mobile Wishlist'
    _order = 'create_date desc'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    create_date = fields.Datetime('Added Date', default=fields.Datetime.now)

    _sql_constraints = [
        ('unique_wishlist_item', 'unique(partner_id, product_id)', 'Product already in wishlist.'),
    ]

    @api.model
    def add_to_wishlist(self, partner_id, product_id):
        """Add product to wishlist"""
        # Check if product exists
        product = self.env['product.product'].browse(product_id)
        if not product.exists():
            raise ValidationError(_('Product not found'))

        # Check if already in wishlist
        existing = self.search([
            ('partner_id', '=', partner_id),
            ('product_id', '=', product_id)
        ])
        if existing:
            return existing

        return self.create({
            'partner_id': partner_id,
            'product_id': product_id,
        })

    @api.model
    def remove_from_wishlist(self, partner_id, product_id):
        """Remove product from wishlist"""
        wishlist_item = self.search([
            ('partner_id', '=', partner_id),
            ('product_id', '=', product_id)
        ])
        if wishlist_item:
            wishlist_item.unlink()
        return True

    @api.model
    def is_in_wishlist(self, partner_id, product_id):
        """Check if product is in wishlist"""
        return bool(self.search([
            ('partner_id', '=', partner_id),
            ('product_id', '=', product_id)
        ], limit=1))

    @api.model
    def get_wishlist(self, partner_id, limit=None):
        """Get user's wishlist"""
        domain = [('partner_id', '=', partner_id)]
        wishlist_items = self.search(domain, limit=limit)
        
        result = []
        for item in wishlist_items:
            product = item.product_id
            result.append({
                'id': item.id,
                'product_id': product.id,
                'name': product.name,
                'list_price': product.list_price,
                'image_url': f'/web/image/product.product/{product.id}/image_1920' if product.image_1920 else None,
                'added_date': item.create_date.isoformat(),
                'in_stock': product.qty_available > 0,
                'website_url': f'/shop/product/{product.id}',
            })
        return result


class ProductProduct(models.Model):
    _inherit = 'product.product'

    mobile_wishlist_count = fields.Integer('Wishlist Count', compute='_compute_mobile_wishlist_count')
    mobile_view_count = fields.Integer('Mobile View Count', default=0)
    mobile_last_viewed = fields.Datetime('Last Viewed on Mobile')

    def _compute_mobile_wishlist_count(self):
        """Compute how many users have this product in wishlist"""
        for product in self:
            product.mobile_wishlist_count = self.env['mobile.wishlist'].search_count([
                ('product_id', '=', product.id)
            ])

    def track_mobile_view(self, partner_id=None):
        """Track product view from mobile"""
        self.ensure_one()
        self.mobile_view_count += 1
        self.mobile_last_viewed = fields.Datetime.now()
        
        if partner_id:
            # Create view history record
            self.env['mobile.product.view'].create({
                'partner_id': partner_id,
                'product_id': self.id,
            })

    @api.model
    def get_mobile_product_data(self, product_id, partner_id=None):
        """Get product data optimized for mobile"""
        product = self.browse(product_id)
        if not product.exists():
            return None

        # Track view
        product.track_mobile_view(partner_id)

        # Get product images
        images = []
        if product.image_1920:
            images.append(f'/web/image/product.product/{product.id}/image_1920')
        
        # Get variants if any
        variants = []
        if product.product_template_id.product_variant_count > 1:
            for variant in product.product_template_id.product_variant_ids:
                if variant.active:
                    variants.append({
                        'id': variant.id,
                        'name': variant.display_name,
                        'price': variant.list_price,
                        'attributes': variant.product_template_attribute_value_ids.mapped('name'),
                    })

        # Check if in wishlist
        in_wishlist = False
        if partner_id:
            in_wishlist = self.env['mobile.wishlist'].is_in_wishlist(partner_id, product.id)

        return {
            'id': product.id,
            'name': product.name,
            'description': product.description_sale or product.description,
            'list_price': product.list_price,
            'currency': product.currency_id.name,
            'images': images,
            'in_stock': product.qty_available > 0,
            'stock_quantity': product.qty_available,
            'sku': product.default_code,
            'barcode': product.barcode,
            'weight': product.weight,
            'category': product.categ_id.name,
            'brand': product.product_brand_id.name if hasattr(product, 'product_brand_id') else None,
            'rating': product.rating_avg if hasattr(product, 'rating_avg') else 0,
            'review_count': product.rating_count if hasattr(product, 'rating_count') else 0,
            'in_wishlist': in_wishlist,
            'variants': variants,
            'tags': product.tag_ids.mapped('name'),
            'website_url': f'/shop/product/{product.id}',
        }


class MobileProductView(models.Model):
    _name = 'mobile.product.view'
    _description = 'Mobile Product View History'
    _order = 'create_date desc'

    partner_id = fields.Many2one('res.partner', string='Customer', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade')
    create_date = fields.Datetime('Viewed Date', default=fields.Datetime.now)

    @api.model
    def get_recent_viewed(self, partner_id, limit=10):
        """Get recently viewed products"""
        views = self.search([
            ('partner_id', '=', partner_id)
        ], limit=limit, order='create_date desc')
        
        result = []
        seen_products = set()
        for view in views:
            if view.product_id.id not in seen_products:
                product = view.product_id
                result.append({
                    'product_id': product.id,
                    'name': product.name,
                    'list_price': product.list_price,
                    'image_url': f'/web/image/product.product/{product.id}/image_1920' if product.image_1920 else None,
                    'viewed_date': view.create_date.isoformat(),
                    'in_stock': product.qty_available > 0,
                })
                seen_products.add(product.id)
        
        return result
