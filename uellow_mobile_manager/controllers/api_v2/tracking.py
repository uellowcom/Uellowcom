# -*- coding: utf-8 -*-
"""Customer journey ingest — the app batches screen views, app open/close
and key actions and POSTs them here. Public (works for guests too); links
to the partner + session when authenticated."""
from odoo import http
from odoo.http import request

from ._common import (ok, get_payload, safe_endpoint, current_partner,
                      current_session, get_website)


class TrackingController(http.Controller):

    @http.route('/api/mobile/v2/track', type='http', auth='public',
                methods=['POST', 'OPTIONS'], csrf=False)
    @safe_endpoint
    def track(self, **kw):
        p = get_payload()
        events = p.get('events')
        # accept a single event too
        if events is None and p.get('event'):
            events = [p]
        if not isinstance(events, list) or not events:
            return ok({'stored': 0})
        partner = current_partner()
        session = current_session()
        try:
            n = request.env['uellow.customer.activity'].sudo().record_batch(
                events, partner=partner, session=session,
                platform=p.get('platform'), app_version=p.get('app_version'),
                device=p.get('device'), website=get_website())
            request.env.cr.commit()
        except Exception:
            n = 0
        return ok({'stored': n})
