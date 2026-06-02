# -*- coding: utf-8 -*-
"""Add an image to product.brand so the mobile app can render brand
logos in the brand block / brand store header."""
from odoo import api, fields, models


class ProductBrandImage(models.Model):
    _inherit = 'product.brand'

    image_1024 = fields.Image('Logo', max_width=1024, max_height=1024)
    image_512 = fields.Image('Logo 512', related='image_1024',
                             max_width=512, max_height=512, store=True)
    image_128 = fields.Image('Logo 128', related='image_1024',
                             max_width=128, max_height=128, store=True)
