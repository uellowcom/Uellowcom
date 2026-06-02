# -*- coding: utf-8 -*-
"""Cash remittance — /api/driver/v1/cash*"""
from datetime import datetime

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth, current_driver,
    fmt_price, short_addr,
)


class DriverCashAPI(http.Controller):

    @http.route('/api/driver/v1/cash/ready', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def ready(self, **kw):
        """COD-delivered orders that are not yet in a submitted remittance."""
        driver = current_driver()
        Line = request.env['delivery.trip.line'].sudo()
        lines = Line.search([
            ('driver_id', '=', driver.id),
            ('delivery_status', '=', 'delivered'),
        ], order='delivery_date_actual desc')
        # An order is "ready to settle" if no remittance row exists for it
        # OR the remittance is still in draft.
        Rem = request.env['delivery.cash.remittance'].sudo()
        used_order_ids = set()
        for r in Rem.search([('state', 'in', ('submitted', 'approved', 'settled'))]):
            used_order_ids.update(r.order_ids.ids)
        out = []
        total = 0.0
        for l in lines:
            o = l.sale_order_id
            if not o or o.id in used_order_ids:
                continue
            # Only COD-style orders should show
            method = (o.payment_term_id.name or '').lower() if o.payment_term_id else ''
            if 'cash' not in method and not any('cod' in (t.provider_code or '').lower()
                                                 for t in o.transaction_ids):
                # Heuristic: if there's a paid transaction, it's not cash
                paid_tx = o.transaction_ids.filtered(lambda t: t.state in ('done', 'authorized'))
                if paid_tx:
                    continue
            amt = float(o.amount_total or 0)
            total += amt
            out.append({
                'line_id': l.id,
                'order_id': o.id,
                'order_name': o.name,
                'customer': o.partner_id.name,
                'addr_short': short_addr(o.partner_shipping_id or o.partner_id),
                'amount': fmt_price(amt, o.currency_id),
                'when': (l.delivery_date_actual or l.write_date or datetime.now()).isoformat(),
            })
        return ok({
            'items': out,
            'total': fmt_price(total),
            'count': len(out),
        })

    @http.route('/api/driver/v1/cash/submit', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def submit(self, **kw):
        driver = current_driver()
        p = get_payload()
        order_ids = p.get('order_ids') or []
        carrier_ref = (p.get('carrier_ref') or '').strip()
        if not order_ids:
            return fail('NO_ORDERS', 'Pick at least one order to settle')
        if not driver.carrier_company_id:
            return fail('NO_COMPANY', 'Driver has no carrier company')
        order_ids = [int(x) for x in order_ids if x]
        orders = request.env['sale.order'].sudo().browse(order_ids).filtered(lambda o: o.exists())
        if not orders:
            return fail('NOT_FOUND', 'No matching orders')
        Rem = request.env['delivery.cash.remittance'].sudo()
        rem = Rem.create({
            'carrier_company_id': driver.carrier_company_id.id,
            'order_ids':  [(6, 0, orders.ids)],
            'state':      'submitted',
        })
        if 'carrier_reference' in rem._fields and carrier_ref:
            rem.write({'carrier_reference': carrier_ref})
        if 'submitted_by_driver_id' in rem._fields:
            rem.write({'submitted_by_driver_id': driver.id})
        rem._compute_totals() if hasattr(rem, '_compute_totals') else None
        return ok({
            'remittance_id': rem.id,
            'reference': rem.name,
            'total': fmt_price(rem.total_amount or 0),
            'state': rem.state,
            'order_count': len(orders),
        })

    @http.route('/api/driver/v1/cash/history', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def history(self, **kw):
        driver = current_driver()
        if not driver.carrier_company_id:
            return ok([])
        Rem = request.env['delivery.cash.remittance'].sudo()
        rows = Rem.search([
            ('carrier_company_id', '=', driver.carrier_company_id.id),
        ], order='id desc', limit=50)
        return ok([{
            'id':     r.id,
            'name':   r.name,
            'state':  r.state,
            'state_label': {
                'submitted': {'en':'Submitted','ar':'مرسلة'},
                'approved':  {'en':'Approved', 'ar':'موافق عليها'},
                'settled':   {'en':'Settled',  'ar':'مسوّاة'},
            }.get(r.state, {'en': r.state, 'ar': r.state}),
            'order_count': len(r.order_ids),
            'total':  fmt_price(r.total_amount or 0),
            'net':    fmt_price(r.net_to_uellow or 0),
            'when':   (r.create_date or datetime.now()).isoformat(),
        } for r in rows])

    @http.route('/api/driver/v1/cash/<int:rem_id>', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def remittance_detail(self, rem_id, **kw):
        rem = request.env['delivery.cash.remittance'].sudo().browse(rem_id)
        if not rem.exists():
            return fail('NOT_FOUND', 'Remittance not found', 404)
        return ok({
            'id':   rem.id,
            'name': rem.name,
            'state': rem.state,
            'totals': {
                'total':        fmt_price(rem.total_amount or 0),
                'delivery_fees':fmt_price(rem.total_delivery_fees or 0),
                'commission':   fmt_price(rem.total_cash_commission or 0),
                'cancel_fees':  fmt_price(rem.total_cancel_fees or 0),
                'return_fees':  fmt_price(rem.total_return_exch_fees or 0),
                'carrier_cost': fmt_price(rem.total_carrier_cost or 0),
                'collected':    fmt_price(rem.cash_collected or 0),
                'net':          fmt_price(rem.net_to_uellow or 0),
            },
            'orders': [{
                'id': o.id, 'name': o.name,
                'amount': fmt_price(o.amount_total, o.currency_id),
                'customer': o.partner_id.name,
            } for o in rem.order_ids],
        })
