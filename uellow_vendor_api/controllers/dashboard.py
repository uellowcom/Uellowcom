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

        # ── Expanded KPIs ───────────────────────────────────────────
        month_orders = confirmed.filtered(
            lambda o: (o.date_order or o.create_date) and (o.date_order or o.create_date) >= month_start)
        month_gmv = sum(month_orders.mapped('amount_total'))
        month_count = len(month_orders)
        aov = (month_gmv / month_count) if month_count else 0.0
        units_month = sum(month_orders.mapped('order_line')
                          .filtered(lambda l: not l.display_type)
                          .mapped('product_uom_qty'))
        # repeat-customer rate (all-time confirmed)
        counts = {}
        for o in confirmed:
            counts[o.partner_id.id] = counts.get(o.partner_id.id, 0) + 1
        distinct = len(counts)
        repeat = sum(1 for c in counts.values() if c > 1)
        repeat_pct = round(repeat / distinct * 100, 1) if distinct else 0.0
        try:
            open_returns = request.env['uellow.return.request'].sudo().search_count(
                [('vendor_id', '=', v.id), ('state', 'not in', ('settled', 'rejected'))])
        except Exception:
            open_returns = 0

        # Recent 5 orders
        recent = Order.search([('vendor_id', '=', v.id)],
                              order='id desc', limit=5)

        return ok({
            'kpis': {
                'aov':            fmt_price(aov, v.currency_id),
                'units_month':    int(units_month),
                'orders_month':   month_count,
                'repeat_pct':     repeat_pct,
                'distinct_customers': distinct,
                'open_returns':   open_returns,
                'low_stock':      low_stock,
            },
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
            'score':          int(v.uc_score or 0),
            'score_band':     v.uc_score_band or 'fair',
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
