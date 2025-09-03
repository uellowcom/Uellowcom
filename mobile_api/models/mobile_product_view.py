# -*- coding: utf-8 -*-

from odoo import models, fields, api


class MobileProductView(models.Model):
    _name = 'mobile.product.view'
    _description = 'Mobile Product View History'
    _rec_name = 'product_id'
    _order = 'create_date desc'

    partner_id = fields.Many2one('res.partner', string='User', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    
    _sql_constraints = [
        ('unique_view_log', 'unique(partner_id, product_id, create_date)', 'Duplicate view entries are not allowed!')
    ]

    @api.model
    def log_product_view(self, partner_id, product_id):
        """Log a product view for analytics"""
        return self.create({
            'partner_id': partner_id,
            'product_id': product_id
        })
