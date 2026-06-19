# -*- coding: utf-8 -*-
"""Vendor stock returns — /api/vendor/v1/returns*

Lets a vendor whose goods are stored at Uellow (FBU / Consignment) request a
withdrawal/return. Admin approves + prints the signed note + settles stock.
"""
from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth,
    current_vendor, fmt_price,
)


_REASON_LABELS = {
    'overstock':     {'en': 'Overstock',                'ar': 'فائض مخزون'},
    'slow_moving':   {'en': 'Slow moving / dead stock', 'ar': 'بطيء الحركة / راكد'},
    'quality_issue': {'en': 'Quality issue',            'ar': 'مشكلة جودة'},
    'expiring':      {'en': 'Expiring / expired',       'ar': 'قارب/منتهي الصلاحية'},
    'end_of_season': {'en': 'End of season',            'ar': 'نهاية الموسم'},
    'recall':        {'en': 'Product recall',           'ar': 'سحب المنتج'},
    'other':         {'en': 'Other',                    'ar': 'أخرى'},
}
_INITIATOR_LABELS = {
    'vendor': {'en': 'Vendor withdrawal', 'ar': 'سحب التاجر'},
    'uellow': {'en': 'Uellow return',     'ar': 'إرجاع من يلو'},
}


def _ser(r):
    return {
        'id': r.id,
        'name': r.name,
        'state': r.state,
        'pickup_mode': r.pickup_mode,
        'initiator': r.initiator,
        'initiator_label': _INITIATOR_LABELS.get(r.initiator, {'en': r.initiator, 'ar': r.initiator}),
        'reason_code': r.reason_code,
        'reason_label': _REASON_LABELS.get(r.reason_code, {'en': '', 'ar': ''}),
        'reason': r.reason or '',
        'total_qty': r.total_qty,
        'total_cost': fmt_price(r.total_cost or 0, r.vendor_id.currency_id),
        'when': r.submitted_date.isoformat() if r.submitted_date else '',
        'items': [{'name': l.product_id.display_name, 'qty': l.qty} for l in r.line_ids],
    }


class VendorReturnsAPI(http.Controller):

    @http.route('/api/vendor/v1/returns', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_returns(self, **kw):
        v = current_vendor()
        rows = request.env['uellow.return.request'].sudo().search(
            [('vendor_id', '=', v.id)], order='id desc', limit=50)
        return ok({
            'returns': [_ser(r) for r in rows],
            'reasons': [{'code': c, **lbl} for c, lbl in _REASON_LABELS.items()],
        })

    @http.route('/api/vendor/v1/returns', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def create_return(self, **kw):
        v = current_vendor()
        if not v.cap('restock'):
            return fail('FORBIDDEN', 'Returns are disabled for your account.', 403, capability='restock')
        p = get_payload()
        pickup = p.get('pickup_mode') if p.get('pickup_mode') in ('self', 'uellow') else 'self'
        reason_code = p.get('reason_code') if p.get('reason_code') in _REASON_LABELS else 'other'
        items = p.get('items') or []
        lines = []
        Tmpl = request.env['product.template'].sudo()
        for it in items:
            try:
                tid = int(it.get('product_id'))
                qty = int(it.get('qty') or 0)
            except (TypeError, ValueError):
                continue
            t = Tmpl.browse(tid)
            if not t.exists() or t.vendor_id.id != v.id or qty <= 0:
                continue
            var = t.product_variant_id
            if not var:
                continue
            lines.append((0, 0, {'product_id': var.id, 'qty': qty,
                                 'cost': t.standard_price or 0}))
        if not lines:
            return fail('NO_ITEMS', 'Select at least one product with a quantity.')
        r = request.env['uellow.return.request'].sudo().create({
            'vendor_id': v.id,
            'pickup_mode': pickup,
            'initiator': 'vendor',
            'reason_code': reason_code,
            'reason': (p.get('reason') or '').strip(),
            'line_ids': lines,
        })
        # notify admins
        try:
            CN = request.env['mobile.customer.notification'].sudo()
            admins = CN._admin_partners()
            if admins:
                CN.push_role('notify_return_request', admins,
                    title_en='New stock return request',
                    title_ar='طلب استرجاع بضاعة جديد',
                    body_en='%s requested a return (%s items).' % (v.display_name, len(lines)),
                    body_ar='%s طلب استرجاع بضاعة.' % v.display_name,
                    data={'type': 'return_request', 'id': r.id})
        except Exception:
            pass
        return ok({'id': r.id, 'name': r.name, 'state': r.state})
