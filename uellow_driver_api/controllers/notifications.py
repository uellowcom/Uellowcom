# -*- coding: utf-8 -*-
"""Notifications inbox — /api/driver/v1/notifications*

Reads from mail.message rows targeted at the driver's partner. Acts as
an in-app inbox; the actual PUSH delivery happens via FCM from a cron
hook that watches new mail.message rows (left as a TODO in the next
release).
"""
from datetime import datetime

from odoo import http
from odoo.http import request

from ._common import (
    safe_endpoint, ok, require_auth, current_driver,
)


def _classify(msg):
    sub = (msg.subject or '').lower()
    body = (msg.body or '').lower()
    if 'new order' in sub or 'assigned' in body:
        return 'new_order'
    if 'reschedule' in sub or 'reschedule' in body:
        return 'reschedule'
    if 'settlement' in sub or 'rem-' in body:
        return 'settlement'
    if 'license' in body or 'inspection' in body or 'document' in body:
        return 'vehicle_doc'
    return 'ops_message'


class DriverNotificationsAPI(http.Controller):

    @http.route('/api/driver/v1/notifications', type='http', auth='public',
                methods=['GET', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def list_notif(self, **kw):
        driver = current_driver()
        partner = driver.portal_user_id.partner_id if driver.portal_user_id else None
        if not partner:
            return ok([])
        Msg = request.env['mail.message'].sudo()
        msgs = Msg.search([
            ('partner_ids', 'in', [partner.id]),
            ('message_type', 'in', ('comment', 'notification', 'email')),
        ], order='id desc', limit=50)
        out = []
        for m in msgs:
            from html import unescape
            import re
            body_text = re.sub('<[^<]+?>', '', (m.body or '')).strip()
            body_text = unescape(body_text)[:240]
            out.append({
                'id': m.id,
                'title': m.subject or (m.record_name or 'Notification'),
                'body': body_text,
                'category': _classify(m),
                'when': (m.date or datetime.now()).isoformat(),
                'is_new': not bool(m.is_internal),  # heuristic
                'order_id': m.res_id if m.model == 'sale.order' else None,
            })
        return ok(out)

    @http.route('/api/driver/v1/notifications/<int:msg_id>/read', type='http',
                auth='public', methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    @require_auth
    def mark_read(self, msg_id, **kw):
        driver = current_driver()
        partner = driver.portal_user_id.partner_id if driver.portal_user_id else None
        if not partner:
            return ok({'marked': False})
        Msg = request.env['mail.message'].sudo()
        msg = Msg.browse(msg_id)
        if msg.exists():
            # Use needaction read marking
            try:
                msg.set_message_done()
            except Exception:
                pass
        return ok({'marked': True})
