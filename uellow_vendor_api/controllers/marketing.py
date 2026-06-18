# -*- coding: utf-8 -*-
"""Vendor marketing & ops — sponsored listings + order disputes (app side)."""
from datetime import datetime

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth, current_vendor,
)

REASONS = [
    ('out_of_stock', 'Out of stock', 'نفاد المخزون'),
    ('customer_unreachable', 'Customer unreachable', 'تعذّر الوصول للعميل'),
    ('damaged', 'Item damaged', 'تلف المنتج'),
    ('wrong_item', 'Wrong item', 'منتج خاطئ'),
    ('not_received', 'Not received', 'لم يصل'),
    ('return_request', 'Customer return request', 'طلب استرجاع'),
    ('other', 'Other', 'أخرى'),
]


def _ser_ad(c):
    return {
        'id': c.id, 'name': c.name, 'product_id': c.product_tmpl_id.id,
        'product': c.product_tmpl_id.name,
        'start': c.start_date.isoformat() if c.start_date else '',
        'end': c.end_date.isoformat() if c.end_date else '',
        'days': c.days, 'daily_rate': c.daily_rate, 'total_cost': c.total_cost,
        'state': c.state, 'impressions': c.impressions, 'clicks': c.clicks,
    }


def _ser_dispute(d):
    return {
        'id': d.id, 'name': d.name, 'order_id': d.order_id.id,
        'order': d.order_id.name, 'customer': d.partner_id.name or '',
        'reason': d.reason, 'state': d.state,
        'description': d.description or '', 'resolution': d.resolution or '',
        'when': d.create_date.isoformat() if d.create_date else '',
    }


class VendorMarketingController(http.Controller):

    # ══ SPONSORED LISTINGS ═══════════════════════════════════════
    @http.route('/api/vendor/v1/ads', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_ads(self, **kw):
        v = current_vendor()
        rate = float(request.env['ir.config_parameter'].sudo().get_param(
            'uellow.vendor_api.ad_daily_rate', '1.0') or 1.0)
        ads = request.env['vendor.ad.campaign'].sudo().search([('vendor_id', '=', v.id)])
        return ok({
            'campaigns': [_ser_ad(c) for c in ads],
            'daily_rate': rate,
            'wallet_balance': v.wallet_id.balance if v.wallet_id else 0.0,
        })

    @http.route('/api/vendor/v1/ads/create', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def create_ad(self, **kw):
        v = current_vendor()
        p = get_payload()
        try:
            pid = int(p.get('product_id'))
        except (TypeError, ValueError):
            return fail('BAD_PRODUCT', 'product_id required')
        t = request.env['product.template'].sudo().browse(pid)
        if not t.exists() or t.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Product not found', 404)
        try:
            start = datetime.strptime(p.get('start'), '%Y-%m-%d').date()
            end = datetime.strptime(p.get('end'), '%Y-%m-%d').date()
        except (TypeError, ValueError):
            return fail('BAD_DATE', 'start and end (YYYY-MM-DD) required')
        if end < start:
            return fail('BAD_RANGE', 'end must be on/after start')
        camp = request.env['vendor.ad.campaign'].sudo().create({
            'name': p.get('name') or ('Sponsored: %s' % t.name),
            'vendor_id': v.id, 'product_tmpl_id': t.id,
            'start_date': start, 'end_date': end,
        })
        try:
            camp.action_activate()
        except Exception as e:
            camp.unlink()
            return fail('CHARGE_FAILED', str(e))
        return ok(_ser_ad(camp))

    @http.route('/api/vendor/v1/ads/<int:cid>/cancel', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def cancel_ad(self, cid, **kw):
        v = current_vendor()
        c = request.env['vendor.ad.campaign'].sudo().browse(cid)
        if not c.exists() or c.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Campaign not found', 404)
        c.action_cancel()
        return ok(_ser_ad(c))

    # ══ ORDER DISPUTES / ISSUES ══════════════════════════════════
    @http.route('/api/vendor/v1/disputes', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_disputes(self, **kw):
        v = current_vendor()
        ds = request.env['vendor.order.dispute'].sudo().search([('vendor_id', '=', v.id)])
        return ok({
            'disputes': [_ser_dispute(d) for d in ds],
            'reasons': [{'code': c, 'en': en, 'ar': ar} for c, en, ar in REASONS],
        })

    @http.route('/api/vendor/v1/disputes/create', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def create_dispute(self, **kw):
        v = current_vendor()
        p = get_payload()
        try:
            oid = int(p.get('order_id'))
        except (TypeError, ValueError):
            return fail('BAD_ORDER', 'order_id required')
        o = request.env['sale.order'].sudo().browse(oid)
        if not o.exists() or o.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Order not found', 404)
        reason = p.get('reason')
        if reason not in {c for c, _e, _a in REASONS}:
            reason = 'other'
        d = request.env['vendor.order.dispute'].sudo().create({
            'vendor_id': v.id, 'order_id': o.id, 'reason': reason,
            'description': (p.get('description') or '').strip(),
        })
        return ok(_ser_dispute(d))
