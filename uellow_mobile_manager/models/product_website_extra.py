# -*- coding: utf-8 -*-
"""
Multi-website product publishing.
=================================
Odoo's native product.template.website_id is a SINGLE website (empty = ALL
sites). That made it impossible to publish a product on, say, BOTH the Egypt
web store and the Egypt mobile-app website while hiding it from Kuwait.

This adds `uellow_extra_website_ids` (M2M): besides the primary `website_id`,
the product is ALSO shown on every website listed here. The mobile API's
published-domain ORs this field in, so a product is visible on website W when:
    website_id is empty  OR  website_id == W  OR  W in uellow_extra_website_ids
"""
from odoo import fields, models


class ProductTemplateMultiWebsite(models.Model):
    _inherit = 'product.template'

    uellow_extra_website_ids = fields.Many2many(
        'website', 'product_tmpl_extra_website_rel', 'tmpl_id', 'website_id',
        string='Also show on websites',
        help='In addition to the primary Website above, this product is also '
             'shown on these websites (web + mobile app). Use it to publish a '
             'product to several country sites without exposing it everywhere. '
             'Leave the primary Website set to the main site for this product.')
