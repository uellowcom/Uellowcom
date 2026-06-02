# -*- coding: utf-8 -*-
"""Vendor dashboard — /api/vendor/v1/dashboard"""
from datetime import datetime, time, timedelta

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, ok, require_auth, current_vendor, fmt_price,
)


class VendorDashboardAPI(http.Controller):

    @http.route('/api/vendor/v1/dashboard', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def dashboard(self, **kw):
        v = current_vendor()
        now = datetime.now()
        today = datetime.combine(now.date(), time.min)
        week_start = today - timedelta(days=now.weekday())
        month_start = today.replace(day=1)

        Order = request.env['sale.order'].sudo()
        confirmed = Order.search([
            ('vendor_id', '=', v.id),
            ('state', 'in', ('sale', 'done')),
        ])

        def rev_in(start):
            return sum(o.amount_total for o in confirmed
                        if (o.date_order or o.create_date) >= start)

        # Orders by status (using uellow_status or fallback)
        pending = Order.search_count([('vendor_id', '=', v.id),
            ('state', '=', 'draft')])
        new_count = Order.search_count([('vendor_id', '=', v.id),
            ('state', '=', 'sent')])
        confirmed_count = Order.search_count([('vendor_id', '=', v.id),
            ('state', 'in', ('sale', 'done')), ('invoice_status', '!=', 'invoiced')])
        completed_count = Order.search_count([('vendor_id', '=', v.id),
            ('state', 'in', ('sale', 'done')), ('invoice_status', '=', 'invoiced')])
        cancelled_count = Order.search_count([('vendor_id', '=', v.id),
            ('state', '=', 'cancel')])

        # Product stats
        Tmpl = request.env['product.template'].sudo()
        active_products = Tmpl.search_count([
            ('vendor_id', '=', v.id), ('is_published', '=', True),
            ('vendor_approval_state', '=', 'approved'),
        ])
        pending_approval = Tmpl.search_count([
            ('vendor_id', '=', v.id),
            ('vendor_approval_state', 'in', ('draft', 'pending')),
        ])
        # Low stock (qty <= 5 across variants)
        low_stock = 0
        try:
            for tmpl in Tmpl.search([('vendor_id', '=', v.id)], limit=500):
                if (tmpl.qty_available or 0) <= 5 and tmpl.qty_available is not None:
                    low_stock += 1
        except Exception:
            pass

        # Recent 5 orders
        recent = Order.search([('vendor_id', '=', v.id)],
                              order='id desc', limit=5)

        return ok({
            'revenue': {
                'today': fmt_price(rev_in(today), v.currency_id),
                'week':  fmt_price(rev_in(week_start), v.currency_id),
                'month': fmt_price(rev_in(month_start), v.currency_id),
                'total': fmt_price(v.total_sales or 0, v.currency_id),
            },
            'orders': {
                'pending':   pending,
                'new':       new_count,
                'confirmed': confirmed_count,
                'completed': completed_count,
                'cancelled': cancelled_count,
            },
            'products': {
                'active':           active_products,
                'pending_approval': pending_approval,
                'low_stock':        low_stock,
            },
            'wallet_balance': fmt_price(v.wallet_balance or 0, v.currency_id),
            'avg_rating':     round(float(v.avg_rating or 0), 2),
            'follower_count': int(v.follower_count or 0),
            'tier':           v.tier or 'bronze',
            'recent_orders': [{
                'id': o.id,
                'name': o.name,
                'customer': o.partner_id.name,
                'amount': fmt_price(o.amount_total, o.currency_id),
                'state': o.state,
                'when': (o.date_order or o.create_date).isoformat()
                        if (o.date_order or o.create_date) else '',
            } for o in recent],
        })
