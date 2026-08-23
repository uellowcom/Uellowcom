# -*- coding: utf-8 -*-
from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def write(self, vals):
        # SEO/UX guard — archiving a product MUST also unpublish it. Odoo does
        # not do this on its own, so archived-but-published products keep
        # serving 200 pages and stay indexed by Google (dead pages that hurt
        # SEO and drop users onto unavailable items). If the caller sets
        # is_published explicitly in the same write, respect their choice.
        if vals.get('active') is False and 'is_published' not in vals:
            vals = dict(vals, is_published=False)
        return super().write(vals)
