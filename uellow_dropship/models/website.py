# -*- coding: utf-8 -*-
"""Website product-domain isolation.

The dropship website (Uellow World) must show ONLY dropship products, and the
main Uellow websites must NEVER show dropship products. Both are enforced in one
place — ``sale_product_domain`` — which every storefront product listing (shop,
categories, search, snippets) funnels through.
"""
from odoo import models
from odoo.osv import expression


class Website(models.Model):
    _inherit = 'website'

    def sale_product_domain(self):
        domain = super().sale_product_domain()
        ds_site = self.env['ir.config_parameter'].sudo().get_param('uellow_dropship.website_id')
        current = self.get_current_website()
        if ds_site and str(current.id) == ds_site:
            # Uellow World: dropship products only.
            return expression.AND([domain, [('is_dropship', '=', True)]])
        # Every other website: hide dropship products entirely.
        return expression.AND([domain, [('is_dropship', '=', False)]])
