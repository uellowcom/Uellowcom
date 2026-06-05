# -*- coding: utf-8 -*-
"""Affiliate PANEL — a standalone console at /affiliate/panel (own
layout + sidebar, NOT the website theme). Session-auth JSON endpoints
feed the page; /my/affiliate now redirects here."""
from datetime import datetime

from odoo import http, fields as ofields
from odoo.http import request


def _aff():
    partner = request.env.user.partner_id
    Aff = request.env['uellow.affiliate'].sudo()
    return Aff.search([('partner_id', '=', partner.id)], limit=1) \
        or Aff.search([('partner_id', '=',
                        partner.commercial_partner_id.id)], limit=1)


def _base_url():
    base = request.env['ir.config_parameter'].sudo().get_param(
        'web.base.url', 'https://uellow.com').rstrip('/')
    try:
        w = request.website
        if w and w.domain:
            d = w.domain.rstrip('/')
            base = d if d.startswith('http') else 'https://' + d
    except Exception:
        pass
    return base


class AffiliatePanel(http.Controller):

    @http.route('/affiliate/panel', type='http', auth='user',
                website=True)
    def panel(self, **kw):
        aff = _aff()
        if not aff:
            return request.redirect('/partners#apply')
        # static shell (data flows through the auth'd JSON endpoints) —
        # served from a file so the inline JS has no XML constraints.
        import os
        path = os.path.join(os.path.dirname(__file__), '..',
                            'static', 'panel', 'index.html')
        with open(path, 'r', encoding='utf-8') as f:
            html = f.read()
        return request.make_response(html, headers=[
            ('Content-Type', 'text/html; charset=utf-8'),
            ('Cache-Control', 'no-cache'),
        ])

    # one-shot dashboard payload
    @http.route('/affiliate/panel/data', type='json', auth='user',
                csrf=False)
    def data(self, **kw):
        aff = _aff()
        if not aff:
            return {'error': 'no_affiliate'}
        from ..models.affiliate import tier_rules
        rules = tier_rules(request.env)
        base = _base_url()
        month_start = datetime.utcnow().replace(
            day=1, hour=0, minute=0, second=0)
        month_comm = sum(c.amount for c in aff.commission_ids
                         if c.state in ('confirmed', 'paid')
                         and c.create_date
                         and c.create_date >= month_start)
        order = ['bronze', 'silver', 'gold', 'platinum']
        nxt = None
        idx = order.index(aff.tier)
        if idx < len(order) - 1:
            need = rules[order[idx + 1]][1]
            sales30 = sum(
                c.base_amount for c in aff.commission_ids
                if c.state in ('confirmed', 'paid'))
            nxt = {'tier': order[idx + 1], 'needed': need,
                   'progress': min(1.0, (month_comm and sales30 or 0)
                                   / need) if need else 1.0}
        clicks = request.env['uellow.affiliate.click'].series_for(aff)
        return {
            'status': aff.state,
            'name': aff.name,
            'code': aff.code,
            'tier': aff.tier,
            'tier_mult': rules.get(aff.tier, (1.0, 0))[0],
            'link': '%s/aff/%s' % (base, aff.code),
            'pending': round(aff.pending_amount, 3),
            'available': round(aff.available_amount, 3),
            'paid': round(aff.paid_amount, 3),
            'month': round(month_comm, 3),
            'total_sales': round(aff.total_sales, 3),
            'clicks_total': aff.click_count,
            'orders_count': aff.order_count,
            'next_tier': nxt,
            'min_payout': float(
                request.env['ir.config_parameter'].sudo().get_param(
                    'uellow_affiliate.min_payout', '5') or 5),
            'payout_method': aff.payout_method or 'wallet',
            'payout_details': aff.payout_details or '',
            'clicks_series': clicks,
            'earnings_series': aff.earnings_series(),
            'activity': aff.activity_feed(12),
            'campaigns': [c.to_public_dict() for c in
                          request.env['uellow.affiliate.campaign']
                          .active_now()],
            'news': [n.to_public_dict() for n in
                     request.env['uellow.affiliate.news'].sudo()
                     .search([('active', '=', True)], limit=10)],
        }

    @http.route('/affiliate/panel/products', type='json', auth='user',
                csrf=False)
    def products(self, q='', **kw):
        aff = _aff()
        if not aff or aff.state != 'active':
            return {'products': []}
        base = _base_url()
        dom = aff.allowed_product_domain()
        if q:
            dom += [('name', 'ilike', q)]
        recs = request.env['product.template'].sudo().search(
            dom, order='create_date desc', limit=60)
        out = []
        for t in recs:
            pct = aff.commission_pct_for(t)
            link = '%s/aff/%s/p/%d' % (base, aff.code, t.id)
            out.append({
                'id': t.id, 'name': t.display_name,
                'image': '/web/image/product.template/%d/image_128'
                         % t.id,
                'price': round(t.list_price or 0, 3),
                'pct': round(pct, 2),
                'commission': round((t.list_price or 0) * pct / 100, 3),
                'link': link,
            })
        return {'products': out}

    @http.route('/affiliate/panel/sales', type='json', auth='user',
                csrf=False)
    def sales(self, **kw):
        aff = _aff()
        if not aff:
            return {'sales': []}
        out = []
        for c in aff.commission_ids[:80]:
            so = c.sale_order_id
            out.append({
                'order': so.name if so else '—',
                'date': c.create_date.strftime('%Y-%m-%d')
                        if c.create_date else '',
                'base': round(c.base_amount, 3),
                'commission': round(c.amount, 3),
                'source': c.source,
                'state': c.state,
            })
        return {'sales': out}

    @http.route('/affiliate/panel/orders', type='json', auth='user',
                csrf=False)
    def orders(self, **kw):
        aff = _aff()
        if not aff:
            return {'orders': []}
        return {'orders': [{
            'name': o.name,
            'date': o.create_date.strftime('%Y-%m-%d')
                    if o.create_date else '',
            'customer': o.customer_name,
            'phone': o.customer_phone,
            'total': round(o.amount_total, 3),
            'commission': round(o.est_commission, 3),
            'state': o.state,
        } for o in aff.submitted_order_ids[:60]]}

    @http.route('/affiliate/panel/order/create', type='json',
                auth='user', csrf=False)
    def order_create(self, customer_name='', customer_phone='',
                     customer_area='', customer_address='',
                     customer_note='', lines=None, **kw):
        aff = _aff()
        if not aff or aff.state != 'active':
            return {'error': 'inactive'}
        if not customer_name or not customer_phone or not lines:
            return {'error': 'missing'}
        Tmpl = request.env['product.template'].sudo()
        allowed = set(Tmpl.search(aff.allowed_product_domain()).ids)
        vals = []
        for l in lines:
            tid = int(l.get('product_id') or 0)
            if tid not in allowed:
                return {'error': 'not_allowed'}
            t = Tmpl.browse(tid)
            vals.append((0, 0, {
                'product_id': t.product_variant_id.id,
                'qty': float(l.get('qty') or 1),
                'price_unit': t.list_price,
                'commission_pct': aff.commission_pct_for(t),
            }))
        order = request.env['uellow.affiliate.order'].sudo().create({
            'affiliate_id': aff.id,
            'customer_name': customer_name.strip(),
            'customer_phone': customer_phone.strip(),
            'customer_area': (customer_area or '').strip(),
            'customer_address': (customer_address or '').strip(),
            'customer_note': (customer_note or '').strip(),
            'line_ids': vals,
        })
        order.action_submit()
        return {'ok': True, 'name': order.name}

    @http.route('/affiliate/panel/payouts', type='json', auth='user',
                csrf=False)
    def payouts(self, **kw):
        aff = _aff()
        if not aff:
            return {'payouts': []}
        return {'payouts': [{
            'name': p.name,
            'date': p.create_date.strftime('%Y-%m-%d')
                    if p.create_date else '',
            'amount': round(p.amount, 3),
            'method': p.method, 'state': p.state,
        } for p in aff.payout_ids[:40]]}

    @http.route('/affiliate/panel/payout/create', type='json',
                auth='user', csrf=False)
    def payout_create(self, amount=0, method='wallet', details='', **kw):
        aff = _aff()
        if not aff or aff.state != 'active':
            return {'error': 'inactive'}
        try:
            amount = float(amount or 0)
        except Exception:
            amount = 0
        min_payout = float(
            request.env['ir.config_parameter'].sudo().get_param(
                'uellow_affiliate.min_payout', '5') or 5)
        if amount < min_payout:
            return {'error': 'min', 'min': min_payout}
        if amount > aff.available_amount + 0.0001:
            return {'error': 'insufficient'}
        p = request.env['uellow.affiliate.payout'].sudo().create({
            'affiliate_id': aff.id, 'amount': amount,
            'method': (method or 'wallet').strip(),
            'details': (details or '').strip(),
        })
        return {'ok': True, 'name': p.name}

    @http.route('/affiliate/panel/settings/save', type='json',
                auth='user', csrf=False)
    def settings_save(self, payout_method='wallet', payout_details='',
                      **kw):
        aff = _aff()
        if not aff:
            return {'error': 'no_affiliate'}
        aff.sudo().write({
            'payout_method': payout_method or 'wallet',
            'payout_details': (payout_details or '').strip(),
        })
        return {'ok': True}


class AffiliatePortalRedirect(http.Controller):
    @http.route('/my/affiliate/panel-go', type='http', auth='user',
                website=True)
    def go(self, **kw):
        return request.redirect('/affiliate/panel')
