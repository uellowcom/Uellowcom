# -*- coding: utf-8 -*-
from odoo import models, fields


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_lamma = fields.Boolean('Lamma line', default=False,
                              help='This line belongs to a لمّة يلو smart bundle.')
    lamma_type = fields.Char('Lamma type')  # 'normal' | 'installment'


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    has_lamma = fields.Boolean('Has Lamma', compute='_compute_has_lamma')

    def _compute_has_lamma(self):
        for o in self:
            o.has_lamma = any(o.order_line.mapped('is_lamma'))

    def _recompute_lamma(self):
        """Re-derive the margin-protected discount for the Lamma lines from the
        CURRENT cart (real price_unit + cost). Closes the 'add many for a high
        tier then remove some' gap — the discount always reflects what's actually
        in the bundle right now. Uses the live cart price, not list_price."""
        cfg = self.env['uellow.lamma.config'].sudo().get_config()
        for order in self:
            lam = order.order_line.filtered(lambda l: l.is_lamma and not l.display_type)
            if not lam:
                continue
            groups = {}
            for l in lam:
                groups.setdefault(l.lamma_type or 'normal', self.env['sale.order.line'])
                groups[l.lamma_type or 'normal'] |= l
            for ltype, lines in groups.items():
                eng = [{'price': (l.price_unit or 0.0) * (l.product_uom_qty or 1.0),
                        'cost': (l.product_id.standard_price or 0.0) * (l.product_uom_qty or 1.0)}
                       for l in lines]
                pct = cfg.compute_lamma(eng, ltype)['discount_pct']
                for l in lines:
                    if abs((l.discount or 0.0) - pct) > 0.001:
                        l.discount = pct

    def _cart_update(self, *args, **kwargs):
        res = super()._cart_update(*args, **kwargs)
        try:
            self._recompute_lamma()
        except Exception:
            pass
        return res
