# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MobileWishlist(models.Model):
    _name = 'mobile.wishlist'
    _description = 'Mobile Wishlist'
    _order = 'create_date desc'

    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product', string='Product', required=True, ondelete='cascade'
    )

    _sql_constraints = [
        ('unique_wishlist_item', 'unique(partner_id, product_id)', 'Product already in wishlist.'),
    ]

    @api.model
    def add_to_wishlist(self, partner_id, product_id):
        """Add product to wishlist"""
        product = self.env['product.product'].browse(product_id)
        if not product.exists():
            raise ValidationError(_('Product not found'))
        existing = self.search([
            ('partner_id', '=', partner_id),
            ('product_id', '=', product_id)
        ])
        if existing:
            return existing
        return self.create({'partner_id': partner_id, 'product_id': product_id})

    @api.model
    def remove_from_wishlist(self, partner_id, product_id):
        """Remove product from wishlist"""
        item = self.search([('partner_id', '=', partner_id), ('product_id', '=', product_id)])
        if item:
            item.unlink()
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
                'added_date': item.create_date.isoformat() if item.create_date else None,
                'in_stock': product.qty_available > 0,
                'website_url': f'/shop/product/{product.id}',
            })
        return result
