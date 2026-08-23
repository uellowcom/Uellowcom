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
        """Re-derive the margin-protected لمّة يلو discount as a PER-LINE discount
        on the bundle lines, from the CURRENT cart (live price_unit + cost).

        Per-line (not an order-level coupon) is deliberate and is what makes the
        discount tamper-proof: removing a bundle line removes its discount with
        it, the total can never go negative, there is no coupon code to leak or
        replay, and it self-corrects on every cart change. The saved amount is
        spread across lines by MARGIN HEADROOM so no single line is ever pushed
        below its guaranteed floor margin."""
        cfg = self.env['uellow.lamma.config'].sudo().get_config()
        for order in self:
            lam = order.order_line.filtered(
                lambda l: l.is_lamma and not l.display_type and not l.is_reward_line)
            if not lam:
                continue
            groups = {}
            for l in lam:
                groups.setdefault(l.lamma_type or 'normal', self.env['sale.order.line'])
                groups[l.lamma_type or 'normal'] |= l
            for ltype, lines in groups.items():
                units = [{
                    'line': l,
                    'price': (l.price_unit or 0.0) * (l.product_uom_qty or 1.0),
                    'cost': (l.product_id.standard_price or 0.0) * (l.product_uom_qty or 1.0),
                } for l in lines]
                q = cfg.compute_lamma(
                    [{'price': u['price'], 'cost': u['cost']} for u in units], ltype)
                saved = float(q.get('saved') or 0.0)
                # headroom per line = how much it can be discounted while keeping
                # its own floor margin (mirrors the engine).
                fm = min(cfg.min_margin_pct
                         + (cfg.installment_extra_margin if ltype == 'installment' else 0.0),
                         99.0)

                def _floor_price(c):
                    return c / (1 - fm / 100.0) if fm < 100 else float('inf')

                heads = [max(0.0, u['price'] - _floor_price(u['cost'])) for u in units]
                total_h = sum(heads)
                for u, h in zip(units, heads):
                    base = u['price']
                    if saved <= 0 or total_h <= 0 or base <= 0 or h <= 0:
                        disc = 0.0
                    else:
                        share = saved * (h / total_h)
                        disc = min(100.0, share / base * 100.0)
                    if abs((u['line'].discount or 0.0) - disc) > 0.001:
                        u['line'].discount = disc

    def _cart_update(self, *args, **kwargs):
        res = super()._cart_update(*args, **kwargs)
        try:
            self._recompute_lamma()
        except Exception:
            pass
        return res
