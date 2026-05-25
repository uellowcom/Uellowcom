# -*- coding: utf-8 -*-

from odoo import models, fields, api


class MobileProductView(models.Model):
    _name = 'mobile.product.view'
    _description = 'Mobile Product View History'
    _rec_name = 'product_id'
    _order = 'create_date desc'

    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product', string='Product', required=True, ondelete='cascade'
    )

    @api.model
    def get_recent_viewed(self, partner_id, limit=10):
        """Get recently viewed products"""
        views = self.search(
            [('partner_id', '=', partner_id)],
            limit=limit, order='create_date desc'
        )
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
                    'viewed_date': view.create_date.isoformat() if view.create_date else None,
                    'in_stock': product.qty_available > 0,
                })
                seen_products.add(product.id)
        return result


class ProductProductMobile(models.Model):
    _inherit = 'product.product'

    mobile_wishlist_count = fields.Integer(
        'Wishlist Count', compute='_compute_mobile_wishlist_count'
    )
    mobile_view_count = fields.Integer('Mobile View Count', default=0)
    mobile_last_viewed = fields.Datetime('Last Viewed on Mobile')

    def _compute_mobile_wishlist_count(self):
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
            self.env['mobile.product.view'].create({
                'partner_id': partner_id,
                'product_id': self.id,
            })
