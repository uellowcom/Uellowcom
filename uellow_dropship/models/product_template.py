# -*- coding: utf-8 -*-
"""Flag + link on product.template so dropship items stay isolated from the
live Uellow catalog and never touch stock."""
from odoo import fields, models


class ProductAttribute(models.Model):
    _inherit = 'product.attribute'

    # dropship-owned attributes (Color, Size, …) are kept SEPARATE from the main
    # store's attributes so provider option values (e.g. "5pcs", "Beige") never
    # pollute the curated store attribute lists, and so we always create them as
    # plain radio selectors (no empty color-swatches).
    is_dropship_attr = fields.Boolean(
        string="Dropship Attribute", index=True, copy=False)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_dropship = fields.Boolean(
        string="Dropship Product", index=True, copy=False,
        help="Sourced from a dropshipping provider; fulfilled on order, no stock.")
    dropship_product_id = fields.Many2one(
        'dropship.product', string="Source Listing", copy=False, index=True)
    dropship_provider_id = fields.Many2one(
        'dropship.provider', related='dropship_product_id.provider_id',
        store=True, string="Dropship Provider")
