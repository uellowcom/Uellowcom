# -*- coding: utf-8 -*-
"""Vendor analytics — /api/vendor/v1/analytics*"""
from datetime import datetime, timedelta

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, require_auth, current_vendor, fmt_price,
    bilingual, img_url,
)


class VendorAnalyticsAPI(http.Controller):

    @http.route('/api/vendor/v1/analytics/sales', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def sales_timeseries(self, **kw):
        """Last N days of sales (default 30). Returns daily revenue + orders."""
        v = current_vendor()
        p = get_payload()
        try:
            days = max(7, min(90, int(p.get('days') or 30)))
        except (TypeError, ValueError):
            days = 30
        Order = request.env['sale.order'].sudo()
        start = datetime.now().date() - timedelta(days=days - 1)
        rows = Order.search([
            ('vendor_id', '=', v.id),
            ('state', 'in', ('sale', 'done')),
            ('date_order', '>=', start),
        ])
        # Group by day
        buckets = {}
        for d in (start + timedelta(days=i) for i in range(days)):
            buckets[d.isoformat()] = {'revenue': 0.0, 'orders': 0}
        for o in rows:
            day = (o.date_order or o.create_date).date().isoformat()
            if day in buckets:
                buckets[day]['revenue'] += o.amount_total or 0
                buckets[day]['orders'] += 1
        return ok({
            'days': [{'date': k, **v} for k, v in buckets.items()],
            'total_revenue': sum(b['revenue'] for b in buckets.values()),
            'total_orders': sum(b['orders'] for b in buckets.values()),
        })

    @http.route('/api/vendor/v1/analytics/top-products', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def top_products(self, **kw):
        v = current_vendor()
        Order = request.env['sale.order'].sudo()
        confirmed = Order.search([('vendor_id', '=', v.id),
                                   ('state', 'in', ('sale', 'done'))], limit=2000)
        totals = {}  # tmpl_id -> {revenue, qty, name}
        for o in confirmed:
            for l in o.order_line.filtered(lambda l: not l.display_type):
                tmpl = l.product_id.product_tmpl_id
                if tmpl.vendor_id.id != v.id:
                    continue
                t = totals.setdefault(tmpl.id, {
                    'tmpl': tmpl, 'revenue': 0.0, 'qty': 0.0,
                })
                t['revenue'] += l.price_subtotal or 0
                t['qty'] += l.product_uom_qty or 0
        rows = sorted(totals.values(), key=lambda x: -x['revenue'])[:20]
        cur = v.currency_id or request.env.company.currency_id
        return ok([{
            'id': r['tmpl'].id,
            'name': bilingual(r['tmpl'], 'name'),
            'image_url': img_url('product.template', r['tmpl'].id,
                                 'image_256', unique=r['tmpl'].write_date)
                          if r['tmpl'].image_1920 else None,
            'revenue': fmt_price(r['revenue'], cur),
            'qty': r['qty'],
        } for r in rows])

    @http.route('/api/vendor/v1/analytics/top-customers', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def top_customers(self, **kw):
        v = current_vendor()
        Order = request.env['sale.order'].sudo()
        confirmed = Order.search([('vendor_id', '=', v.id),
                                   ('state', 'in', ('sale', 'done'))], limit=2000)
        totals = {}
        for o in confirmed:
            t = totals.setdefault(o.partner_id.id, {
                'partner': o.partner_id, 'spent': 0.0, 'orders': 0,
            })
            t['spent'] += o.amount_total or 0
            t['orders'] += 1
        rows = sorted(totals.values(), key=lambda x: -x['spent'])[:20]
        cur = v.currency_id or request.env.company.currency_id
        return ok([{
            'id': r['partner'].id,
            'name': r['partner'].name,
            'spent': fmt_price(r['spent'], cur),
            'orders': r['orders'],
            'avatar_url': img_url('res.partner', r['partner'].id,
                                  'image_128', unique=r['partner'].write_date)
                          if r['partner'].image_128 else None,
        } for r in rows])
