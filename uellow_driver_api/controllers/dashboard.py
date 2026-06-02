# -*- coding: utf-8 -*-
"""Driver dashboard — /api/driver/v1/dashboard"""
from datetime import datetime, time

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, ok, require_auth, current_driver, fmt_price,
    short_addr, order_status_code, status_label,
)


class DriverDashboardAPI(http.Controller):

    @http.route('/api/driver/v1/dashboard', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def dashboard(self, **kw):
        driver = current_driver()
        today_start = datetime.combine(datetime.now().date(), time.min)
        Line = request.env['delivery.trip.line'].sudo()
        today_lines = Line.search([
            ('driver_id', '=', driver.id),
            ('create_date', '>=', today_start),
        ])
        done = today_lines.filtered(lambda l: l.delivery_status == 'delivered')
        pending = today_lines.filtered(
            lambda l: l.delivery_status in ('pending', 'received', 'in_transit'))
        failed = today_lines.filtered(lambda l: l.delivery_status == 'failed')

        total = max(1, len(done) + len(failed))
        success_rate = round(len(done) * 100 / total) if total else 0

        # Cash held = sum of COD orders delivered but not yet remitted
        cash_lines = Line.search([
            ('driver_id', '=', driver.id),
            ('delivery_status', '=', 'delivered'),
        ])
        # An order counts as "to-settle" if it hasn't been added to a
        # remittance yet OR its remittance is still draft.
        cash_held = 0.0
        for l in cash_lines:
            order = l.sale_order_id
            if not order:
                continue
            # Heuristic: if order has a remittance flag stored on it use that;
            # else fall back to amount_total.
            if hasattr(order, 'remittance_state') and order.remittance_state in ('settled', 'submitted'):
                continue
            cash_held += order.amount_total or 0

        next_three = []
        upcoming = pending.sorted(
            lambda l: (l.sequence or 999, l.id))[:3]
        for l in upcoming:
            o = l.sale_order_id
            if not o:
                continue
            code = order_status_code(l)
            next_three.append({
                'id': o.id,
                'name': o.name,
                'customer': o.partner_id.name,
                'addr_short': short_addr(o.partner_shipping_id or o.partner_id),
                'amount': fmt_price(o.amount_total, o.currency_id),
                'status': code,
                'status_label': status_label(code),
            })

        return ok({
            'kpis': {
                'done': len(done),
                'pending': len(pending),
                'failed': len(failed),
                'success_rate': success_rate,
            },
            'cash_held': fmt_price(cash_held),
            'status': driver.status or 'available',
            'driver_name': driver.name,
            'next': next_three,
            'has_active_trip': bool(request.env['delivery.trip'].sudo().search([
                ('carrier_company_id', '=', driver.carrier_company_id.id),
                ('state', '=', 'in_progress'),
            ], limit=1)),
        })
