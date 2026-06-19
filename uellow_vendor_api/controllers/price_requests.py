# -*- coding: utf-8 -*-
"""Vendor app — price-update requests.  /api/vendor/v1/price-requests*

The merchant lists requests addressed to them, opens one, and per line
either Matches (keeps the current price) or proposes a new price. Matched
/ unchanged lines auto-confirm; changed lines route to the buyer's
approval inbox (see uellow.price.request.submit_response)."""
from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth,
    current_vendor, img_url, bilingual,
)

_OPEN_STATES = ('sent', 'received', 'applied')


def _line(ln):
    return {
        'id': ln.id,
        'line_id': ln.id,
        'product_id': ln.product_tmpl_id.id,
        'name': bilingual(ln.product_tmpl_id, 'name'),
        'sku': ln.default_code or '',
        'image_url': img_url('product.template', ln.product_tmpl_id.id,
                             'image_256', unique=ln.product_tmpl_id.write_date)
                     if ln.product_tmpl_id.image_256 else None,
        'current_price': round(ln.current_price, 3),
        'new_price': round(ln.new_price, 3) if ln.new_price else None,
        'response': ln.response or None,
        'line_state': ln.line_state,
        'margin_after': round(ln.new_margin_pct, 1) if ln.new_price else None,
    }


def _request_brief(r):
    return {
        'id': r.id,
        'name': r.name,
        'state': r.state,
        'date': r.date,
        'product_count': r.product_count,
        'pending': len(r.line_ids.filtered(lambda l: l.line_state == 'pending')),
        'note': r.note or '',
    }


class VendorPriceRequestAPI(http.Controller):

    @http.route('/api/vendor/v1/price-requests', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_requests(self, **kw):
        vendor = current_vendor()
        recs = request.env['uellow.price.request'].sudo().search(
            [('merchant_id', '=', vendor.id), ('state', 'in', _OPEN_STATES)],
            order='create_date desc')
        return ok({'requests': [_request_brief(r) for r in recs]})

    @http.route('/api/vendor/v1/price-requests/<int:req_id>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def request_detail(self, req_id, **kw):
        vendor = current_vendor()
        r = request.env['uellow.price.request'].sudo().browse(req_id)
        if not r.exists() or r.merchant_id.id != vendor.id:
            return fail('NOT_FOUND', 'Request not found', 404)
        data = _request_brief(r)
        data['editable'] = r.state == 'sent'
        data['lines'] = [_line(ln) for ln in r.line_ids]
        return ok(data)

    @http.route('/api/vendor/v1/price-requests/<int:req_id>/respond',
                type='http', auth='public', methods=['POST', 'OPTIONS'],
                csrf=False)
    @safe_endpoint
    @require_auth
    def respond(self, req_id, **kw):
        """Body: {"responses":[{"line_id":1,"action":"match"},
                                {"line_id":2,"action":"price","price":9.5},
                                {"line_id":3,"action":"oos"}]}"""
        vendor = current_vendor()
        r = request.env['uellow.price.request'].sudo().browse(req_id)
        if not r.exists() or r.merchant_id.id != vendor.id:
            return fail('NOT_FOUND', 'Request not found', 404)
        if r.state != 'sent':
            return fail('ALREADY_DONE', 'You already responded', 409)
        p = get_payload()
        responses = p.get('responses') or []
        if not isinstance(responses, list) or not responses:
            return fail('MISSING_FIELDS', 'responses[] required')
        summary = r.submit_response(responses)
        request.env.cr.commit()
        return ok({'summary': summary, 'request': _request_brief(r)})
