# -*- coding: utf-8 -*-
"""Website PORTAL for affiliates: a card on /my + /my/affiliate
dashboard (stats, link, catalog w/ commissions, orders, ledger,
payout request)."""
from datetime import datetime

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


def _portal_affiliate():
    partner = request.env.user.partner_id
    Aff = request.env['uellow.affiliate'].sudo()
    return Aff.search([('partner_id', '=', partner.id)], limit=1) \
        or Aff.search([('partner_id', '=',
                        partner.commercial_partner_id.id)], limit=1)


class AffiliatePortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'affiliate_count' in counters:
            aff = _portal_affiliate()
            values['affiliate_count'] = 1 if aff else 0
        return values

    @http.route('/my/affiliate', type='http', auth='user', website=True)
    def my_affiliate(self, **kw):
        # v2 — the rich standalone console replaced the inline portal page.
        aff = _portal_affiliate()
        if aff:
            return request.redirect('/affiliate/panel')
        values = self._prepare_portal_layout_values()
        if not aff:
            values['aff'] = None
            return request.render(
                'uellow_affiliate.portal_affiliate_join', values)
        from ..models.affiliate import tier_rules
        rules = tier_rules(request.env)
        month_start = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0)
        month_comm = sum(c.amount for c in aff.commission_ids
                         if c.state in ('confirmed', 'paid')
                         and c.create_date
                         and c.create_date >= month_start)
        base = request.env['ir.config_parameter'].sudo().get_param(
            'web.base.url', '').rstrip('/')
        try:
            w = request.website
            if w and w.domain:
                d = w.domain.rstrip('/')
                base = d if d.startswith('http') else 'https://' + d
        except Exception:
            pass
        # top products with commissions
        Tmpl = request.env['product.template'].sudo()
        prods = Tmpl.search(aff.allowed_product_domain(),
                            order='create_date desc', limit=30)
        prod_rows = [{
            'rec': t,
            'pct': aff.commission_pct_for(t),
            'comm': (t.list_price or 0) * aff.commission_pct_for(t) / 100.0,
            'link': '%s/aff/%s/p/%d' % (base, aff.code, t.id),
        } for t in prods]
        min_payout = float(request.env['ir.config_parameter'].sudo()
                           .get_param('uellow_affiliate.min_payout', '5')
                           or 5)
        values.update({
            'aff': aff,
            'page_name': 'affiliate',
            'tier_mult': rules.get(aff.tier, (1.0, 0))[0],
            'month_comm': month_comm,
            'ref_link': '%s/aff/%s' % (base, aff.code),
            'prod_rows': prod_rows,
            'min_payout': min_payout,
            'payout_msg': kw.get('payout_msg', ''),
        })
        return request.render(
            'uellow_affiliate.portal_affiliate_dashboard', values)

    @http.route('/my/affiliate/apply', type='http', auth='user',
                website=True, methods=['POST'], csrf=True)
    def my_affiliate_apply(self, **kw):
        partner = request.env.user.partner_id
        if not _portal_affiliate():
            request.env['uellow.affiliate'].sudo().create({
                'name': partner.name,
                'partner_id': partner.id,
                'phone': partner.phone or '',
                'email': partner.email or '',
            })
        return request.redirect('/my/affiliate')

    @http.route('/my/affiliate/payout', type='http', auth='user',
                website=True, methods=['POST'], csrf=True)
    def my_affiliate_payout(self, **kw):
        aff = _portal_affiliate()
        if not aff or aff.state != 'active':
            return request.redirect('/my/affiliate')
        try:
            amount = float(kw.get('amount') or 0)
        except Exception:
            amount = 0
        method = (kw.get('method') or 'wallet').strip()
        min_payout = float(request.env['ir.config_parameter'].sudo()
                           .get_param('uellow_affiliate.min_payout', '5')
                           or 5)
        if amount < min_payout or amount > aff.available_amount + 0.0001:
            return request.redirect(
                '/my/affiliate?payout_msg=invalid')
        request.env['uellow.affiliate.payout'].sudo().create({
            'affiliate_id': aff.id,
            'amount': amount,
            'method': method,
            'details': (kw.get('details') or '').strip(),
        })
        return request.redirect('/my/affiliate?payout_msg=ok')
