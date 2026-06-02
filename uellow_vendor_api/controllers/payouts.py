# -*- coding: utf-8 -*-
"""Vendor payouts + commissions — /api/vendor/v1/payouts*"""
from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth,
    current_vendor, fmt_price,
)


def _ser_payout(p):
    return {
        'id': p.id,
        'name': p.name,
        'amount': fmt_price(p.amount or 0, p.currency_id),
        'state': p.state,
        'state_label': {
            'draft':    {'en': 'Pending', 'ar': 'قيد التحضير'},
            'approved': {'en': 'Approved','ar': 'مُعتمد'},
            'paid':     {'en': 'Paid',    'ar': 'مدفوع'},
            'cancelled':{'en': 'Cancelled','ar': 'ملغى'},
        }.get(p.state, {'en': p.state, 'ar': p.state}),
        'payout_date': p.payout_date.isoformat() if p.payout_date else None,
        'bank_iban': p.bank_iban or '',
        'when': p.create_date.isoformat() if p.create_date else '',
        'line_count': len(p.commission_line_ids),
    }


def _ser_commission(c):
    return {
        'id': c.id,
        'order_id': c.order_id.id if c.order_id else 0,
        'order_name': c.order_id.name if c.order_id else '',
        'order_date': c.order_date.isoformat() if c.order_date else '',
        'order_amount': fmt_price(c.order_amount or 0, c.currency_id),
        'commission_rate': float(c.commission_rate or 0),
        'commission_amount': fmt_price(c.commission_amount or 0, c.currency_id),
        'net_vendor_amount': fmt_price(c.net_vendor_amount or 0, c.currency_id),
        'state': c.state,
        'release_date': c.release_date.isoformat() if c.release_date else None,
    }


class VendorPayoutsAPI(http.Controller):

    @http.route('/api/vendor/v1/payouts', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_payouts(self, **kw):
        v = current_vendor()
        Payout = request.env['uellow.vendor.payout'].sudo()
        rows = Payout.search([('vendor_id', '=', v.id)], order='id desc', limit=100)
        return ok([_ser_payout(p) for p in rows])

    @http.route('/api/vendor/v1/payouts/<int:pid>', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def payout_detail(self, pid, **kw):
        v = current_vendor()
        p = request.env['uellow.vendor.payout'].sudo().browse(pid)
        if not p.exists() or p.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Payout not found', 404)
        return ok({
            'payout': _ser_payout(p),
            'lines': [_ser_commission(c) for c in p.commission_line_ids],
        })

    @http.route('/api/vendor/v1/commissions', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def commissions(self, **kw):
        v = current_vendor()
        p = get_payload()
        state = (p.get('state') or '').strip()
        Comm = request.env['uellow.vendor.commission'].sudo()
        domain = [('vendor_id', '=', v.id)]
        if state:
            domain += [('state', '=', state)]
        rows = Comm.search(domain, order='id desc', limit=100)
        # Aggregate totals
        pending = sum(c.net_vendor_amount or 0 for c in rows.filtered(lambda c: c.state == 'pending'))
        released = sum(c.net_vendor_amount or 0 for c in rows.filtered(lambda c: c.state == 'released'))
        paid_out = sum(c.net_vendor_amount or 0 for c in rows.filtered(lambda c: c.state == 'paid_out'))
        cur = v.currency_id or request.env.company.currency_id
        return ok({
            'items': [_ser_commission(c) for c in rows],
            'totals': {
                'pending':  fmt_price(pending, cur),
                'released': fmt_price(released, cur),
                'paid_out': fmt_price(paid_out, cur),
            },
        })

    @http.route('/api/vendor/v1/payouts/request', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def request_payout(self, **kw):
        """Vendor-initiated payout request: bundles every released
        commission with no payout yet into a fresh draft payout."""
        v = current_vendor()
        Comm = request.env['uellow.vendor.commission'].sudo()
        ready = Comm.search([
            ('vendor_id', '=', v.id),
            ('state', '=', 'released'),
            ('payout_id', '=', False),
        ])
        if not ready:
            return fail('NOTHING', 'No released commissions to pay out')
        amount = sum(c.net_vendor_amount or 0 for c in ready)
        Payout = request.env['uellow.vendor.payout'].sudo()
        cur = v.currency_id or request.env.company.currency_id
        p = Payout.create({
            'vendor_id': v.id,
            'currency_id': cur.id,
            'amount': amount,
            'state': 'draft',
        })
        ready.write({'payout_id': p.id})
        return ok({'payout': _ser_payout(p), 'line_count': len(ready)})
