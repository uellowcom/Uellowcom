# -*- coding: utf-8 -*-
"""Vendor → customer chat per order, backed by mail.thread on sale.order."""
from html import unescape
import re

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, get_payload, ok, fail, require_auth, current_vendor, img_url,
)


def _strip_html(s):
    s = re.sub('<[^<]+?>', ' ', s or '').strip()
    return unescape(s)


class VendorChatAPI(http.Controller):

    @http.route('/api/vendor/v1/chat/<int:order_id>', type='http',
                auth='public', methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_messages(self, order_id, **kw):
        v = current_vendor()
        o = request.env['sale.order'].sudo().browse(order_id)
        if not o.exists() or o.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Order not found', 404)
        msgs = o.message_ids.filtered(lambda m: m.message_type != 'auto_comment')[:80]
        out = []
        for m in reversed(list(msgs)):
            out.append({
                'id': m.id,
                'body': _strip_html(m.body or ''),
                'author': {
                    'id': m.author_id.id if m.author_id else 0,
                    'name': m.author_id.name if m.author_id else 'System',
                    'avatar_url': img_url('res.partner', m.author_id.id, 'image_128',
                                          unique=m.author_id.write_date)
                                   if m.author_id and m.author_id.image_128 else None,
                },
                'is_self': bool(m.author_id and v.user_id and
                                m.author_id.id == v.user_id.partner_id.id),
                'when': m.date.isoformat() if m.date else '',
            })
        return ok(out)

    @http.route('/api/vendor/v1/chat/<int:order_id>/send', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def send(self, order_id, **kw):
        v = current_vendor()
        p = get_payload()
        text = (p.get('body') or '').strip()
        if not text:
            return fail('EMPTY', 'Message body required')
        o = request.env['sale.order'].sudo().browse(order_id)
        if not o.exists() or o.vendor_id.id != v.id:
            return fail('NOT_FOUND', 'Order not found', 404)
        partner = v.user_id.partner_id if v.user_id else None
        notify = [o.partner_id.id] if o.partner_id else []
        msg = o.with_user(v.user_id.id).message_post(
            body=text, author_id=partner.id if partner else None,
            partner_ids=notify)
        return ok({'message_id': msg.id})
