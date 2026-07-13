# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    warranty_policy_id = fields.Many2one(
        'uellow.warranty.policy', string='Warranty policy',
        help='Override the warranty for this product. '
             'Leave empty to fall back to the category / default policy.')
    warranty_months_display = fields.Integer(
        related='warranty_policy_id.duration_months', string='Warranty (months)')

    def _uellow_get_warranty_policy(self, website=None):
        """Resolve the active warranty policy for this product (website-aware).
        Used by the storefront product page and APIs."""
        self.ensure_one()
        if self.env['ir.config_parameter'].sudo().get_param(
                'uellow_warranty.enabled', 'True') not in ('True', 'true', '1'):
            return self.env['uellow.warranty.policy']
        variant = self.product_variant_id
        if not variant:
            return self.env['uellow.warranty.policy']
        if website is None:
            try:
                website = self.env['website'].get_current_website()
            except Exception:
                website = None
        return self.env['uellow.warranty.policy'].sudo()._get_for_product(variant, website=website)
