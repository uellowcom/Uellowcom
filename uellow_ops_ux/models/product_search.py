# -*- coding: utf-8 -*-
"""Hide dropship (Uellow World) products from every backend product picker.

The action-domain filter only covers list views; the Many2one product picker
(Purchase / Sale / Inventory lines, filters, reports) uses ``name_search`` (the
public method the web client / web_name_search route through), which ignored it.
This excludes ``is_dropship`` products from ``name_search`` everywhere, EXCEPT
when the caller opts in via ``context['include_dropship']``. The World website +
app load their catalogue through the storefront/API domains (``_search`` /
``search_read``), NOT ``name_search``, so they are unaffected.
"""
from odoo import api, models
from odoo.osv import expression


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = list(args or [])
        if 'is_dropship' in self._fields \
                and not self.env.context.get('include_dropship'):
            args = expression.AND([[('is_dropship', '=', False)], args])
        return super().name_search(name=name, args=args, operator=operator, limit=limit)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = list(args or [])
        if 'is_dropship' in self._fields \
                and not self.env.context.get('include_dropship'):
            args = expression.AND([[('is_dropship', '=', False)], args])
        return super().name_search(name=name, args=args, operator=operator, limit=limit)
