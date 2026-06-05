# -*- coding: utf-8 -*-
"""Referral attribution: sale orders carry the affiliate; commissions
book automatically for link-attributed orders on confirmation."""
from odoo import api, fields, models


class SaleOrderAffiliate(models.Model):
    _inherit = 'sale.order'

    uellow_affiliate_id = fields.Many2one(
        'uellow.affiliate', string='Affiliate', index=True,
        ondelete='set null',
        help='Agent whose referral link / submitted order produced this '
             'sale.')

    def action_confirm(self):
        res = super().action_confirm()
        for so in self:
            so._uellow_book_affiliate_commission()
        return res

    def _uellow_book_affiliate_commission(self):
        """Create the PENDING commission entry once per order (link
        attribution path — submitted orders book theirs at approval)."""
        self.ensure_one()
        aff = self.uellow_affiliate_id
        if not aff or aff.state != 'active':
            return
        Comm = self.env['uellow.affiliate.commission'].sudo()
        if Comm.search_count([('sale_order_id', '=', self.id)]):
            return
        base = 0.0
        commission = 0.0
        for l in self.order_line:
            if l.display_type or getattr(l, 'is_delivery', False) \
                    or getattr(l, 'is_reward_line', False):
                continue
            line_base = l.price_subtotal
            pct = aff.commission_pct_for(l.product_id.product_tmpl_id)
            base += line_base
            commission += line_base * (pct / 100.0)
        if commission <= 0:
            return
        Comm.create({
            'affiliate_id': aff.id,
            'sale_order_id': self.id,
            'source': 'link',
            'base_amount': base,
            'amount': commission,
        })

    @api.model_create_multi
    def create(self, vals_list):
        """WEBSITE parity: carts created during a web session carry the
        30-day `uellow_aff` referral cookie set by /aff/<code>."""
        orders = super().create(vals_list)
        try:
            from odoo.http import request as _req
            code = _req and _req.httprequest.cookies.get('uellow_aff')
            if code:
                for so in orders:
                    if so.website_id and not so.uellow_affiliate_id:
                        self.uellow_attach_affiliate_code(so, code)
        except Exception:
            pass
        return orders

    @api.model
    def uellow_attach_affiliate_code(self, order, code):
        """Best-effort: stamp an affiliate (by referral code) on a cart /
        order. Used by the mobile checkout when the customer arrived
        through a referral link."""
        if not order or not code:
            return False
        aff = self.env['uellow.affiliate'].sudo().search(
            [('code', '=', code.strip().upper()),
             ('state', '=', 'active')], limit=1)
        if not aff:
            return False
        # the agent must not earn commission on his own purchases
        if order.partner_id and aff.partner_id and \
                order.partner_id.commercial_partner_id.id == \
                aff.partner_id.commercial_partner_id.id:
            return False
        order.uellow_affiliate_id = aff.id
        return True
